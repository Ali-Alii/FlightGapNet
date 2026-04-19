import asyncio
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from services.opensky_client import OpenSkyClient

RAW_TRACKS_DIR = Path(__file__).resolve().parent.parent / "data" / "raw_tracks"
COMBINED_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
COMBINED_FILE = COMBINED_DIR / "flights.csv"

MIN_TRACK_POINTS = 20
MAX_TIME_GAP_SECONDS = 900

# ===== Rate-limit protection =====
MAX_AIRCRAFT_PER_RUN = 12
REQUEST_DELAY_SECONDS = 8
MAX_RETRIES_ON_429 = 2
BACKOFF_BASE_SECONDS = 30


def is_rate_limit_error(exc: Exception) -> bool:
    """Return True if exception looks like an HTTP 429 rate limit error."""
    text = str(exc).lower()
    if "429" in text or "too many requests" in text:
        return True

    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code == 429:
        return True

    return False


def is_good_track(track_df: pd.DataFrame) -> tuple[bool, str]:
    if track_df is None or track_df.empty:
        return False, "empty"

    if len(track_df) < MIN_TRACK_POINTS:
        return False, f"too short (< {MIN_TRACK_POINTS} points)"

    if "time" not in track_df.columns:
        return False, "missing time column"

    df = track_df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

    if len(df) < MIN_TRACK_POINTS:
        return False, f"too short after time cleaning (< {MIN_TRACK_POINTS} points)"

    time_gaps = df["time"].diff().dt.total_seconds().dropna()
    if not time_gaps.empty and time_gaps.max() > MAX_TIME_GAP_SECONDS:
        return False, (
            f"fragmented track (max gap {time_gaps.max():.0f}s > "
            f"{MAX_TIME_GAP_SECONDS}s)"
        )

    return True, "ok"


def rebuild_combined_file() -> None:
    """Rebuild flights.csv from everything currently saved in raw_tracks/."""
    all_tracks = []

    for csv_path in sorted(RAW_TRACKS_DIR.glob("*.csv")):
        try:
            df = pd.read_csv(csv_path, parse_dates=["time"])
            if not df.empty:
                all_tracks.append(df)
        except Exception as e:
            print(f"  Skipping bad saved file {csv_path.name}: {e}")

    if not all_tracks:
        print("No saved tracks found to rebuild combined file.")
        return

    combined_df = pd.concat(all_tracks, ignore_index=True)
    combined_df = combined_df.sort_values(["icao24", "time"]).reset_index(drop=True)
    combined_df.to_csv(COMBINED_FILE, index=False)

    print(f"\nRebuilt combined file with {len(combined_df)} total rows")
    print(f"Saved combined dataset to {COMBINED_FILE}")


async def fetch_track_with_retry(client: OpenSkyClient, icao24: str):
    """
    Fetch one aircraft track with retry/backoff on HTTP 429.
    Returns:
        ("success", track_df)
        ("empty", None)
        ("rate_limited", None)
        ("error", None)
    """
    for attempt in range(1, MAX_RETRIES_ON_429 + 1):
        try:
            track_df = await client.get_track_by_aircraft(icao24)

            if track_df is None or track_df.empty:
                return "empty", None

            return "success", track_df

        except Exception as e:
            if is_rate_limit_error(e):
                wait_time = BACKOFF_BASE_SECONDS * attempt
                print(
                    f"  Rate limited for {icao24} (attempt {attempt}/{MAX_RETRIES_ON_429}). "
                    f"Waiting {wait_time}s before retry..."
                )
                await asyncio.sleep(wait_time)
                continue

            print(f"  Non-rate-limit error for {icao24}: {e}")
            return "error", None

    return "rate_limited", None


