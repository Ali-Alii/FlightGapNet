"""
baseline.py
-----------
Trajectory reconstruction baselines / classical models.

Includes:
1. Great-circle interpolation baseline
2. Constant-velocity reconstruction model
3. Kalman-style constant-velocity smoother / predictor

The Kalman-style model uses a simple linear dynamical system with state:
    [lat, lon, altitude, v_lat, v_lon, v_alt]

It can:
- filter known trajectory points before a gap
- predict through the missing segment
- optionally blend lightly toward the first known point after the gap
  for offline gap reconstruction
"""

import numpy as np
import pandas as pd
from geopy.distance import geodesic


def great_circle_interpolate(gapped_df: pd.DataFrame) -> pd.DataFrame:
    df = gapped_df.copy()

    if "is_gap" not in df.columns or not df["is_gap"].any():
        return df

    gap_indices = df[df["is_gap"]].index

    start_idx = gap_indices.min() - 1
    end_idx = gap_indices.max() + 1

    if start_idx < 0 or end_idx >= len(df):
        return df

    start = df.loc[start_idx]
    end = df.loc[end_idx]

    n = len(gap_indices)

    for i, idx in enumerate(gap_indices):
        alpha = (i + 1) / (n + 1)

        df.loc[idx, "lat"] = (1 - alpha) * start["lat"] + alpha * end["lat"]
        df.loc[idx, "lon"] = (1 - alpha) * start["lon"] + alpha * end["lon"]

        if "altitude" in df.columns:
            df.loc[idx, "altitude"] = (
                (1 - alpha) * start["altitude"] + alpha * end["altitude"]
            )

    return df


def constant_velocity_fill(
    gapped_df: pd.DataFrame,
    history_points: int = 3,
) -> pd.DataFrame:
    filled = gapped_df.copy().reset_index(drop=True)

    required_cols = ["lat", "lon"]
    for col in required_cols:
        if col not in filled.columns:
            raise ValueError(f"Missing required column '{col}' in gapped_df")

    if "altitude" not in filled.columns:
        filled["altitude"] = 0.0

    is_gap = filled["lat"].isna() | filled["lon"].isna()

    if not is_gap.any():
        return filled

    gap_indices = np.where(is_gap.to_numpy())[0]
    blocks = _group_consecutive_indices(gap_indices)

    for block in blocks:
        gap_start = block[0]
        gap_len = len(block)

        if gap_start < 1:
            continue

        valid_before = filled.iloc[:gap_start].dropna(subset=["lat", "lon", "altitude"])
        if len(valid_before) < 2:
            continue

        hist = valid_before.tail(history_points + 1).copy()
        if len(hist) < 2:
            continue

        dlat = hist["lat"].diff().dropna().mean()
        dlon = hist["lon"].diff().dropna().mean()
        dalt = hist["altitude"].diff().dropna().mean()

        dlat = 0.0 if pd.isna(dlat) else float(dlat)
        dlon = 0.0 if pd.isna(dlon) else float(dlon)
        dalt = 0.0 if pd.isna(dalt) else float(dalt)

        lat = float(valid_before.iloc[-1]["lat"])
        lon = float(valid_before.iloc[-1]["lon"])
        alt = float(valid_before.iloc[-1]["altitude"])

        for i in range(gap_len):
            lat += dlat
            lon += dlon
            alt = max(0.0, alt + dalt)

            idx = gap_start + i
            filled.at[idx, "lat"] = lat
            filled.at[idx, "lon"] = lon
            filled.at[idx, "altitude"] = alt

    for col in ["velocity", "heading", "vertical_rate"]:
        if col in filled.columns:
            filled[col] = filled[col].interpolate(
                method="linear", limit_direction="both"
            ).ffill().bfill()

    return filled


def constant_velocity_predict_gap(
    context_df: pd.DataFrame,
    gap_length: int,
    history_points: int = 3,
) -> pd.DataFrame:
    if len(context_df) < 2:
        raise ValueError("Need at least 2 context points for constant-velocity prediction.")

    work = context_df[["lat", "lon", "altitude"]].copy().dropna().reset_index(drop=True)
    if len(work) < 2:
        raise ValueError("Context does not contain enough valid points.")

    hist = work.tail(history_points + 1)
    dlat = hist["lat"].diff().dropna().mean()
    dlon = hist["lon"].diff().dropna().mean()
    dalt = hist["altitude"].diff().dropna().mean()

    dlat = 0.0 if pd.isna(dlat) else float(dlat)
    dlon = 0.0 if pd.isna(dlon) else float(dlon)
    dalt = 0.0 if pd.isna(dalt) else float(dalt)

    lat = float(work.iloc[-1]["lat"])
    lon = float(work.iloc[-1]["lon"])
    alt = float(work.iloc[-1]["altitude"])

    preds = []
    for _ in range(gap_length):
        lat += dlat
        lon += dlon
        alt = max(0.0, alt + dalt)
        preds.append([lat, lon, alt])

    return pd.DataFrame(preds, columns=["lat", "lon", "altitude"])


