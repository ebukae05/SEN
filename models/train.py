"""Train the CNN-LSTM model on a CMAPSS dataset.

Loads the preprocessed CSV produced by preprocess.py, builds sliding windows
of sensor data per engine, trains the CNN-LSTM regressor for the configured
number of epochs, evaluates RMSE on the held-out CMAPSS test set, and saves
the resulting weights to models/saved/.

Run as a script:
    python models/train.py --dataset FD001
"""

from __future__ import annotations

import argparse
import logging
import pickle
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch import nn, optim
from torch.utils.data import DataLoader, Dataset, random_split

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.cnn_lstm import CNNLSTM, build_model  # noqa: E402

CONFIG_PATH = REPO_ROOT / "config.yaml"
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


def set_seed(seed: int) -> None:
    """Seed Python, NumPy, and PyTorch RNGs for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_processed_data(
    dataset_id: str, config: dict[str, Any]
) -> tuple[pd.DataFrame, list[str]]:
    """Load the cleaned training CSV and return (df, sensor_columns)."""
    csv_name = config["data"]["processed_filename"].format(dataset_id=dataset_id)
    csv_path = REPO_ROOT / config["paths"]["data_processed"] / csv_name
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed dataset missing: {csv_path}. Run preprocess.py first."
        )
    df = pd.read_csv(csv_path)
    prefix = config["data"]["schema"]["sensor_prefix"]
    sensor_cols = [col for col in df.columns if col.startswith(prefix)]
    logger.info("Loaded %s: %d rows, %d sensors", dataset_id, len(df), len(sensor_cols))
    return df, sensor_cols


def make_train_windows(
    df: pd.DataFrame, sensor_cols: list[str], seq_len: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build sliding-window samples and matching RUL labels from training df."""
    windows: list[np.ndarray] = []
    labels: list[float] = []
    for _, engine_df in df.groupby("unit_id", sort=True):
        engine_df = engine_df.sort_values("cycle")
        if len(engine_df) < seq_len:
            continue
        features = engine_df[sensor_cols].to_numpy(dtype=np.float32)
        ruls = engine_df["RUL"].to_numpy(dtype=np.float32)
        for start in range(len(engine_df) - seq_len + 1):
            windows.append(features[start:start + seq_len])
            labels.append(ruls[start + seq_len - 1])
    return np.stack(windows), np.asarray(labels, dtype=np.float32)


class SensorWindowDataset(Dataset):
    """Wraps stacked windows + labels as a PyTorch Dataset."""

    def __init__(self, windows: np.ndarray, labels: np.ndarray) -> None:
        """Store windows and labels as float tensors."""
        if len(windows) != len(labels):
            raise ValueError("windows and labels must have the same length")
        self.windows = torch.from_numpy(windows).float()
        self.labels = torch.from_numpy(labels).float()

    def __len__(self) -> int:
        """Number of samples."""
        return len(self.labels)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        """Return one (window, label) pair."""
        return self.windows[index], self.labels[index]


def train_epoch(
    model: CNNLSTM, loader: DataLoader, optimizer: optim.Optimizer,
    criterion: nn.Module, device: torch.device,
) -> float:
    """Run one training epoch and return mean batch loss."""
    model.train()
    running = 0.0
    samples = 0
    for windows, labels in loader:
        windows = windows.to(device)
        labels = labels.to(device)
        optimizer.zero_grad()
        predictions = model(windows)
        loss = criterion(predictions, labels)
        loss.backward()
        optimizer.step()
        running += loss.item() * windows.size(0)
        samples += windows.size(0)
    return running / samples


def eval_loss(
    model: CNNLSTM, loader: DataLoader, criterion: nn.Module, device: torch.device,
) -> float:
    """Compute mean loss over the loader with the model in eval mode."""
    model.eval()
    running = 0.0
    samples = 0
    with torch.no_grad():
        for windows, labels in loader:
            windows = windows.to(device)
            labels = labels.to(device)
            predictions = model(windows)
            running += criterion(predictions, labels).item() * windows.size(0)
            samples += windows.size(0)
    return running / samples


def _load_test_dataframe(
    dataset_id: str, sensor_cols: list[str], config: dict[str, Any]
) -> pd.DataFrame:
    """Read test_{id}.txt, apply schema, drop unused sensors, normalize."""
    raw_dir = REPO_ROOT / config["paths"]["data_raw"]
    test_path = raw_dir / config["data"]["datasets"][dataset_id]["test"]
    all_cols = config["data"]["schema"]["columns"]
    df = pd.read_csv(test_path, sep=r"\s+", header=None, names=all_cols)
    scaler_name = config["data"]["scaler_filename"].format(dataset_id=dataset_id)
    scaler_path = REPO_ROOT / config["paths"]["data_processed"] / scaler_name
    with scaler_path.open("rb") as scaler_file:
        scaler = pickle.load(scaler_file)
    df[sensor_cols] = scaler.transform(df[sensor_cols])
    return df[["unit_id", "cycle", *sensor_cols]]


