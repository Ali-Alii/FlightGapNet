import sys
import json
import pandas as pd
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from config import (
    DATA_DIR,
    MODEL_DIR,
    PRED_LEN,
    SEQ_LEN,
    FEATURE_COLS,
    TARGET_COLS,
    MIN_GAP_DURATION,
    MAX_GAP_DURATION,
)
from services.preprocessor import clean_track, normalize_features
from ml.dataset import build_dataloaders
from ml.model import get_model
from ml.trainer import train_model, load_model
from ml.predictor import predict_gap
from services.gap_simulator import simulate_gaps
from services.baseline import (
    great_circle_interpolate,
    constant_velocity_predict_gap,
    kalman_fill_gap_offline,
    last_point_hold_predict_gap,
)
from services.evaluator import compute_metrics

MIN_CLEAN_TRACK_LEN = SEQ_LEN + PRED_LEN + 5


def load_all_tracks() -> list[pd.DataFrame]:
    track_dir = DATA_DIR / "raw_tracks"
    print("DATA_DIR =", DATA_DIR)
    print("track_dir =", track_dir)

    csv_files = sorted(track_dir.glob("*.csv"))
    print("CSV files found by train_models.py:", len(csv_files))
    print("First 10 files:", [p.name for p in csv_files[:10]])

    trajectories = []
    kept_count = 0
    dropped_empty_count = 0
    dropped_short_count = 0
    dropped_useless_speed = 0

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path, parse_dates=["time"])
            raw_len = len(df)

            clean_df = clean_track(df, track_name=csv_path.name)
            clean_len = len(clean_df) if clean_df is not None else 0

            if clean_df is None or clean_df.empty:
                print(f"DROP {csv_path.name}: raw={raw_len}, clean=0 (empty after cleaning)")
                dropped_empty_count += 1
                continue

            if "speed_knots" in clean_df.columns:
                if clean_df["speed_knots"].abs().max() < 1e-6:
                    print(f"DROP {csv_path.name}: useless speed signal")
                    dropped_useless_speed += 1
                    continue

            if len(clean_df) >= MIN_CLEAN_TRACK_LEN:
                print(f"KEEP {csv_path.name}: raw={raw_len}, clean={clean_len}")
                trajectories.append(clean_df)
                kept_count += 1
            else:
                print(f"DROP {csv_path.name}: raw={raw_len}, clean={clean_len} (< {MIN_CLEAN_TRACK_LEN})")
                dropped_short_count += 1

        except Exception as e:
            print(f"⚠ Skipping {csv_path.name}: {e}")

    print("\nTrack loading summary:")
    print(f"  Kept: {kept_count}")
    print(f"  Dropped empty after cleaning: {dropped_empty_count}")
    print(f"  Dropped too short after cleaning: {dropped_short_count}")
    print(f"  Dropped useless speed: {dropped_useless_speed}")
    print(f"Loaded {len(trajectories)} cleaned trajectories (len >= {MIN_CLEAN_TRACK_LEN})")

    return trajectories


def normalize_all(trajectories, train_frac=0.70):
    n_train = int(len(trajectories) * train_frac)
    train_trajs = trajectories[:n_train]

    if not train_trajs:
        raise ValueError("No training trajectories — cannot fit scaler.")

    train_combined = pd.concat(train_trajs, ignore_index=True)
    all_cols = list(dict.fromkeys(list(FEATURE_COLS) + list(TARGET_COLS)))

    dropped = []
    for col in all_cols:
        if col not in train_combined.columns or not train_combined[col].notna().any():
            dropped.append(col)
    if dropped:
        print(f"⚠ All-NaN columns (will normalize to 0): {dropped}")

    _, scaler_params = normalize_features(train_combined)

    print("\nScaler ranges (all must be finite — NaN here = broken inference):")
    for col in all_cols:
        p = scaler_params.get(col, {})
        mn, mx = p.get("min", "MISSING"), p.get("max", "MISSING")
        flag = " ← 🚨 NaN!" if (isinstance(mn, float) and np.isnan(mn)) else ""
        print(f"  {col:<20} min={mn}  max={mx}{flag}")

    for col in TARGET_COLS:
        p = scaler_params.get(col, {})
        if isinstance(p.get("min"), float) and np.isnan(p["min"]):
            raise RuntimeError(f"Target column '{col}' has NaN scaler bounds.")

    normalized = []
    for df in trajectories:
        norm_df, _ = normalize_features(df.copy(), scaler_params)
        normalized.append(norm_df)

    return normalized, scaler_params


