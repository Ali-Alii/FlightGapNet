import pandas as pd
import numpy as np


def simulate_gaps(
    df: pd.DataFrame,
    min_gap: int = 2,
    max_gap: int = 4,
    edge_buffer: int = 5,
    seed: int | None = None,
    max_tries: int = 20,
):
    """
    Create one random safe gap in the trajectory.

    Rules:
    - gap must stay away from the edges
    - gap length is between min_gap and max_gap
    - gap should not be static (lat/lon unchanged through the removed segment)

    Returns:
        gapped_df: original dataframe with gap inserted and 'is_gap' column
        gap_truth: true removed points
    """
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if seed is not None:
        np.random.seed(seed)

    df = df.copy().reset_index(drop=True)
    n = len(df)
    df["is_gap"] = False

    required_cols = ["lat", "lon", "altitude"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"simulate_gaps: missing required column '{col}'")

    min_required = max(15, edge_buffer * 2 + min_gap + 1)
    if n < min_required:
        return df, pd.DataFrame()

    max_gap = min(max_gap, n - 2 * edge_buffer - 1)
    if max_gap < min_gap:
        return df, pd.DataFrame()

    start_low = edge_buffer
    start_high = n - edge_buffer - min_gap
    if start_high <= start_low:
        return df, pd.DataFrame()

    for _ in range(max_tries):
        gap_length = np.random.randint(min_gap, max_gap + 1)

        start_high_for_len = n - edge_buffer - gap_length
        if start_high_for_len <= start_low:
            continue

        start = np.random.randint(start_low, start_high_for_len + 1)
        gap_idx = list(range(start, start + gap_length))

        gap_truth = df.iloc[gap_idx].copy()

        # Skip invalid or static gaps
        if gap_truth.empty:
            continue

        # Remove rows with NaNs before checking movement
        moving_check = gap_truth[["lat", "lon"]].dropna()
        if len(moving_check) < 2:
            continue

        lat_std = moving_check["lat"].std()
        lon_std = moving_check["lon"].std()

        if pd.isna(lat_std):
            lat_std = 0.0
        if pd.isna(lon_std):
            lon_std = 0.0

        # Skip static gaps
        if lat_std < 1e-6 and lon_std < 1e-6:
            continue

        gapped_df = df.copy()
        gapped_df.loc[gap_idx, ["lat", "lon", "altitude"]] = np.nan
        gapped_df.loc[gap_idx, "is_gap"] = True

        return gapped_df, gap_truth

    # If no valid moving gap was found
    return df, pd.DataFrame()