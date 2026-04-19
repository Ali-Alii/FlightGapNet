import sys
from pathlib import Path

# Add project root: aerotrack/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_loader import get_track_by_icao24
from backend.services.preprocessor import clean_track
import matplotlib.pyplot as plt

icao24 = "a36898"  # change if needed

raw = get_track_by_icao24(icao24)
clean = clean_track(raw)

print("RAW rows:", len(raw))
print("CLEAN rows:", len(clean))

print(clean[["time", "lat", "lon", "altitude"]].head(20))
print(clean[["delta_lat", "delta_lon"]].describe())

plt.plot(clean["lon"], clean["lat"])
plt.title(f"Trajectory for {icao24}")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()