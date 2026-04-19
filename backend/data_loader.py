import pandas as pd
from config import RAW_TRACKS_DIR

def get_track_by_icao24(icao24: str) -> pd.DataFrame:
    path = RAW_TRACKS_DIR / f"{icao24.lower()}.csv"
    if not path.exists():
        raise FileNotFoundError(f"No track file for {icao24}: {path}")
    df = pd.read_csv(path, parse_dates=["time"])
    return df.sort_values("time").reset_index(drop=True)


def get_available_icao24_list() -> list[str]:
    if not RAW_TRACKS_DIR.exists():
        return []
    return sorted(p.stem for p in RAW_TRACKS_DIR.glob("*.csv"))