"""Training utilities for LSTM and GRU models."""

import json
import math

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from config import GRAD_CLIP, LEARNING_RATE, MODEL_DIR, NUM_EPOCHS, WEIGHT_DECAY


def train_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    model_name: str = "model",
    patience: int = 12,
) -> dict:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=4
    )
    criterion = nn.SmoothL1Loss(beta=0.05)

    best_val_loss = float("inf")
    epochs_without_improvement = 0
    history = {"train_losses": [], "val_losses": [], "best_epoch": 0}
    checkpoint_path = MODEL_DIR / f"{model_name}_best.pt"

    print(f"\n🚀 Training {model_name} on {device}")
    print(f"   Params: {sum(p.numel() for p in model.parameters()):,}")

    has_validation = val_loader is not None and len(val_loader) > 0
    if not has_validation:
        print("⚠ Validation loader is empty. Falling back to train loss for checkpointing.")

    for epoch in range(1, NUM_EPOCHS + 1):
        model.train()
        train_losses = []

        for x_batch, y_batch in train_loader:
            x_batch = x_batch.to(device)
            y_batch = y_batch.to(device)

            optimizer.zero_grad(set_to_none=True)
            preds = model(x_batch)
            loss = criterion(preds, y_batch)

            if not torch.isfinite(loss):
                continue

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_CLIP)
            optimizer.step()
            train_losses.append(loss.item())

        train_loss = float(np.mean(train_losses)) if train_losses else float("inf")

        model.eval()
        val_losses = []
        if has_validation:
            with torch.no_grad():
                for x_batch, y_batch in val_loader:
                    x_batch = x_batch.to(device)
                    y_batch = y_batch.to(device)
                    preds = model(x_batch)
                    loss = criterion(preds, y_batch)
                    if torch.isfinite(loss):
                        val_losses.append(loss.item())

        val_loss = float(np.mean(val_losses)) if val_losses else train_loss
        if math.isnan(val_loss) or math.isinf(val_loss):
            val_loss = train_loss

        history["train_losses"].append(train_loss)
        history["val_losses"].append(val_loss)
        scheduler.step(val_loss)

        if epoch % 5 == 0 or epoch == 1:
            lr = optimizer.param_groups[0]["lr"]
            print(f"  Epoch {epoch:3d}/{NUM_EPOCHS}  train={train_loss:.6f}  val={val_loss:.6f}  lr={lr:.2e}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            history["best_epoch"] = epoch
            epochs_without_improvement = 0
            torch.save(model.state_dict(), checkpoint_path)
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                print(f"  ⏹ Early stopping at epoch {epoch}")
                break

    if checkpoint_path.exists():
        model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    else:
        torch.save(model.state_dict(), checkpoint_path)

    print(f"\n✅ Best val loss: {best_val_loss:.6f} at epoch {history['best_epoch']}")

    history_path = MODEL_DIR / f"{model_name}_history.json"
    with open(history_path, "w") as f:
        json.dump(history, f)

    return history


def load_model(model: nn.Module, model_name: str) -> nn.Module:
    checkpoint_path = MODEL_DIR / f"{model_name}_best.pt"
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.load_state_dict(torch.load(checkpoint_path, map_location=device))
    model.eval()
    return model.to(device)
