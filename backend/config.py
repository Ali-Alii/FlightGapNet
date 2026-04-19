"""Central configuration for AeroTrack backend and ML pipeline."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BACKEND_DIR / "saved_models"
RAW_TRACKS_DIR = DATA_DIR / "raw_tracks"

DATA_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)
RAW_TRACKS_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{DATA_DIR}/aerotrack.db"

OPENSKY_BASE_URL = "https://opensky-network.org/api"
OPENSKY_CLIENT_ID = "batoul.nasser@net.usj.edu.lb-api-client"
OPENSKY_CLIENT_SECRET = "VzX2h4C1dkYTT86ImLYZzJNdXrHSqMtT"

# Preprocessing
RESAMPLE_INTERVAL_SECONDS = 30
MIN_TRACK_POINTS = 12
MAX_SPEED_KNOTS = 700
MAX_ALTITUDE_FT = 60000
OUTLIER_Z_SCORE = 3.0

# Gap simulation
GAP_FRACTION = 0.20
MIN_GAP_DURATION = 8 
MAX_GAP_DURATION = 12

# Model hyperparameters
SEQ_LEN = 12
PRED_LEN = 12 
HIDDEN_SIZE = 128
NUM_LAYERS = 2
DROPOUT = 0.2
BATCH_SIZE = 32
LEARNING_RATE = 7e-4
WEIGHT_DECAY = 1e-5
NUM_EPOCHS = 80
GRAD_CLIP = 1.0
RANDOM_SEED = 42

# Input features must exactly match what preprocessor computes.
FEATURE_COLS = [
    "delta_lat",
    "delta_lon",
    "delta_alt",
    "speed_knots",
    "heading_sin",
    "heading_cos",
]

# Predict motion deltas, then reconstruct absolute positions from the last known point.
TARGET_COLS = ["delta_lat", "delta_lon", "delta_alt"]