def _last_window(engine_df: pd.DataFrame, sensor_cols: list[str], seq_len: int) -> np.ndarray:
    """Return the last seq_len rows of engine_df, pre-padding with the first row if short."""
    features = engine_df.sort_values("cycle")[sensor_cols].to_numpy(dtype=np.float32)
    if len(features) >= seq_len:
        return features[-seq_len:]
    pad = np.repeat(features[:1], seq_len - len(features), axis=0)
    return np.vstack([pad, features])


def make_test_windows(
    dataset_id: str, sensor_cols: list[str], seq_len: int, config: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray]:
    """Build one window per engine (the last seq_len cycles) and load true RULs."""
    test_df = _load_test_dataframe(dataset_id, sensor_cols, config)
    rul_path = (
        REPO_ROOT / config["paths"]["data_raw"]
        / config["data"]["datasets"][dataset_id]["rul"]
    )
    true_ruls = pd.read_csv(rul_path, header=None, names=["RUL"])["RUL"].to_numpy(dtype=np.float32)
    windows = [
        _last_window(engine_df, sensor_cols, seq_len)
        for _, engine_df in test_df.groupby("unit_id", sort=True)
    ]
    return np.stack(windows), true_ruls


def compute_rmse(predictions: np.ndarray, labels: np.ndarray, cap: float) -> float:
    """Root-mean-squared error after clipping both arrays to [0, cap]."""
    clipped_predictions = np.clip(predictions, 0.0, cap)
    clipped_labels = np.clip(labels, 0.0, cap)
    return float(np.sqrt(np.mean((clipped_predictions - clipped_labels) ** 2)))


def predict_batched(
    model: CNNLSTM, windows: np.ndarray, device: torch.device, batch_size: int = 64,
) -> np.ndarray:
    """Run inference over an array of windows, returning predictions as numpy."""
    model.eval()
    tensor = torch.from_numpy(windows).float()
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(tensor), batch_size):
            batch = tensor[start:start + batch_size].to(device)
            outputs.append(model(batch).cpu().numpy())
    return np.concatenate(outputs)


def save_weights(model: CNNLSTM, dataset_id: str, config: dict[str, Any]) -> Path:
    """Persist the model state dict to models/saved/."""
    save_dir = REPO_ROOT / config["paths"]["models_saved"]
    save_dir.mkdir(parents=True, exist_ok=True)
    weights_path = save_dir / config["model"]["weights_filename"].format(
        dataset_id=dataset_id
    )
    torch.save(model.state_dict(), weights_path)
    logger.info("Saved weights to %s", weights_path)
    return weights_path


def _build_loaders(
    windows: np.ndarray, labels: np.ndarray, config: dict[str, Any]
) -> tuple[DataLoader, DataLoader]:
    """Split into train/val Datasets and return their DataLoaders."""
    dataset = SensorWindowDataset(windows, labels)
    val_size = int(len(dataset) * config["training"]["validation_split"])
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(
        dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(config["training"]["random_seed"]),
    )
    batch_size = config["training"]["batch_size"]
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    return train_loader, val_loader


def train(dataset_id: str) -> dict[str, float]:
    """Full training run: load, window, fit, evaluate, save."""
    config = _load_config()
    set_seed(config["training"]["random_seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training on device: %s", device)
    df, sensor_cols = load_processed_data(dataset_id, config)
    seq_len = config["model"]["sequence_length"]
    windows, labels = make_train_windows(df, sensor_cols, seq_len)
    logger.info("Built %d training windows", len(windows))
    train_loader, val_loader = _build_loaders(windows, labels, config)
    model = build_model(config).to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=config["training"]["learning_rate"])
    epochs = config["training"]["epochs"]
    for epoch in range(1, epochs + 1):
        train_mse = train_epoch(model, train_loader, optimizer, criterion, device)
        val_mse = eval_loss(model, val_loader, criterion, device)
        logger.info("Epoch %d/%d: train_mse=%.3f val_mse=%.3f",
                    epoch, epochs, train_mse, val_mse)
    save_weights(model, dataset_id, config)
    test_windows, test_labels = make_test_windows(dataset_id, sensor_cols, seq_len, config)
    predictions = predict_batched(model, test_windows, device)
    test_rmse = compute_rmse(predictions, test_labels, float(config["preprocessing"]["rul_cap"]))
    logger.info("Test RMSE on %s: %.3f cycles", dataset_id, test_rmse)
    return {"test_rmse": test_rmse}


def _configure_logging(config: dict[str, Any]) -> None:
    """Apply the project logging configuration."""
    logging.basicConfig(
        level=config["logging"]["level"],
        format=config["logging"]["format"],
        datefmt=config["logging"]["datefmt"],
    )


def main() -> None:
    """CLI entry point: choose a dataset and run training."""
    config = _load_config()
    _configure_logging(config)
    parser = argparse.ArgumentParser(description="Train the SEN CNN-LSTM model")
    parser.add_argument(
        "--dataset", required=True, choices=list(config["data"]["datasets"])
    )
    args = parser.parse_args()
    train(args.dataset)


if __name__ == "__main__":
    main()
