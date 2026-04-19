import asyncio
from pathlib import Path
import pandas as pd

from services.opensky_client import OpenSkyClient

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "flights.csv"


async def main():
    client = OpenSkyClient()

    # Step 1: get all visible aircraft / states
    states_df = await client.get_current_states()   # you need this method in your client

    if states_df is None or states_df.empty:
        print("No aircraft states found.")
        return

    # Step 2: keep valid aircraft ids
    if "icao24" not in states_df.columns:
        print("No 'icao24' column found in current states.")
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

    all_tracks = []

    # Step 3: collect track for each aircraft
    for icao24 in icao24_list:
        try:
            track_df = await client.get_track_by_aircraft(icao24)

            if track_df is not None and not track_df.empty:
                track_df["icao24"] = icao24
                all_tracks.append(track_df)
                print(f"Collected {len(track_df)} rows for {icao24}")
            else:
                print(f"No track for {icao24}")

        except Exception as e:
            print(f"Error for {icao24}: {e}")

    if not all_tracks:
        print("No tracks collected.")
        return

    combined_df = pd.concat(all_tracks, ignore_index=True)

    # rename if needed
    rename_map = {}
    if "latitude" in combined_df.columns and "lat" not in combined_df.columns:
        rename_map["latitude"] = "lat"
    if "longitude" in combined_df.columns and "lon" not in combined_df.columns:
        rename_map["longitude"] = "lon"
    if "geo_altitude" in combined_df.columns and "altitude" not in combined_df.columns:
        rename_map["geo_altitude"] = "altitude"

    if rename_map:
        combined_df = combined_df.rename(columns=rename_map)

    # keep useful columns only if they exist
    wanted = ["icao24", "time", "lat", "lon", "altitude", "velocity"]
    existing = [c for c in wanted if c in combined_df.columns]
    combined_df = combined_df[existing].copy()

    combined_df = combined_df.drop_duplicates()
    required = [c for c in ["icao24", "time", "lat", "lon"] if c in combined_df.columns]
    combined_df = combined_df.dropna(subset=required)
    combined_df = combined_df.sort_values(["icao24", "time"])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined_df.to_csv(OUTPUT_FILE, index=False)

    print(f"Saved {len(combined_df)} rows to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())