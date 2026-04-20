"""
tools/stream_tools.py — MonitorAgent tool for streaming sensor windows.

Simulates real-time sensor ingestion by yielding sliding windows of
cleaned sensor data for a given engine, one window at a time.
"""

import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import numpy as np
import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def stream_sensors(
    df: "pd.DataFrame",
    engine_id: int,
    window_size: int = 30,
) -> Generator[np.ndarray, None, None]:
    """
    Yield sliding windows of sensor readings for a single engine.

    Simulates real-time ingestion: each call to next() returns the next
    window of `window_size` consecutive cycles for the specified engine.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with sensor columns and 'unit_id', 'cycle' present.
    engine_id : int
        The engine unit_id to stream data for.
    window_size : int
        Number of cycles per window (default 30, matches model sequence length).

    Yields
    ------
    np.ndarray
        Array of shape (window_size, n_features) — one sliding window.

    Raises
    ------
    TypeError
        If df is not a DataFrame or engine_id is not an int.
    ValueError
        If engine_id is not in the DataFrame or has fewer cycles than window_size.
    """
    import pandas as pd

    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not found in DataFrame")

    cfg = _load_config()
    sensor_cols = [c for c in cfg["data"]["keep_sensors"] if c in df.columns]
    engine_df = df[df["unit_id"] == engine_id].sort_values("cycle")
    sensor_data = engine_df[sensor_cols].values

    if len(sensor_data) < window_size:
        raise ValueError(
            f"Engine {engine_id} has only {len(sensor_data)} cycles; "
            f"need at least {window_size}"
        )

    n_windows = len(sensor_data) - window_size + 1
    logger.info("Streaming engine %d: %d windows of size %d", engine_id, n_windows, window_size)

    for i in range(n_windows):
        yield sensor_data[i : i + window_size].astype(np.float32)
