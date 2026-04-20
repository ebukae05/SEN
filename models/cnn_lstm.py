"""
models/cnn_lstm.py — CNN-LSTM architecture for turbofan RUL regression.

Architecture (from config.yaml):
    Input (30 timesteps × 14 features)
    → Conv1D (64 filters, kernel 3, ReLU)
    → Conv1D (64 filters, kernel 3, ReLU)
    → MaxPooling1D (pool 2)
    → LSTM (50 units, return_sequences=True)
    → Dropout (0.3)
    → LSTM (50 units)
    → Dropout (0.3)
    → Dense (1) → RUL output
"""

import logging
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
import torch.nn.functional as F
import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


class CNNLSTM(nn.Module):
    """
    CNN-LSTM model for Remaining Useful Life regression on CMAPSS FD001.

    Input shape:  (batch_size, sequence_length, n_features)
    Output shape: (batch_size,)  — one predicted RUL per sample
    """

    def __init__(
        self,
        n_features: int,
        conv_filters: int,
        conv_kernel: int,
        pool_size: int,
        lstm_units: int,
        dropout_rate: float,
    ) -> None:
        """
        Initialize all layers.

        Parameters
        ----------
        n_features : int
            Number of sensor input channels (14 for FD001).
        conv_filters : int
            Output channels for both Conv1d layers.
        conv_kernel : int
            Kernel size for both Conv1d layers.
        pool_size : int
            Kernel size for MaxPool1d.
        lstm_units : int
            Hidden size for both LSTM layers.
        dropout_rate : float
            Dropout probability applied after each LSTM.
        """
        super().__init__()
        self.conv1    = nn.Conv1d(n_features, conv_filters, conv_kernel)
        self.conv2    = nn.Conv1d(conv_filters, conv_filters, conv_kernel)
        self.pool     = nn.MaxPool1d(pool_size)
        self.lstm1    = nn.LSTM(conv_filters, lstm_units, batch_first=True)
        self.dropout1 = nn.Dropout(dropout_rate)
        self.lstm2    = nn.LSTM(lstm_units, lstm_units, batch_first=True)
        self.dropout2 = nn.Dropout(dropout_rate)
        self.fc       = nn.Linear(lstm_units, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through the network.

        Parameters
        ----------
        x : torch.Tensor
            Shape (batch_size, seq_len, n_features).

        Returns
        -------
        torch.Tensor
            Predicted RUL values, shape (batch_size,).
        """
        x = x.permute(0, 2, 1)        # → (batch, n_features, seq_len)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = self.pool(x)
        x = x.permute(0, 2, 1)        # → (batch, seq_len', conv_filters)
        x, _ = self.lstm1(x)
        x = self.dropout1(x)
        x, _ = self.lstm2(x)
        x = x[:, -1, :]               # last timestep → (batch, lstm_units)
        x = self.dropout2(x)
        return self.fc(x).squeeze(-1) # → (batch,)


def build_model() -> CNNLSTM:
    """
    Instantiate a CNNLSTM model using hyperparameters from config.yaml.

    Returns
    -------
    CNNLSTM
        Untrained model instance ready for training or weight loading.
    """
    cfg = _load_config()["model"]
    model = CNNLSTM(
        n_features=cfg["n_features"],
        conv_filters=cfg["conv_filters"],
        conv_kernel=cfg["conv_kernel_size"],
        pool_size=cfg["pool_size"],
        lstm_units=cfg["lstm_units"],
        dropout_rate=cfg["dropout_rate"],
    )
    n_params = sum(p.numel() for p in model.parameters())
    logger.info("Built CNNLSTM: %d trainable parameters", n_params)
    return model
