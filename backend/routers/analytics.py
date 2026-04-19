"""
analytics.py
------------
Route analytics endpoints (PDF Section 6, Step 6).
"Show why better tracks matter" — compute route metrics from reconstructed trajectories.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.baseline import compute_path_length_km
import pandas as pd

router = APIRouter(prefix="/analytics", tags=["analytics"])


class RouteAnalyticsRequest(BaseModel):
    track: list[dict]   # list of {lat, lon, altitude}


@router.post("/route")
async def compute_route_analytics(req: RouteAnalyticsRequest):
    """
    Compute route-level analytics for a trajectory.
    Returns: total distance, average altitude, altitude profile,
             a simple fuel-proxy (distance × altitude factor), deviation score.
    """
    df = pd.DataFrame(req.track)
    if df.empty or "lat" not in df.columns:
        raise HTTPException(status_code=422, detail="Invalid track data")

    path_km = compute_path_length_km(df)
    avg_altitude_m = float(df["altitude"].mean()) if "altitude" in df.columns else 0.0

    # Simple emissions proxy: fuel ~ distance × (1 + 0.1 × altitude_factor)
    # This is illustrative, not physically accurate
    altitude_factor = avg_altitude_m / 10000.0
    fuel_proxy = path_km * (1 + 0.1 * altitude_factor)

    # Altitude profile for chart
    alt_profile = df["altitude"].fillna(0).tolist() if "altitude" in df.columns else []

    return {
        "path_length_km": round(path_km, 2),
        "avg_altitude_m": round(avg_altitude_m, 1),
        "fuel_proxy_index": round(fuel_proxy, 2),
        "altitude_profile": alt_profile,
        "point_count": len(df),
    }