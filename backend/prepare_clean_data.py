import pandas as pd
from pathlib import Path
from services.preprocessor import clean_track

RAW_PATH = Path(__file__).resolve().parent.parent / "data" / "raw" / "flights.csv"
CLEAN_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "cleaned_flights.csv"

def main():
    df = pd.read_csv(RAW_PATH)

    if "icao24" in df.columns:
        df["icao24"] = df["icao24"].astype(str).str.lower()

    cleaned_tracks = []

    for icao24, group in df.groupby("icao24"):
        clean_df = clean_track(group)
        if not clean_df.empty:
            clean_df["icao24"] = icao24
            cleaned_tracks.append(clean_df)

    if not cleaned_tracks:
        print("No cleaned tracks produced.")
        return

    final_df = pd.concat(cleaned_tracks, ignore_index=True)

    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(CLEAN_PATH, index=False)

    print(f"Saved {len(final_df)} rows to {CLEAN_PATH}")

if __name__ == "__main__":
    main()