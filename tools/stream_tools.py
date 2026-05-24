"""Stream tools — yield sliding sensor windows for a target engine.

Used by the MonitorAgent to feed fixed-length windows into the CNN-LSTM
predictor in real-time order.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


def _sensor_columns(df: pd.DataFrame) -> list[str]:
    """Return the sensor column names (those prefixed by the schema prefix)."""
    prefix = _load_config()["data"]["schema"]["sensor_prefix"]
    return [col for col in df.columns if col.startswith(prefix)]


def stream_sensors(
    df: pd.DataFrame, engine_id: int, window_size: int | None = None
) -> Iterator[np.ndarray]:
    """Yield consecutive sensor windows for the given engine.

    Args:
        df: Preprocessed DataFrame with unit_id, cycle, and sensor columns.
        engine_id: Target unit_id to stream.
        window_size: Number of cycles per window. Defaults to monitoring.window_size.

    Yields:
        2-D numpy arrays of shape (window_size, n_sensors).
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if window_size is None:
        window_size = _load_config()["monitoring"]["window_size"]
    if window_size <= 0:
        raise ValueError(f"window_size must be positive, got {window_size}")
    engine_df = df[df["unit_id"] == engine_id].sort_values("cycle")
    if engine_df.empty:
        raise ValueError(f"No rows found for engine_id={engine_id}")
    sensors = _sensor_columns(engine_df)
    features = engine_df[sensors].to_numpy(dtype=np.float32)
    if len(features) < window_size:
        logger.warning("Engine %d has %d cycles, less than window_size=%d",
                       engine_id, len(features), window_size)
        return
    for start in range(len(features) - window_size + 1):
        yield features[start:start + window_size]