async def collect_data():
    client = OpenSkyClient()

    states_df = await client.get_live_states()

    if states_df is None or states_df.empty:
        print("No aircraft states found.")
        return

    if "icao24" not in states_df.columns:
        print("No 'icao24' column found in live states.")
        print("Available columns:", states_df.columns.tolist())
        return

    icao24_list = (
        states_df["icao24"]
        .dropna()
        .astype(str)
        .str.lower()
        .unique()
        .tolist()
    )

    print(f"Found {len(icao24_list)} aircraft IDs")

    RAW_TRACKS_DIR.mkdir(parents=True, exist_ok=True)
    COMBINED_DIR.mkdir(parents=True, exist_ok=True)

    # Remove already collected aircraft first
    pending_icao24 = []
    already_existing_count = 0

    for icao24 in icao24_list:
        per_aircraft_file = RAW_TRACKS_DIR / f"{icao24}.csv"
        if per_aircraft_file.exists():
            already_existing_count += 1
        else:
            pending_icao24.append(icao24)

    if not pending_icao24:
        print("All currently found aircraft were already collected.")
        rebuild_combined_file()
        return

    # Limit requests per run to reduce rate limiting
    pending_icao24 = pending_icao24[:MAX_AIRCRAFT_PER_RUN]

    print(f"Will try to collect {len(pending_icao24)} new aircraft in this run")
    print(f"Already existing tracks skipped: {already_existing_count}")

    kept_count = 0
    skipped_bad_count = 0
    skipped_empty_count = 0
    rate_limited_count = 0
    error_count = 0

    for i, icao24 in enumerate(pending_icao24, start=1):
        per_aircraft_file = RAW_TRACKS_DIR / f"{icao24}.csv"

        print(f"\n[{i}/{len(pending_icao24)}] Collecting {icao24}...")

        status, track_df = await fetch_track_with_retry(client, icao24)

        if status == "rate_limited":
            print(f"  Skipped {icao24}: still rate-limited after retries")
            rate_limited_count += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        if status == "error":
            print(f"  Skipped {icao24}: request failed")
            error_count += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        if status == "empty":
            print(f"  No track for {icao24}")
            skipped_empty_count += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        track_df["icao24"] = icao24

        rename_map = {}
        if "latitude" in track_df.columns and "lat" not in track_df.columns:
            rename_map["latitude"] = "lat"
        if "longitude" in track_df.columns and "lon" not in track_df.columns:
            rename_map["longitude"] = "lon"
        if "geo_altitude" in track_df.columns and "altitude" not in track_df.columns:
            rename_map["geo_altitude"] = "altitude"
        if rename_map:
            track_df = track_df.rename(columns=rename_map)

        wanted = ["icao24", "time", "lat", "lon", "altitude", "velocity"]
        existing = [c for c in wanted if c in track_df.columns]
        track_df = track_df[existing].copy()

        required = ["icao24", "time", "lat", "lon"]
        existing_required = [c for c in required if c in track_df.columns]
        track_df = track_df.dropna(subset=existing_required).drop_duplicates()

        if track_df.empty:
            print(f"  Empty after cleaning: {icao24}")
            skipped_bad_count += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        track_df["time"] = pd.to_datetime(track_df["time"], errors="coerce")
        track_df = track_df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)

        ok, reason = is_good_track(track_df)
        if not ok:
            print(f"  Skipped {icao24}: {reason}")
            skipped_bad_count += 1
            await asyncio.sleep(REQUEST_DELAY_SECONDS)
            continue

        track_df.to_csv(per_aircraft_file, index=False)

        kept_count += 1

        print(f"  Collected {len(track_df)} rows")
        print(f"  Saved to {per_aircraft_file}")

        await asyncio.sleep(REQUEST_DELAY_SECONDS)

    print(
        f"\nCollection summary:"
        f"\n  New good tracks kept: {kept_count}"
        f"\n  Empty/no tracks: {skipped_empty_count}"
        f"\n  Bad tracks after cleaning/validation: {skipped_bad_count}"
        f"\n  Rate-limited after retries: {rate_limited_count}"
        f"\n  Other request errors: {error_count}"
        f"\n  Already existing tracks skipped: {already_existing_count}"
    )

    rebuild_combined_file()


if __name__ == "__main__":
    asyncio.run(collect_data())