def _to_latlonalt_df(values) -> pd.DataFrame:
    if isinstance(values, pd.DataFrame):
        cols = [c for c in ["lat", "lon", "altitude"] if c in values.columns]
        if len(cols) != 3:
            raise ValueError(f"Expected lat/lon/altitude columns, got: {list(values.columns)}")

        out = values[["lat", "lon", "altitude"]].copy().reset_index(drop=True)
        out = out.apply(pd.to_numeric, errors="coerce")
        out = out.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return out.astype(float)

    arr = np.asarray(values)

    if arr.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {arr.shape}")

    if arr.shape[1] < 3:
        raise ValueError(f"Expected at least 3 columns, got shape {arr.shape}")

    arr = arr[:, :3]
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)

    return pd.DataFrame(arr, columns=["lat", "lon", "altitude"]).reset_index(drop=True).astype(float)


def _avg_metric_dict(metrics_list):
    keys = metrics_list[0].keys()
    averaged = {}

    for k in keys:
        numeric_vals = []
        for m in metrics_list:
            if k not in m:
                continue
            v = m[k]
            if isinstance(v, (int, float, np.integer, np.floating)) and np.isfinite(v):
                numeric_vals.append(float(v))

        if numeric_vals:
            averaged[k] = float(np.mean(numeric_vals))

    return averaged


def evaluate_on_test(model, model_name, test_trajs_raw, scaler_params):
    all_gc_metrics = []
    all_lph_metrics = []
    all_cv_metrics = []
    all_kf_metrics = []
    all_model_metrics = []
    valid_count = 0
    skipped_nan = 0

    skip_short_df = 0
    skip_gap_empty = 0
    skip_no_gap = 0
    skip_gap_too_long = 0
    skip_context_short = 0
    skip_simulate_error = 0
    skip_metric_error = 0

    for df in test_trajs_raw:
        if df is None or df.empty or len(df) < SEQ_LEN + PRED_LEN + 5:
            skip_short_df += 1
            continue

        for _ in range(5):
            try:
                gapped_df, gap_truth = simulate_gaps(
                    df,
                    min_gap=MIN_GAP_DURATION,
                    max_gap=MAX_GAP_DURATION,
                    edge_buffer=SEQ_LEN,
                )
            except Exception as e:
                skip_simulate_error += 1
                print(f"simulate_gaps error: {e}")
                continue

            if gap_truth.empty or "is_gap" not in gapped_df.columns:
                skip_gap_empty += 1
                continue

            if not gapped_df["is_gap"].any():
                skip_no_gap += 1
                continue

            gap_start = int(gapped_df["is_gap"].idxmax())
            gap_length = int(gapped_df["is_gap"].sum())

            if gap_length <= 0 or gap_length > PRED_LEN:
                skip_gap_too_long += 1
                continue

            context_df = df.iloc[max(0, gap_start - SEQ_LEN): gap_start].copy()
            if len(context_df) < SEQ_LEN:
                skip_context_short += 1
                continue

            try:
                model_pred = predict_gap(model, context_df, gap_length, scaler_params)
                lph_pred = last_point_hold_predict_gap(context_df, gap_length)
                cv_pred = constant_velocity_predict_gap(context_df, gap_length, history_points=3)

                kf_filled = kalman_fill_gap_offline(
                    gapped_df,
                    history_points=6,
                    blend_with_endpoint=0.35,
                )
                gap_indices = gapped_df.index[gapped_df["is_gap"]].tolist()
                kf_df = kf_filled.loc[gap_indices, ["lat", "lon", "altitude"]].copy().reset_index(drop=True)

            except ValueError as e:
                skipped_nan += 1
                if skipped_nan <= 3:
                    print(f"  Skipped: {e}")
                continue
            except Exception as e:
                print(f"  Eval error: {e}")
                continue

            try:
                gc_vals_full = great_circle_interpolate(gapped_df)
                gap_indices = gapped_df.index[gapped_df["is_gap"]].tolist()

                if isinstance(gc_vals_full, pd.DataFrame):
                    gc_df = gc_vals_full.loc[gap_indices, ["lat", "lon", "altitude"]].copy().reset_index(drop=True)
                else:
                    gc_arr = np.asarray(gc_vals_full)
                    gc_arr = gc_arr[gap_indices, :3]
                    gc_df = pd.DataFrame(gc_arr, columns=["lat", "lon", "altitude"]).reset_index(drop=True)

                true_df = gap_truth[["lat", "lon", "altitude"]].copy().reset_index(drop=True)
                gc_df = _to_latlonalt_df(gc_df)
                lph_df = _to_latlonalt_df(lph_pred)
                cv_df = _to_latlonalt_df(cv_pred)
                kf_df = _to_latlonalt_df(kf_df)
                model_df = _to_latlonalt_df(model_pred)

                true_df = true_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
                gc_df = gc_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
                lph_df = lph_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
                cv_df = cv_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
                kf_df = kf_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)
                model_df = model_df.apply(pd.to_numeric, errors="coerce").fillna(0.0).astype(float)

                min_len = min(
                    len(true_df),
                    len(gc_df),
                    len(lph_df),
                    len(cv_df),
                    len(kf_df),
                    len(model_df),
                )
                if min_len == 0:
                    skip_metric_error += 1
                    continue

                true_df = true_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)
                gc_df = gc_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)
                lph_df = lph_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)
                cv_df = cv_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)
                kf_df = kf_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)
                model_df = model_df.iloc[:min_len][["lat", "lon", "altitude"]].reset_index(drop=True).astype(float)

                gc_metrics = compute_metrics(true_df, gc_df, label="great_circle")
                lph_metrics = compute_metrics(true_df, lph_df, label="last_point_hold")
                cv_metrics = compute_metrics(true_df, cv_df, label="constant_velocity")
                kf_metrics = compute_metrics(true_df, kf_df, label="kalman")
                model_metrics = compute_metrics(true_df, model_df, label=model_name)

                all_gc_metrics.append(gc_metrics)
                all_lph_metrics.append(lph_metrics)
                all_cv_metrics.append(cv_metrics)
                all_kf_metrics.append(kf_metrics)
                all_model_metrics.append(model_metrics)
                valid_count += 1

            except Exception as e:
                skip_metric_error += 1
                print(f"  Metric error: {e}")
                continue

    if valid_count == 0:
        print("No valid test cases.")
        print("skip_short_df =", skip_short_df)
        print("skip_gap_empty =", skip_gap_empty)
        print("skip_no_gap =", skip_no_gap)
        print("skip_gap_too_long =", skip_gap_too_long)
        print("skip_context_short =", skip_context_short)
        print("skip_simulate_error =", skip_simulate_error)
        print("skip_metric_error =", skip_metric_error)
        return

    gc_avg = _avg_metric_dict(all_gc_metrics)
    lph_avg = _avg_metric_dict(all_lph_metrics)
    cv_avg = _avg_metric_dict(all_cv_metrics)
    kf_avg = _avg_metric_dict(all_kf_metrics)
    model_avg = _avg_metric_dict(all_model_metrics)

    print(f"\nValid test cases: {valid_count}  (skipped {skipped_nan} invalid cases)")
    print("skip_short_df =", skip_short_df)
    print("skip_gap_empty =", skip_gap_empty)
    print("skip_no_gap =", skip_no_gap)
    print("skip_gap_too_long =", skip_gap_too_long)
    print("skip_context_short =", skip_context_short)
    print("skip_simulate_error =", skip_simulate_error)
    print("skip_metric_error =", skip_metric_error)
    print()
    print(
        f"{'Metric':<34}"
        f"{'GreatCircle':>12}"
        f"{'LastHold':>12}"
        f"{'ConstVel':>12}"
        f"{'Kalman':>12}"
        f"{model_name.upper():>12}"
    )
    print("-" * 94)

    common_keys = [
        k for k in gc_avg.keys()
        if k in lph_avg and k in cv_avg and k in kf_avg and k in model_avg
    ]
    for key in common_keys:
        gc = gc_avg[key]
        lph = lph_avg[key]
        cv = cv_avg[key]
        kf = kf_avg[key]
        mv = model_avg[key]
        print(f"{key:<34}{gc:>12.4f}{lph:>12.4f}{cv:>12.4f}{kf:>12.4f}{mv:>12.4f}")


