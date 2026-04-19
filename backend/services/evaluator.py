"""
evaluator.py
------------
Computes all trajectory prediction metrics.

Metrics (PDF Section 6, Step 5):
  - MAE:              Mean Absolute Error on lat/lon/altitude separately
  - RMSE:             Root Mean Square Error
  - Geodesic Error:   True geographic distance error in km (most meaningful)
  - Cross-track Error: Lateral deviation from the true path
  - Path Length Error: Difference in total route distance

These metrics let us compare: Baseline vs LSTM vs GRU.
"""

import numpy as np
import pandas as pd
from geopy.distance import geodesic
from typing import Optional


def compute_metrics(
    true_df: pd.DataFrame,
    pred_df: pd.DataFrame,
    label: str = "model"
) -> dict:
    """
    Compute all evaluation metrics between ground truth and predictions.

    Args:
        true_df: DataFrame with true lat, lon, altitude
        pred_df: DataFrame with predicted lat, lon, altitude
        label:   Identifier for this model (used in output dict)

    Returns:
        dict of metric_name -> value
    """
    assert len(true_df) == len(pred_df), "Must have equal length for comparison"

    true_lat = true_df["lat"].values
    true_lon = true_df["lon"].values
    pred_lat = pred_df["lat"].values
    pred_lon = pred_df["lon"].values

    # ── MAE / RMSE on coordinates ──────────────────────────────────────────
    lat_mae = float(np.mean(np.abs(true_lat - pred_lat)))
    lon_mae = float(np.mean(np.abs(true_lon - pred_lon)))
    lat_rmse = float(np.sqrt(np.mean((true_lat - pred_lat) ** 2)))
    lon_rmse = float(np.sqrt(np.mean((true_lon - pred_lon) ** 2)))

    # ── Geodesic (great-circle) position error in km ───────────────────────
    geo_errors = []
    for t_lat, t_lon, p_lat, p_lon in zip(true_lat, true_lon, pred_lat, pred_lon):
        try:
            dist = geodesic((t_lat, t_lon), (p_lat, p_lon)).km
        except Exception:
            dist = float("nan")
        geo_errors.append(dist)

    geo_errors = np.array(geo_errors)
    mean_geo_error_km = float(np.nanmean(geo_errors))
    max_geo_error_km = float(np.nanmax(geo_errors))
    p90_geo_error_km = float(np.nanpercentile(geo_errors, 90))

    # ── Altitude MAE (if available) ────────────────────────────────────────
    alt_mae = None
    if "altitude" in true_df.columns and "altitude" in pred_df.columns:
        alt_mae = float(np.mean(np.abs(
            true_df["altitude"].values - pred_df["altitude"].fillna(0).values
        )))

    # ── Path length error ──────────────────────────────────────────────────
    from services.baseline import compute_path_length_km
    true_path_km = compute_path_length_km(true_df)
    pred_path_km = compute_path_length_km(pred_df)
    path_length_error_km = abs(true_path_km - pred_path_km)

    return {
        "label": label,
        "lat_mae": lat_mae,
        "lon_mae": lon_mae,
        "lat_rmse": lat_rmse,
        "lon_rmse": lon_rmse,
        "mean_geodesic_error_km": mean_geo_error_km,
        "max_geodesic_error_km": max_geo_error_km,
        "p90_geodesic_error_km": p90_geo_error_km,
        "altitude_mae_m": alt_mae,
        "path_length_error_km": path_length_error_km,
        "geo_error_series": geo_errors.tolist(),  # for distribution plot
    }