"""
tools/predict_tools.py — MonitorAgent tools for RUL inference and threshold alerts.

Wraps the trained CNN-LSTM model for single-window inference and provides
threshold checking to flag engines approaching failure.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

# Module-level model cache — loaded once, reused across calls
_model_cache: dict[str, Any] = {}


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _get_model() -> "torch.nn.Module":
    """
    Load the CNN-LSTM model from saved weights, caching it after the first load.

    Returns
    -------
    torch.nn.Module
        Model in eval mode with weights loaded from config-specified path.

    Raises
    ------
    FileNotFoundError
        If the weights file does not exist.
    """
    if "model" in _model_cache:
        return _model_cache["model"]

    import sys
    sys.path.insert(0, str(_PROJECT_ROOT))
    from models.cnn_lstm import build_model

    cfg = _load_config()["model"]
    weights_path = _PROJECT_ROOT / cfg["saved_dir"] / cfg["weights_file"]
    if not weights_path.exists():
        raise FileNotFoundError(f"Model weights not found: {weights_path}")

    model = build_model()
    model.load_state_dict(torch.load(weights_path, map_location="cpu", weights_only=True))
    model.eval()
    _model_cache["model"] = model
    logger.info("Model loaded from %s", weights_path)
    return model


def predict_rul(window: np.ndarray) -> float:
    """
    Run CNN-LSTM inference on a single sensor window and return predicted RUL.

    Parameters
    ----------
    window : np.ndarray
        Sensor window of shape (window_size, n_features) — normalized values.

    Returns
    -------
    float
        Predicted Remaining Useful Life in cycles.

    Raises
    ------
    TypeError
        If window is not a numpy array.
    ValueError
        If window does not have exactly 2 dimensions.
    """
    if not isinstance(window, np.ndarray):
        raise TypeError(f"window must be a numpy ndarray, got {type(window)}")
    if window.ndim != 2:
        raise ValueError(f"window must be 2D (seq_len, n_features), got shape {window.shape}")

    model = _get_model()
    tensor = torch.from_numpy(window.astype(np.float32)).unsqueeze(0)  # (1, seq_len, n_features)
    with torch.no_grad():
        rul_pred = model(tensor).item()

    rul_pred = max(0.0, rul_pred)  # clamp to non-negative
    logger.debug("Predicted RUL: %.2f cycles", rul_pred)
    return rul_pred


def check_thresholds(engine_id: int, rul: float, threshold: int = 50) -> dict[str, Any]:
    """
    Check whether a predicted RUL falls below the alert threshold.

    Parameters
    ----------
    engine_id : int
        The engine being monitored.
    rul : float
        Predicted RUL in cycles.
    threshold : int
        Alert threshold in cycles (default 50, from config).

    Returns
    -------
    dict[str, Any]
        Result with keys: engine_id, rul, threshold, alert (bool), severity.

    Raises
    ------
    TypeError
        If engine_id is not an int or rul is not a float/int.
    ValueError
        If threshold is not a positive integer.
    """
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if not isinstance(rul, (float, int, np.floating)):
        raise TypeError(f"rul must be numeric, got {type(rul)}")
    if not isinstance(threshold, int) or threshold <= 0:
        raise ValueError(f"threshold must be a positive int, got {threshold!r}")

    cfg = _load_config()
    alert_threshold = cfg["monitor"]["rul_alert_threshold"]
    effective_threshold = threshold if threshold != 50 else alert_threshold

    alert = rul < effective_threshold
    if rul < effective_threshold * 0.4:
        severity = "CRITICAL"
    elif rul < effective_threshold * 0.7:
        severity = "WARNING"
    elif alert:
        severity = "CAUTION"
    else:
        severity = "NORMAL"

    result = {
        "engine_id": int(engine_id),
        "rul":       round(float(rul), 2),
        "threshold": effective_threshold,
        "alert":     alert,
        "severity":  severity,
    }
    if alert:
        logger.warning("Engine %d — %s: RUL=%.1f below threshold=%d", engine_id, severity, rul, effective_threshold)
    else:
        logger.info("Engine %d — %s: RUL=%.1f", engine_id, severity, rul)
    return result