def main():
    MODEL_DIR.mkdir(exist_ok=True)

    trajectories = load_all_tracks()
    if len(trajectories) < 5:
        print("⚠ Not enough data. Collect more tracks first.")
        return

    norm_trajs, scaler_params = normalize_all(trajectories)
    with open(MODEL_DIR / "scaler_params.json", "w") as f:
        json.dump(scaler_params, f, indent=2)

    train_loader, val_loader, test_loader = build_dataloaders(norm_trajs)

    print(
        f"\n📊 Dataset: {len(norm_trajs)} trajectories  |  "
        f"Train={len(train_loader.dataset)}  "
        f"Val={len(val_loader.dataset)}  "
        f"Test={len(test_loader.dataset)}"
    )

    if len(train_loader.dataset) == 0:
        print("🚨 Training dataset is empty — tracks too short for SEQ_LEN+PRED_LEN.")
        return
    if len(val_loader.dataset) == 0:
        print("🚨 Validation dataset is empty — need more trajectories.")
        return

    n_test = max(1, int(len(trajectories) * 0.15))
    test_trajs_raw = trajectories[-n_test:]

    print("\n" + "=" * 60)
    lstm = get_model("lstm")
    train_model(lstm, train_loader, val_loader, model_name="lstm")
    lstm = load_model(get_model("lstm"), "lstm")
    print("\nLSTM Test Evaluation:")
    evaluate_on_test(lstm, "lstm", test_trajs_raw, scaler_params)

    print("\n" + "=" * 60)
    gru = get_model("gru")
    train_model(gru, train_loader, val_loader, model_name="gru")
    gru = load_model(get_model("gru"), "gru")
    print("\nGRU Test Evaluation:")
    evaluate_on_test(gru, "gru", test_trajs_raw, scaler_params)

    print("\n🎉 All models trained and saved to", MODEL_DIR)


if __name__ == "__main__":
    main()