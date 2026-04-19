import numpy as np
import pandas as pd
from scipy.stats import zscore

from config import (
    FEATURE_COLS,
    MAX_ALTITUDE_FT,
    MAX_SPEED_KNOTS,
    MIN_TRACK_POINTS,
    OUTLIER_Z_SCORE,
    RESAMPLE_INTERVAL_SECONDS,
    TARGET_COLS,
)

MS_TO_KNOTS = 1.94384
FT_TO_M = 0.3048
MAX_ALTITUDE_M = MAX_ALTITUDE_FT * FT_TO_M


def clean_track(df: pd.DataFrame, track_name: str = "unknown") -> pd.DataFrame:
    df = df.copy()

    print(f"\n--- CLEANING {track_name} ---")
    print(f"start rows: {len(df)}")

    if "time" in df.columns:
        before = len(df)
        df["time"] = pd.to_datetime(df["time"], errors="coerce", utc=True)
        df = df.dropna(subset=["time"])
        print(f"after time parse/dropna: {len(df)} (removed {before - len(df)})")
    else:
        print("missing time column")
        return pd.DataFrame()

    before = len(df)
    df = _drop_missing_positions(df)
    print(f"after drop missing positions: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _remove_ground_points(df)
    print(f"after remove ground points: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _remove_impossible_speed(df)
    print(f"after remove impossible speed: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _remove_altitude_outliers(df)
    print(f"after remove altitude outliers: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _drop_duplicate_timestamps(df)
    print(f"after drop duplicate timestamps: {len(df)} (removed {before - len(df)})")

    df = df.sort_values("time").reset_index(drop=True)

    if len(df) < MIN_TRACK_POINTS:
        print(f"STOP before spatial/resample: too short ({len(df)} < {MIN_TRACK_POINTS})")
        return pd.DataFrame()

    before = len(df)
    #df = _remove_spatial_outliers(df)
    print(f"after remove spatial outliers: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _resample_uniform(df)
    print(f"after resample uniform: {len(df)} (change {len(df) - before})")

    before = len(df)
    df = _fill_missing_features(df)
    print(f"after fill missing features: {len(df)} (removed {before - len(df)})")

    before = len(df)
    df = _compute_derived_features(df)
    print(f"after compute derived features: {len(df)} (removed {before - len(df)})")

    df = _ensure_required_columns(df)

    finite_cols = [c for c in set(FEATURE_COLS + TARGET_COLS + ["lat", "lon", "altitude"]) if c in df.columns]
    df[finite_cols] = df[finite_cols].replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)

    print(f"FINAL rows: {len(df)}")
    if "speed_knots" in df.columns:
        print(f"speed_knots min={df['speed_knots'].min()} max={df['speed_knots'].max()}")

    return df.reset_index(drop=True)


def _drop_missing_positions(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(subset=["lat", "lon"])


def _remove_ground_points(df: pd.DataFrame) -> pd.DataFrame:
    if "on_ground" in df.columns:
        df = df[df["on_ground"] != True]
    return df


def _remove_impossible_speed(df: pd.DataFrame) -> pd.DataFrame:
    if "velocity" in df.columns:
        max_ms = MAX_SPEED_KNOTS / MS_TO_KNOTS
        df = df[df["velocity"].isna() | (df["velocity"] <= max_ms)]
    return df


def _remove_altitude_outliers(df: pd.DataFrame) -> pd.DataFrame:
    if "altitude" not in df.columns:
        df["altitude"] = 0.0
    df["altitude"] = pd.to_numeric(df["altitude"], errors="coerce")
    return df[df["altitude"].isna() | df["altitude"].between(0, MAX_ALTITUDE_M)]


def _remove_spatial_outliers(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 10:
        return df

    work = df.copy()
    work["dlat"] = work["lat"].diff().abs()
    work["dlon"] = work["lon"].diff().abs()

    if work["dlat"].std() > 1e-9 and work["dlon"].std() > 1e-9:
        z_lat = np.abs(zscore(work["dlat"].fillna(0.0)))
        z_lon = np.abs(zscore(work["dlon"].fillna(0.0)))
        keep = (z_lat < OUTLIER_Z_SCORE) & (z_lon < OUTLIER_Z_SCORE)
        work = work[keep]

    return work.drop(columns=["dlat", "dlon"], errors="ignore")


def _drop_duplicate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=["time"], keep="first")


def _resample_uniform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.set_index("time").sort_index()
    rule = f"{RESAMPLE_INTERVAL_SECONDS}s"
    numeric_cols = df.select_dtypes(include=[np.number, "bool"]).columns
    df_numeric = df[numeric_cols].resample(rule).interpolate(method="linear")

    if "lat" in df_numeric.columns:
        df_numeric["lat"] = df_numeric["lat"].clip(-90.0, 90.0)
    if "lon" in df_numeric.columns:
        df_numeric["lon"] = df_numeric["lon"].clip(-180.0, 180.0)

    return df_numeric.reset_index().rename(columns={"index": "time"})

    # Drop rows still missing key trajectory fields
    required = [c for c in ["lat", "lon", "altitude"] if c in df_resampled.columns]
    if required:
        df_resampled = df_resampled.dropna(subset=required)

    if "lat" in df_resampled.columns:
        df_resampled["lat"] = df_resampled["lat"].clip(-90.0, 90.0)
    if "lon" in df_resampled.columns:
        df_resampled["lon"] = df_resampled["lon"].clip(-180.0, 180.0)

    return df_resampled.reset_index()


def _fill_missing_features(df: pd.DataFrame) -> pd.DataFrame:
    return df.ffill().bfill()


def _compute_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["delta_lat"] = df["lat"].diff().fillna(0.0)
    df["delta_lon"] = df["lon"].diff().fillna(0.0)
    df["delta_alt"] = df["altitude"].diff().fillna(0.0)

    if "heading" in df.columns:
        heading_num = pd.to_numeric(df["heading"], errors="coerce")
        if heading_num.notna().any():
            heading_rad = np.deg2rad(heading_num.ffill().bfill().fillna(0.0))
            df["heading_sin"] = np.sin(heading_rad)
            df["heading_cos"] = np.cos(heading_rad)
        else:
            angle = np.arctan2(df["delta_lon"].to_numpy(), df["delta_lat"].to_numpy())
            df["heading_sin"] = np.sin(angle)
            df["heading_cos"] = np.cos(angle)
    else:
        angle = np.arctan2(df["delta_lon"].to_numpy(), df["delta_lat"].to_numpy())
        df["heading_sin"] = np.sin(angle)
        df["heading_cos"] = np.cos(angle)

    velocity_num = None
    if "velocity" in df.columns:
        velocity_num = pd.to_numeric(df["velocity"], errors="coerce")

    use_velocity = velocity_num is not None and velocity_num.notna().any()

    lat_rad = np.deg2rad(df["lat"].clip(-89.9, 89.9))
    dlat_km = df["delta_lat"] * 111.32
    dlon_km = df["delta_lon"] * 111.32 * np.cos(lat_rad)
    step_km = np.sqrt(dlat_km**2 + dlon_km**2)

    hours = RESAMPLE_INTERVAL_SECONDS / 3600.0
    estimated_speed_knots = (step_km / hours) * 0.539957

    if use_velocity:
        speed_knots = velocity_num.ffill().bfill() * MS_TO_KNOTS

        # if provided velocity is mostly missing/zero, fall back to estimated speed
        if speed_knots.abs().sum() < 1e-6:
            speed_knots = estimated_speed_knots
    else:
        speed_knots = estimated_speed_knots

    df["speed_knots"] = (
        pd.Series(speed_knots, index=df.index)
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .clip(0.0, MAX_SPEED_KNOTS)
    )

    return df


def _ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in set(FEATURE_COLS + TARGET_COLS + ["lat", "lon", "altitude"]):
        if col not in df.columns:
            df[col] = 0.0
    return df


def _cols_to_normalize() -> list[str]:
    cols = []
    seen = set()
    for col in list(FEATURE_COLS) + list(TARGET_COLS):
        if col not in seen:
            cols.append(col)
            seen.add(col)
    return cols


def normalize_features(df: pd.DataFrame, scaler_params: dict | None = None) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    params = {} if scaler_params is None else dict(scaler_params)

    for col in _cols_to_normalize():
        if col not in df.columns:
            df[col] = 0.0

        raw = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)

        if col not in params:
            col_min = float(raw.min())
            col_max = float(raw.max())
            if not np.isfinite(col_min):
                col_min = 0.0
            if not np.isfinite(col_max):
                col_max = 0.0
            params[col] = {"min": col_min, "max": col_max}

        col_min = float(params[col].get("min", 0.0))
        col_max = float(params[col].get("max", 0.0))
        rng = col_max - col_min

        if rng > 1e-9:
            df[col] = ((raw - col_min) / rng).clip(0.0, 1.0)
        else:
            df[col] = 0.0

    return df, params


def denormalize_targets(arr: np.ndarray, scaler_params: dict) -> np.ndarray:
    result = np.array(arr, dtype=float, copy=True)

    for i, col in enumerate(TARGET_COLS):
        p = scaler_params.get(col, {"min": 0.0, "max": 0.0})
        col_min = float(p.get("min", 0.0))
        col_max = float(p.get("max", 0.0))
        rng = col_max - col_min

        if rng > 1e-9:
            result[:, i] = result[:, i] * rng + col_min
        else:
            result[:, i] = col_min

    return np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)
