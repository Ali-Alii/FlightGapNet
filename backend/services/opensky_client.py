"""
opensky_client.py
-----------------
Wrapper around the OpenSky REST API using OAuth2 client credentials.

OpenSky now requires OAuth2 client-credentials auth for authenticated access.
Basic auth with username/password is no longer accepted.
"""

import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import OPENSKY_BASE_URL, OPENSKY_CLIENT_ID, OPENSKY_CLIENT_SECRET

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/"
    "opensky-network/protocol/openid-connect/token"
)
TOKEN_REFRESH_MARGIN_SECONDS = 30


class OpenSkyClient:
    """Async HTTP client for the OpenSky REST API."""

    def __init__(self):
        self.base_url = OPENSKY_BASE_URL
        self.client_id = OPENSKY_CLIENT_ID
        self.client_secret = OPENSKY_CLIENT_SECRET
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def _has_valid_token(self) -> bool:
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now(timezone.utc) < self.token_expires_at

    async def _refresh_token(self) -> str:
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Missing OpenSky OAuth credentials. "
                "Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in config.py."
            )

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(TOKEN_URL, data=data)
            resp.raise_for_status()
            token_data = resp.json()

        self.access_token = token_data["access_token"]
        expires_in = int(token_data.get("expires_in", 1800))
        self.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=max(1, expires_in - TOKEN_REFRESH_MARGIN_SECONDS)
        )
        return self.access_token

    async def _get_headers(self) -> dict:
        if not self._has_valid_token():
            await self._refresh_token()
        return {"Authorization": f"Bearer {self.access_token}"}

    async def _authorized_get(self, url: str, params: Optional[dict] = None) -> httpx.Response:
        headers = await self._get_headers()

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            resp = await client.get(url, params=params)

            # If token expired unexpectedly, refresh once and retry once.
            if resp.status_code == 401:
                await self._refresh_token()
                headers = await self._get_headers()
                resp = await client.get(url, params=params, headers=headers)

        return resp

    async def get_live_states(
        self,
        lat_min: float = -90,
        lat_max: float = 90,
        lon_min: float = -180,
        lon_max: float = 180,
        limit: int = 200,
    ) -> pd.DataFrame:
        """
        Fetch current ADS-B state vectors for all aircraft in a bounding box.
        Returns a DataFrame with one row per aircraft.
        """
        params = {
            "lamin": lat_min,
            "lamax": lat_max,
            "lomin": lon_min,
            "lomax": lon_max,
        }

        resp = await self._authorized_get(f"{self.base_url}/states/all", params=params)
        resp.raise_for_status()
        data = resp.json()

        if not data or not data.get("states"):
            return pd.DataFrame()

        columns = [
            "icao24",
            "callsign",
            "origin_country",
            "time_position",
            "last_contact",
            "longitude",
            "latitude",
            "baro_altitude",
            "on_ground",
            "velocity",
            "true_track",
            "vertical_rate",
            "sensors",
            "geo_altitude",
            "squawk",
            "spi",
            "position_source",
        ]

        df = pd.DataFrame(data["states"][:limit], columns=columns)
        df = df[df["on_ground"] == False].copy()
        df["callsign"] = df["callsign"].fillna("").astype(str).str.strip()
        return df

    async def get_track_by_aircraft(
        self, icao24: str, begin_time: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Fetch the full track for a specific aircraft.

        Args:
            icao24: The 24-bit ICAO address (hex string, e.g. 'a0b1c2')
            begin_time: Unix timestamp of track start; None = most recent track

        Returns:
            DataFrame with columns: time, lat, lon, altitude, velocity,
                                    heading, vertical_rate
        """
        params = {"icao24": icao24.lower()}
        if begin_time is not None:
            params["time"] = begin_time

        resp = await self._authorized_get(f"{self.base_url}/tracks/all", params=params)

        if resp.status_code == 404:
            return pd.DataFrame()

        # Useful debug if you still hit limits:
        if resp.status_code == 429:
            remaining = resp.headers.get("X-Rate-Limit-Remaining")
            retry_after = resp.headers.get("X-Rate-Limit-Retry-After-Seconds")
            print(
                f"  OpenSky 429 for {icao24} | remaining={remaining} | "
                f"retry_after={retry_after}s"
            )

        resp.raise_for_status()
        data = resp.json()

        if not data or not data.get("path"):
            return pd.DataFrame()

        rows = data["path"]
        df = pd.DataFrame(
            rows,
            columns=["time", "lat", "lon", "altitude", "heading", "on_ground"],
        )

        df = df[df["on_ground"] == False].copy()
        df["icao24"] = icao24
        df["callsign"] = str(data.get("callsign", "")).strip()

        if "velocity" not in df.columns:
            df["velocity"] = np.nan
        if "vertical_rate" not in df.columns:
            df["vertical_rate"] = np.nan

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df.sort_values("time").reset_index(drop=True)
        return df

    async def search_flights_by_callsign(self, callsign: str) -> list[dict]:
        """
        Search for recent flights matching a callsign pattern.
        """
        df = await self.get_live_states(limit=1000)
        if df.empty:
            return []

        mask = df["callsign"].str.upper().str.contains(callsign.upper(), na=False)
        matches = df[mask][["icao24", "callsign", "origin_country"]].copy()
        return matches.to_dict(orient="records")