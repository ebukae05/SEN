"""CNN-LSTM architecture for Remaining Useful Life regression.

Two Conv1D layers extract local temporal features over sliding sensor
windows, MaxPool downsamples, then a two-layer LSTM consumes the resulting
sequence and a Dense head produces a single RUL estimate.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import torch
import yaml
from torch import nn

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


class CNNLSTM(nn.Module):
    """CNN-LSTM regressor for RUL prediction over sensor windows."""

    def __init__(
        self,
        n_features: int,
        conv_filters: int,
        conv_kernel: int,
        pool_size: int,
        lstm_units: int,
        dropout: float,
    ) -> None:
        """Build the layers from explicit hyperparameters."""
        super().__init__()
        self.conv1 = nn.Conv1d(n_features, conv_filters, conv_kernel)
        self.conv2 = nn.Conv1d(conv_filters, conv_filters, conv_kernel)
        self.pool = nn.MaxPool1d(pool_size)
        self.lstm1 = nn.LSTM(conv_filters, lstm_units, batch_first=True)
        self.dropout1 = nn.Dropout(dropout)
        self.lstm2 = nn.LSTM(lstm_units, lstm_units, batch_first=True)
        self.dropout2 = nn.Dropout(dropout)
        self.fc = nn.Linear(lstm_units, 1)

    def forward(self, sensor_window: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            sensor_window: Tensor of shape [batch, seq_len, n_features].

        Returns:
            Tensor of shape [batch] with one predicted RUL per window.
        """
        features = sensor_window.transpose(1, 2)
        features = torch.relu(self.conv1(features))
        features = torch.relu(self.conv2(features))
        features = self.pool(features).transpose(1, 2)
        lstm1_out, _ = self.lstm1(features)
        lstm1_out = self.dropout1(lstm1_out)
        _, (last_hidden, _) = self.lstm2(lstm1_out)
        pooled = self.dropout2(last_hidden.squeeze(0))
        return self.fc(pooled).squeeze(-1)


def build_model(config: dict[str, Any] | None = None) -> CNNLSTM:
    """Construct a CNNLSTM from config.yaml's `model` section.

    Args:
        config: Optional pre-loaded config dict. Falls back to config.yaml.

    Returns:
        A freshly initialized CNNLSTM ready for training or inference.
    """
    if config is None:
        config = _load_config()
    model_cfg = config["model"]
    return CNNLSTM(
        n_features=model_cfg["n_features"],
        conv_filters=model_cfg["conv_filters"],
        conv_kernel=model_cfg["conv_kernel"],
        pool_size=model_cfg["pool_size"],
        lstm_units=model_cfg["lstm_units"],
        dropout=model_cfg["dropout"],
    )


def load_weights(model: CNNLSTM, weights_path: Path, device: torch.device) -> CNNLSTM:
    """Load saved weights into a CNNLSTM and set it to eval mode.

    Args:
        model: An initialized CNNLSTM matching the saved architecture.
        weights_path: Path to a .pt state dict file.
        device: Target device for the model.

    Returns:
        The same model with weights loaded and moved to device, in eval mode.
    """
    if not weights_path.exists():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")
    state_dict = torch.load(weights_path, map_location=device, weights_only=True)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model
