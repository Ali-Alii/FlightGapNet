"""
predict.py
----------
Prediction endpoints: gap-filling and future trajectory prediction.
These endpoints use the locally saved dataset (CSV), not live OpenSky calls.
"""

import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import MODEL_DIR, SEQ_LEN
from ml.model import get_model
from ml.trainer import load_model
from ml.predictor import predict_gap
from services.preprocessor import clean_track
from services.gap_simulator import simulate_gaps
from services.baseline import great_circle_interpolate
from services.evaluator import compute_metrics
from data_loader import get_track_by_icao24, get_available_icao24_list

router = APIRouter(prefix="/predict", tags=["predict"])

# Cache loaded models in memory (avoid disk reads on every request)
_model_cache: dict = {}
_scaler_cache: dict = {}


def _get_loaded_model(model_type: str):
    if model_type not in _model_cache:
        model = get_model(model_type)
        model = load_model(model, model_type)
        _model_cache[model_type] = model

    scaler_path = MODEL_DIR / "scaler_params.json"
    if "scaler" not in _scaler_cache and scaler_path.exists():
        with open(scaler_path) as f:
            _scaler_cache["scaler"] = json.load(f)

    return _model_cache[model_type], _scaler_cache.get("scaler", {})


class PredictRequest(BaseModel):
    icao24: str
    model_type: str = "lstm"   # "lstm" or "gru"
    steps_ahead: int = 10      # reserved for future prediction support


@router.post("/trajectory")
def predict_trajectory(req: PredictRequest):
    """
    Main prediction endpoint.
    1. Load saved track for the given aircraft from CSV
    2. Clean the track
    3. Simulate a gap (for honest evaluation)
    4. Run baseline + model reconstruction on the gap
    5. Return predictions + evaluation metrics
    """
    try:
        raw_df = get_track_by_icao24(req.icao24)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="No local dataset found. Run collect_data.py first."
        )

    if raw_df.empty:
        raise HTTPException(status_code=404, detail=f"No track found for {req.icao24}")

    clean_df = clean_track(raw_df)
    if clean_df.empty or len(clean_df) < SEQ_LEN + 10:
        raise HTTPException(status_code=422, detail="Insufficient track data for prediction")

    try:
        model, scaler_params = _get_loaded_model(req.model_type)
    except (FileNotFoundError, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail=f"Model '{req.model_type}' not trained yet. Run scripts/train_models.py first."
        )

    # Simulate a gap for evaluation
    gapped_df, gap_truth = simulate_gaps(clean_df, seed=42)

    if gap_truth.empty:
        raise HTTPException(status_code=422, detail="Could not simulate gap in trajectory")

    # Find the gap region
    gap_mask = gapped_df["is_gap"]
    gap_start_idx = gap_mask.idxmax()
    gap_length = int(gap_mask.sum())

    # Context = points before the gap
    context_df = clean_df.iloc[max(0, gap_start_idx - SEQ_LEN): gap_start_idx]

    # Baseline prediction
    baseline_filled = great_circle_interpolate(gapped_df)
    baseline_gap_pred = baseline_filled.iloc[
        gap_start_idx: gap_start_idx + gap_length
    ][["lat", "lon", "altitude"]]

    # Model prediction
    model_pred_df = predict_gap(model, context_df, gap_length, scaler_params)
    

    # Metrics
    truth_subset = gap_truth[["lat", "lon", "altitude"]].reset_index(drop=True)

    baseline_metrics = compute_metrics(
        truth_subset,
        baseline_gap_pred.reset_index(drop=True),
        "baseline"
    )
    model_metrics = compute_metrics(
        truth_subset,
        model_pred_df.reset_index(drop=True),
        req.model_type
    )

    return {
        "icao24": req.icao24,
        "model_type": req.model_type,
        "full_track": clean_df[["lat", "lon", "altitude"]].assign(
            time=clean_df["time"].astype(str)
        ).to_dict(orient="records"),
        "gap_region": {
            "start_idx": int(gap_start_idx),
            "length": gap_length,
        },
        "true_gap": truth_subset.to_dict(orient="records"),
        "baseline_pred": baseline_gap_pred.reset_index(drop=True).to_dict(orient="records"),
        "model_pred": model_pred_df.to_dict(orient="records"),
        "metrics": {
            "baseline": {
                k: v for k, v in baseline_metrics.items() if k != "geo_error_series"
            },
            req.model_type: {
                k: v for k, v in model_metrics.items() if k != "geo_error_series"
            },
        },
        "geo_error_distribution": {
            "baseline": baseline_metrics["geo_error_series"],
            req.model_type: model_metrics["geo_error_series"],
        },
    }


@router.get("/model-history/{model_type}")
def get_model_history(model_type: str):
    """Return training loss history for dashboard charts."""
    path = MODEL_DIR / f"{model_type}_history.json"
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="Model history not found. Train the model first."
        )
    with open(path) as f:
        return json.load(f)


@router.get("/available-aircraft")
def available_aircraft():
    """Return all aircraft IDs available in the local CSV dataset."""
    try:
        return {"icao24_list": get_available_icao24_list()}
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="No local dataset found. Run collect_data.py first."
        )