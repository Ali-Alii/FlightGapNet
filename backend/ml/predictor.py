"""Inference utilities for trajectory gap filling."""

import numpy as np
import pandas as pd
import torch
from torch import nn

from config import FEATURE_COLS, PRED_LEN, SEQ_LEN, TARGET_COLS


def _check_scaler_params(scaler_params: dict):
    needed = set(FEATURE_COLS) | set(TARGET_COLS)
    for col in needed:
        if col not in scaler_params:
            raise ValueError(f"'{col}' missing from scaler_params. Delete saved_models/ and retrain.")
        p = scaler_params[col]
        if "min" not in p or "max" not in p:
            raise ValueError(f"scaler_params['{col}'] is malformed: {p}")
        if not np.isfinite(p["min"]) or not np.isfinite(p["max"]):
            raise ValueError(f"scaler_params['{col}'] has non-finite bounds {p}")


def _build_autoregressive_rows(current_context: np.ndarray, pred_steps: np.ndarray) -> np.ndarray:
    last_row = current_context[-1].copy()
    new_rows = np.tile(last_row, (len(pred_steps), 1))

    for i, col in enumerate(TARGET_COLS):
        if col in FEATURE_COLS:
            fi = FEATURE_COLS.index(col)
            new_rows[:, fi] = pred_steps[:, i]

    return new_rows


def _target_bounds(scaler_params: dict) -> list[tuple[float, float]]:
    bounds = []
    for col in TARGET_COLS:
        p = scaler_params[col]
        bounds.append((float(p["min"]), float(p["max"])))
    return bounds


def predict_gap(model: nn.Module, context_df: pd.DataFrame, gap_length: int, scaler_params: dict) -> pd.DataFrame:
    from services.preprocessor import denormalize_targets, normalize_features

    device = next(model.parameters()).device
    model.eval()

    if len(context_df) < SEQ_LEN:
        raise ValueError(f"Context needs >= SEQ_LEN={SEQ_LEN} rows, got {len(context_df)}")

    for col in ["lat", "lon", "altitude"]:
        if col not in context_df.columns:
            raise ValueError(f"context_df missing required absolute column '{col}'")

    _check_scaler_params(scaler_params)
    norm_context, _ = normalize_features(context_df.copy(), scaler_params)

    for col in FEATURE_COLS:
        if col not in norm_context.columns:
            norm_context[col] = 0.0

    current_context = norm_context[FEATURE_COLS].to_numpy(dtype=np.float32)[-SEQ_LEN:]
    if not np.isfinite(current_context).all():
        raise ValueError("NaN or inf found in model input after normalization.")

    all_preds = []
    remaining = gap_length
    while remaining > 0:
        x = torch.tensor(current_context[np.newaxis], dtype=torch.float32).to(device)
        with torch.no_grad():
            out = model(x)
        pred = out.squeeze(0).cpu().numpy()

        if not np.isfinite(pred).all():
            raise ValueError("Model produced NaN/inf output. Delete saved_models/ and retrain.")

        steps = min(remaining, PRED_LEN)
        step_pred = np.clip(pred[:steps], 0.0, 1.0)
        all_preds.append(step_pred)
        remaining -= steps

        if remaining > 0:
            new_rows = _build_autoregressive_rows(current_context, step_pred)
            current_context = np.vstack([current_context[steps:], new_rows])

    predicted_norm = np.vstack(all_preds)
    predicted_deltas = denormalize_targets(predicted_norm, scaler_params)
    bounds = _target_bounds(scaler_params)

    lat = float(context_df.iloc[-1]["lat"])
    lon = float(context_df.iloc[-1]["lon"])
    alt = float(context_df.iloc[-1]["altitude"])

    positions = []
    for row in predicted_deltas:
        dlat = float(np.clip(row[0], bounds[0][0], bounds[0][1]))
        dlon = float(np.clip(row[1], bounds[1][0], bounds[1][1]))
        dalt = float(np.clip(row[2], bounds[2][0], bounds[2][1]))

        lat = float(np.clip(lat + dlat, -90.0, 90.0))
        lon = float(np.clip(lon + dlon, -180.0, 180.0))
        alt = float(max(0.0, alt + dalt))
        positions.append([lat, lon, alt])

    result_df = pd.DataFrame(positions, columns=["lat", "lon", "altitude"])
    if result_df.isna().any().any():
        raise ValueError("Predicted output contains NaN after reconstruction.")
    return result_df


def predict_future(model, context_df, steps_ahead, scaler_params):
    return predict_gap(model, context_df, steps_ahead, scaler_params)