def kalman_predict_gap(
    context_df: pd.DataFrame,
    gap_length: int,
    dt: float = 1.0,
    process_var: float = 1e-3,
    meas_var_pos: float = 1e-4,
    meas_var_alt: float = 25.0,
) -> pd.DataFrame:
    """
    Predict a future gap using a simple constant-velocity Kalman filter.

    Uses only the past context:
      state x = [lat, lon, alt, v_lat, v_lon, v_alt]

    Args:
        context_df: clean trajectory points before the gap
        gap_length: number of future missing points
        dt: time step in resampled units
        process_var: motion uncertainty
        meas_var_pos: measurement noise for lat/lon
        meas_var_alt: measurement noise for altitude

    Returns:
        DataFrame with predicted lat/lon/altitude for the gap
    """
    work = context_df[["lat", "lon", "altitude"]].copy().dropna().reset_index(drop=True)
    if len(work) < 2:
        raise ValueError("Need at least 2 context points for Kalman prediction.")

    x = _init_kalman_state(work)
    P = np.eye(6, dtype=float)

    F = np.array([
        [1, 0, 0, dt, 0,  0],
        [0, 1, 0, 0,  dt, 0],
        [0, 0, 1, 0,  0,  dt],
        [0, 0, 0, 1,  0,  0],
        [0, 0, 0, 0,  1,  0],
        [0, 0, 0, 0,  0,  1],
    ], dtype=float)

    H = np.array([
        [1, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0],
    ], dtype=float)

    Q = process_var * np.array([
        [dt**4 / 4, 0, 0, dt**3 / 2, 0, 0],
        [0, dt**4 / 4, 0, 0, dt**3 / 2, 0],
        [0, 0, dt**4 / 4, 0, 0, dt**3 / 2],
        [dt**3 / 2, 0, 0, dt**2, 0, 0],
        [0, dt**3 / 2, 0, 0, dt**2, 0],
        [0, 0, dt**3 / 2, 0, 0, dt**2],
    ], dtype=float)

    R = np.diag([meas_var_pos, meas_var_pos, meas_var_alt]).astype(float)

    # Filter over context observations
    for _, row in work.iterrows():
        z = np.array([row["lat"], row["lon"], row["altitude"]], dtype=float)
        x, P = _kalman_predict(x, P, F, Q)
        x, P = _kalman_update(x, P, z, H, R)

    # Forecast the missing steps
    preds = []
    for _ in range(gap_length):
        x, P = _kalman_predict(x, P, F, Q)

        lat = float(np.clip(x[0], -90.0, 90.0))
        lon = float(np.clip(x[1], -180.0, 180.0))
        alt = float(max(0.0, x[2]))

        preds.append([lat, lon, alt])

    return pd.DataFrame(preds, columns=["lat", "lon", "altitude"])


