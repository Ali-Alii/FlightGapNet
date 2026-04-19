"""PyTorch dataset for trajectory delta prediction."""

import random
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, Dataset

from config import BATCH_SIZE, FEATURE_COLS, PRED_LEN, RANDOM_SEED, SEQ_LEN, TARGET_COLS


class TrajectoryDataset(Dataset):
    def __init__(self, trajectories: list[pd.DataFrame], samples_per_track: int | None = None):
        self.samples: list[tuple[np.ndarray, np.ndarray]] = []
        self._build(trajectories, samples_per_track)

    def _build(self, trajectories: list[pd.DataFrame], samples_per_track: int | None):
        window = SEQ_LEN + PRED_LEN
        rng = np.random.default_rng(RANDOM_SEED)

        for df in trajectories:
            if len(df) < window:
                continue

            work = df.copy().reset_index(drop=True)
            for col in FEATURE_COLS + TARGET_COLS:
                if col not in work.columns:
                    work[col] = 0.0

            feat = work[FEATURE_COLS].to_numpy(dtype=np.float32)
            tgt = work[TARGET_COLS].to_numpy(dtype=np.float32)

            valid_windows = []
            for i in range(len(work) - window + 1):
                x = feat[i : i + SEQ_LEN]
                y = tgt[i + SEQ_LEN : i + window]
                if np.isfinite(x).all() and np.isfinite(y).all():
                    valid_windows.append((x, y))

            if not valid_windows:
                continue

            if samples_per_track is None or len(valid_windows) <= samples_per_track:
                chosen = valid_windows
            else:
                idx = rng.choice(len(valid_windows), size=samples_per_track, replace=False)
                chosen = [valid_windows[i] for i in idx]

            self.samples.extend(chosen)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx: int):
        x, y = self.samples[idx]
        return torch.tensor(x, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)


def build_dataloaders(
    trajectories: list[pd.DataFrame],
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> tuple[DataLoader, DataLoader, DataLoader]:
    rng = random.Random(RANDOM_SEED)
    trajectories = list(trajectories)
    rng.shuffle(trajectories)

    n = len(trajectories)
    n_train = int(n * train_frac)
    n_val = int(n * val_frac)

    train_trajs = trajectories[:n_train]
    val_trajs = trajectories[n_train : n_train + n_val]
    test_trajs = trajectories[n_train + n_val :]

    train_ds = TrajectoryDataset(train_trajs, samples_per_track=None)
    val_ds = TrajectoryDataset(val_trajs, samples_per_track=None)
    test_ds = TrajectoryDataset(test_trajs, samples_per_track=None)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    return train_loader, val_loader, test_loader
