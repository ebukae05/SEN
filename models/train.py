"""
models/train.py — Training script for the CNN-LSTM RUL model.

Usage:
    python models/train.py                  # trains on default (FD001)
    python models/train.py --dataset FD002  # trains on FD002

Loads CMAPSS data, builds sliding-window sequences, trains the CNN-LSTM,
and saves the best weights (by validation RMSE) to models/saved/.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data import DataLoader, TensorDataset, random_split

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from models.cnn_lstm import build_model
from tools.ingest_tools import clean_data, generate_rul_labels, load_dataset

logger = logging.getLogger(__name__)
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

VALID_DATASETS = ("FD001", "FD002", "FD003", "FD004")


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def create_sequences(
    df: "pd.DataFrame",
    sensor_cols: list[str],
    seq_len: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Build sliding-window sequences and RUL labels from the labeled DataFrame.

    Each window covers seq_len consecutive cycles; the label is the RUL
    at the last cycle of that window.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned, RUL-labeled DataFrame with 'unit_id', 'cycle', sensor cols, 'RUL'.
    sensor_cols : list[str]
        Names of the sensor feature columns.
    seq_len : int
        Number of cycles per sliding window.

    Returns
    -------
    tuple[np.ndarray, np.ndarray]
        X of shape (n_samples, seq_len, n_features) and y of shape (n_samples,).
    """
    X_list: list[np.ndarray] = []
    y_list: list[float] = []
    for engine_id in df["unit_id"].unique():
        engine = df[df["unit_id"] == engine_id].sort_values("cycle")
        sensors = engine[sensor_cols].values
        rul_vals = engine["RUL"].values
        for i in range(len(sensors) - seq_len + 1):
            X_list.append(sensors[i : i + seq_len])
            y_list.append(rul_vals[i + seq_len - 1])
    return np.array(X_list, dtype=np.float32), np.array(y_list, dtype=np.float32)


def build_dataloaders(
    X: np.ndarray,
    y: np.ndarray,
    batch_size: int,
    val_split: float = 0.2,
) -> tuple[DataLoader, DataLoader]:
    """
    Wrap arrays in TensorDatasets and split into train/val DataLoaders.

    Parameters
    ----------
    X : np.ndarray
        Feature sequences of shape (n_samples, seq_len, n_features).
    y : np.ndarray
        RUL labels of shape (n_samples,).
    batch_size : int
        Mini-batch size for training.
    val_split : float
        Fraction of samples to hold out for validation.

    Returns
    -------
    tuple[DataLoader, DataLoader]
        Train DataLoader and validation DataLoader.
    """
    dataset = TensorDataset(torch.from_numpy(X), torch.from_numpy(y))
    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)
    logger.info("DataLoaders ready: %d train / %d val samples", train_size, val_size)
    return train_loader, val_loader


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """
    Run one full training epoch and return the mean MSE loss.

    Parameters
    ----------
    model : nn.Module
    loader : DataLoader
    optimizer : torch.optim.Optimizer
    criterion : nn.Module
    device : torch.device

    Returns
    -------
    float
        Mean MSE loss across all training samples.
    """
    model.train()
    total_loss = 0.0
    for X_batch, y_batch in loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        optimizer.zero_grad()
        preds = model(X_batch)
        loss = criterion(preds, y_batch)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * len(X_batch)
    return total_loss / len(loader.dataset)  # type: ignore[arg-type]


def evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    """
    Evaluate the model on a DataLoader and return mean loss and RMSE.

    Parameters
    ----------
    model : nn.Module
    loader : DataLoader
    criterion : nn.Module
    device : torch.device

    Returns
    -------
    tuple[float, float]
        (mean_mse_loss, rmse)
    """
    model.eval()
    total_loss = 0.0
    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            preds = model(X_batch)
            total_loss += criterion(preds, y_batch).item() * len(X_batch)
    mean_loss = total_loss / len(loader.dataset)  # type: ignore[arg-type]
    return mean_loss, float(np.sqrt(mean_loss))


def run_training_loop(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    epochs: int,
    weights_path: Path,
) -> float:
    """
    Execute the full training loop, checkpoint the best model, and return best RMSE.

    Parameters
    ----------
    model : nn.Module
    train_loader : DataLoader
    val_loader : DataLoader
    optimizer : torch.optim.Optimizer
    criterion : nn.Module
    device : torch.device
    epochs : int
    weights_path : Path
        File path to save the best model weights.

    Returns
    -------
    float
        Best validation RMSE achieved during training.
    """
    best_rmse = float("inf")
    for epoch in range(1, epochs + 1):
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)
        val_loss, val_rmse = evaluate(model, val_loader, criterion, device)
        logger.info(
            "Epoch %02d/%02d | train_loss=%.2f | val_loss=%.2f | val_RMSE=%.2f",
            epoch, epochs, train_loss, val_loss, val_rmse,
        )
        if val_rmse < best_rmse:
            best_rmse = val_rmse
            torch.save(model.state_dict(), weights_path)
            logger.info("  → New best RMSE=%.2f — weights saved", best_rmse)
    return best_rmse


def main(dataset_id: str = "FD001") -> None:
    """
    Full pipeline: load data → build sequences → train CNN-LSTM → save weights.

    Parameters
    ----------
    dataset_id : str
        Target dataset ('FD001'–'FD004').
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    cfg = _load_config()
    model_cfg = cfg["model"]
    ds_cfg = cfg["data"]["datasets"][dataset_id]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("Training %s on device: %s", dataset_id, device)

    raw_df = load_dataset("train", dataset_id=dataset_id)
    cleaned_df = clean_data(raw_df, dataset_id=dataset_id)
    labeled_df = generate_rul_labels(cleaned_df, cap=cfg["rul"]["cap"])

    sensor_cols = ds_cfg["keep_sensors"]
    X, y = create_sequences(labeled_df, sensor_cols, model_cfg["sequence_length"])
    logger.info("Sequences built: X=%s  y=%s", X.shape, y.shape)

    train_loader, val_loader = build_dataloaders(X, y, model_cfg["training"]["batch_size"])
    model = build_model(dataset_id=dataset_id).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=model_cfg["training"]["learning_rate"])
    criterion = nn.MSELoss()

    saved_dir = _PROJECT_ROOT / model_cfg["saved_dir"]
    saved_dir.mkdir(parents=True, exist_ok=True)
    weights_file = model_cfg["weights_files"][dataset_id]
    weights_path = saved_dir / weights_file

    best_rmse = run_training_loop(
        model, train_loader, val_loader, optimizer, criterion,
        device, model_cfg["training"]["epochs"], weights_path,
    )
    logger.info("Training complete (%s). Best val RMSE: %.2f cycles", dataset_id, best_rmse)
    logger.info("Weights saved to: %s", weights_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train CNN-LSTM RUL model on CMAPSS dataset")
    parser.add_argument("--dataset", type=str, default="FD001", choices=VALID_DATASETS,
                        help="CMAPSS dataset to train on (default: FD001)")
    args = parser.parse_args()
    main(dataset_id=args.dataset)