def kalman_fill_gap_offline(
    gapped_df: pd.DataFrame,
    history_points: int = 6,
    dt: float = 1.0,
    blend_with_endpoint: float = 0.15,
) -> pd.DataFrame:
    """
    Offline gap reconstruction using a Kalman-style predictor plus light endpoint blending.

    This version is useful when you have the full gapped trajectory and want to reconstruct
    the missing block(s). It:
      1. predicts through the gap from the left context using Kalman
      2. if a right endpoint exists, lightly blends predictions toward it

    Args:
        gapped_df: DataFrame with NaNs in gap rows
        history_points: recent valid samples used as context
        dt: time step in resampled units
        blend_with_endpoint: 0.0 = no endpoint blend, 1.0 = full linear pull

    Returns:
        DataFrame with gap rows filled
    """
    filled = gapped_df.copy().reset_index(drop=True)

    if "altitude" not in filled.columns:
        filled["altitude"] = 0.0

    is_gap = filled["lat"].isna() | filled["lon"].isna()
    if not is_gap.any():
        return filled

    gap_indices = np.where(is_gap.to_numpy())[0]
    blocks = _group_consecutive_indices(gap_indices)

    for block in blocks:
        gap_start = block[0]
        gap_end = block[-1]
        gap_len = len(block)

        left_ctx = filled.iloc[:gap_start].dropna(subset=["lat", "lon", "altitude"]).tail(history_points)
        if len(left_ctx) < 2:
            continue

        pred_df = kalman_predict_gap(left_ctx, gap_len, dt=dt)

        right_idx = gap_end + 1
        has_right = right_idx < len(filled) and pd.notna(filled.loc[right_idx, "lat"]) and pd.notna(filled.loc[right_idx, "lon"])

        if has_right and blend_with_endpoint > 0:
            end_lat = float(filled.loc[right_idx, "lat"])
            end_lon = float(filled.loc[right_idx, "lon"])
            end_alt = float(filled.loc[right_idx, "altitude"]) if "altitude" in filled.columns else 0.0

            start_lat = float(pred_df.iloc[0]["lat"])
            start_lon = float(pred_df.iloc[0]["lon"])
            start_alt = float(pred_df.iloc[0]["altitude"])

            for i in range(gap_len):
                alpha = (i + 1) / (gap_len + 1)

                linear_lat = (1 - alpha) * start_lat + alpha * end_lat
                linear_lon = (1 - alpha) * start_lon + alpha * end_lon
                linear_alt = (1 - alpha) * start_alt + alpha * end_alt

                pred_df.at[i, "lat"] = (
                    (1 - blend_with_endpoint) * pred_df.at[i, "lat"] +
                    blend_with_endpoint * linear_lat
                )
                pred_df.at[i, "lon"] = (
                    (1 - blend_with_endpoint) * pred_df.at[i, "lon"] +
                    blend_with_endpoint * linear_lon
                )
                pred_df.at[i, "altitude"] = max(
                    0.0,
                    (1 - blend_with_endpoint) * pred_df.at[i, "altitude"] +
                    blend_with_endpoint * linear_alt
                )

        for i, idx in enumerate(block):
            filled.at[idx, "lat"] = float(pred_df.iloc[i]["lat"])
            filled.at[idx, "lon"] = float(pred_df.iloc[i]["lon"])
            filled.at[idx, "altitude"] = float(pred_df.iloc[i]["altitude"])

    for col in ["velocity", "heading", "vertical_rate"]:
        if col in filled.columns:
            filled[col] = filled[col].interpolate(
                method="linear", limit_direction="both"
            ).ffill().bfill()

    return filled


def compute_path_length_km(df: pd.DataFrame) -> float:
    total = 0.0
    coords = list(zip(df["lat"], df["lon"]))
    for i in range(len(coords) - 1):
        total += geodesic(coords[i], coords[i + 1]).km
    return total


def _group_consecutive_indices(indices: np.ndarray) -> list[list[int]]:
    if len(indices) == 0:
        return []

    groups = [[int(indices[0])]]
    for idx in indices[1:]:
        idx = int(idx)
        if idx == groups[-1][-1] + 1:
            groups[-1].append(idx)
        else:
            groups.append([idx])
    return groups


def _init_kalman_state(work: pd.DataFrame) -> np.ndarray:
    """
    Initialize [lat, lon, alt, v_lat, v_lon, v_alt] from recent context.
    """
    tail = work.tail(3).copy()

    lat = float(tail.iloc[-1]["lat"])
    lon = float(tail.iloc[-1]["lon"])
    alt = float(tail.iloc[-1]["altitude"])

    dlat = tail["lat"].diff().dropna().mean()
    dlon = tail["lon"].diff().dropna().mean()
    dalt = tail["altitude"].diff().dropna().mean()

    dlat = 0.0 if pd.isna(dlat) else float(dlat)
    dlon = 0.0 if pd.isna(dlon) else float(dlon)
    dalt = 0.0 if pd.isna(dalt) else float(dalt)

    return np.array([lat, lon, alt, dlat, dlon, dalt], dtype=float)


def _kalman_predict(x, P, F, Q):
    x_pred = F @ x
    P_pred = F @ P @ F.T + Q
    return x_pred, P_pred


def _kalman_update(x, P, z, H, R):
    y = z - (H @ x)
    S = H @ P @ H.T + R
    K = P @ H.T @ np.linalg.inv(S)
    x_new = x + K @ y
    I = np.eye(P.shape[0])
    P_new = (I - K @ H) @ P
    return x_new, P_new

def last_point_hold_predict_gap(
    context_df: pd.DataFrame,
    gap_length: int,
) -> pd.DataFrame:
    """
    Very weak baseline:
    repeat the last known point for the whole gap.
    """
    if len(context_df) < 1:
        raise ValueError("Need at least 1 context point.")

    last = context_df[["lat", "lon", "altitude"]].dropna().iloc[-1]

    preds = []
    for _ in range(gap_length):
        preds.append([
            float(last["lat"]),
            float(last["lon"]),
            float(last["altitude"]),
        ])

    return pd.DataFrame(preds, columns=["lat", "lon", "altitude"])