"""
flights.py
----------
FastAPI router for flight data endpoints.
Handles fetching, storing, and retrieving flight trajectories.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from database import get_db
from models.db_models import Flight, TrajectoryPoint
from services.opensky_client import OpenSkyClient
from services.preprocessor import clean_track

router = APIRouter(prefix="/flights", tags=["flights"])
client = OpenSkyClient()


@router.get("/live")
async def get_live_flights(
    lat_min: float = Query(30.0),
    lat_max: float = Query(50.0),
    lon_min: float = Query(-10.0),
    lon_max: float = Query(40.0),
):
    """
    Fetch current live ADS-B state vectors for flights in a bounding box.
    Default box covers Europe.
    """
    df = await client.get_live_states(lat_min, lat_max, lon_min, lon_max, limit=100)
    if df.empty:
        return {"flights": [], "count": 0}

    flights = df[["icao24", "callsign", "origin_country", "latitude", "longitude"]].to_dict(orient="records")
    return {"flights": flights, "count": len(flights)}


@router.get("/track/{icao24}")
async def get_flight_track(icao24: str, db: AsyncSession = Depends(get_db)):
    """
    Fetch, clean, and store the full track for an aircraft ICAO24 address.
    Returns the cleaned trajectory as a list of position points.
    """
    raw_df = await client.get_track_by_aircraft(icao24)
    if raw_df.empty:
        raise HTTPException(status_code=404, detail=f"No track found for {icao24}")

    clean_df = clean_track(raw_df)
    if clean_df.empty:
        raise HTTPException(status_code=422, detail="Track too short after cleaning")

    # Upsert flight record
    result = await db.execute(select(Flight).where(Flight.icao24 == icao24))
    flight = result.scalar_one_or_none()
    if not flight:
        flight = Flight(
            icao24=icao24,
            callsign=raw_df["callsign"].iloc[0] if "callsign" in raw_df.columns else "",
            first_seen=clean_df["time"].iloc[0],
            last_seen=clean_df["time"].iloc[-1],
            point_count=len(clean_df),
        )
        db.add(flight)
        await db.flush()
    else:
        flight.point_count = len(clean_df)
        flight.last_seen = clean_df["time"].iloc[-1]

    # Store trajectory points
    points = [
        TrajectoryPoint(
            flight_id=flight.id,
            timestamp=row["time"],
            lat=row["lat"],
            lon=row["lon"],
            altitude=row.get("altitude"),
            velocity=row.get("velocity"),
            heading=row.get("heading"),
            vertical_rate=row.get("vertical_rate"),
        )
        for _, row in clean_df.iterrows()
    ]
    db.add_all(points)
    await db.commit()

    return {
        "icao24": icao24,
        "callsign": flight.callsign,
        "point_count": len(clean_df),
        "track": clean_df[["time", "lat", "lon", "altitude", "velocity", "heading"]].assign(
            time=lambda d: d["time"].astype(str)
        ).to_dict(orient="records"),
    }


@router.get("/search")
async def search_flights(q: str = Query(..., min_length=3)):
    """Search for flights by callsign substring in live data."""
    matches = await client.search_flights_by_callsign(q)
    return {"results": matches, "count": len(matches)}