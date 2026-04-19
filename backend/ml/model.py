import torch
import torch.nn as nn

from config import DROPOUT, FEATURE_COLS, HIDDEN_SIZE, NUM_LAYERS, PRED_LEN, TARGET_COLS

N_FEATURES = len(FEATURE_COLS)
N_TARGETS = len(TARGET_COLS)


class _Head(nn.Module):
    def __init__(self, hidden_size: int, pred_len: int, output_size: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(hidden_size),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, pred_len * output_size),
        )
        for module in self.net:
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class TrajectoryLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = N_FEATURES,
        hidden_size: int = HIDDEN_SIZE,
        num_layers: int = NUM_LAYERS,
        dropout: float = DROPOUT,
        pred_len: int = PRED_LEN,
        output_size: int = N_TARGETS,
    ):
        super().__init__()
        self.pred_len = pred_len
        self.output_size = output_size
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.head = _Head(hidden_size, pred_len, output_size, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_state = out[:, -1, :]
        preds = self.head(last_state)
        return preds.view(-1, self.pred_len, self.output_size)


class TrajectoryGRU(nn.Module):
    def __init__(
        self,
        input_size: int = N_FEATURES,
        hidden_size: int = HIDDEN_SIZE,
        num_layers: int = NUM_LAYERS,
        dropout: float = DROPOUT,
        pred_len: int = PRED_LEN,
        output_size: int = N_TARGETS,
    ):
        super().__init__()
        self.pred_len = pred_len
        self.output_size = output_size
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.head = _Head(hidden_size, pred_len, output_size, dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.gru(x)
        last_state = out[:, -1, :]
        preds = self.head(last_state)
        return preds.view(-1, self.pred_len, self.output_size)


def get_model(model_type: str = "lstm") -> nn.Module:
    model_type = model_type.lower()
    if model_type == "lstm":
        return TrajectoryLSTM()
    if model_type == "gru":
        return TrajectoryGRU()
    raise ValueError(f"Unknown model type: {model_type}. Use 'lstm' or 'gru'.")
