"""Predict tools — RUL inference and threshold alerting.

Wraps the trained CNN-LSTM for use by the MonitorAgent. Model weights are
loaded lazily on first call and cached per dataset.
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.cnn_lstm import CNNLSTM, build_model, load_weights  # noqa: E402

CONFIG_PATH = REPO_ROOT / "config.yaml"
logger = logging.getLogger(__name__)

_MODEL_CACHE: dict[str, tuple[CNNLSTM, torch.device]] = {}


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


def _get_model(dataset_id: str) -> tuple[CNNLSTM, torch.device]:
    """Return a cached (model, device) tuple for the given dataset_id."""
    if dataset_id in _MODEL_CACHE:
        return _MODEL_CACHE[dataset_id]
    config = _load_config()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    weights_path = (
        REPO_ROOT / config["paths"]["models_saved"]
        / config["model"]["weights_filename"].format(dataset_id=dataset_id)
    )
    model = build_model(config)
    model = load_weights(model, weights_path, device)
    _MODEL_CACHE[dataset_id] = (model, device)
    logger.info("Loaded model for %s from %s", dataset_id, weights_path)
    return model, device


def _validate_window(window: np.ndarray, expected_shape: tuple[int, int]) -> None:
    """Raise if the window shape does not match the model's expected input."""
    if not isinstance(window, np.ndarray):
        raise TypeError("window must be a numpy ndarray")
    if window.shape != expected_shape:
        raise ValueError(
            f"window shape {window.shape} does not match expected {expected_shape}"
        )


def predict_rul(window: np.ndarray, dataset_id: str | None = None) -> float:
    """Run CNN-LSTM inference on one sensor window and return predicted RUL.

    Args:
        window: 2-D array of shape (seq_len, n_features).
        dataset_id: Which trained model to use; defaults to data.active_dataset.

    Returns:
        Predicted RUL in cycles, clipped at zero.
    """
    config = _load_config()
    if dataset_id is None:
        dataset_id = config["data"]["active_dataset"]
    expected = (config["model"]["sequence_length"], config["model"]["n_features"])
    _validate_window(window, expected)
    model, device = _get_model(dataset_id)
    batch = torch.as_tensor(np.ascontiguousarray(window), dtype=torch.float32).unsqueeze(0).to(device)
    with torch.no_grad():
        prediction = model(batch).item()
    return float(max(0.0, prediction))


def _severity(rul: float, severity_config: dict[str, float]) -> str:
    """Map an RUL value to a severity label."""
    if rul < severity_config["critical_below"]:
        return "critical"
    if rul < severity_config["watch_below"]:
        return "watch"
    return "healthy"


def check_thresholds(
    engine_id: int, rul: float, threshold: float | None = None
) -> dict[str, Any] | None:
    """Return an alert dict when RUL is below threshold, otherwise None.

    Args:
        engine_id: Engine being evaluated.
        rul: Predicted RUL in cycles.
        threshold: Alert threshold; defaults to monitoring.rul_alert_threshold.

    Returns:
        Dict with engine_id, rul, threshold, and severity when alerting; None otherwise.
    """
    config = _load_config()
    if threshold is None:
        threshold = config["monitoring"]["rul_alert_threshold"]
    if rul >= threshold:
        return None
    return {
        "engine_id": engine_id,
        "rul": rul,
        "threshold": threshold,
        "severity": _severity(rul, config["monitoring"]["severity"]),
        "alert": True,
    }
