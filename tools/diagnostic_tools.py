"""Diagnostic tools — characterize engine degradation against fleet baseline.

Used by the DiagnosticAgent to identify which sensors are degrading and how
fast, relative to the rest of the fleet.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from scipy.stats import linregress

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
    """Return the sensor column names in df."""
    prefix = _load_config()["data"]["schema"]["sensor_prefix"]
    return [col for col in df.columns if col.startswith(prefix)]


def _engine_subset(df: pd.DataFrame, engine_id: int) -> pd.DataFrame:
    """Return the rows for engine_id, sorted by cycle, or raise if absent."""
    engine_df = df[df["unit_id"] == engine_id].sort_values("cycle")
    if engine_df.empty:
        raise ValueError(f"No rows found for engine_id={engine_id}")
    return engine_df


def compare_to_fleet(df: pd.DataFrame, engine_id: int) -> dict[str, dict[str, float]]:
    """Compare an engine's sensor means to fleet-wide means.

    Args:
        df: Preprocessed DataFrame containing all engines.
        engine_id: Target engine.

    Returns:
        Dict mapping each sensor to {engine_mean, fleet_mean, deviation}.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    engine_df = _engine_subset(df, engine_id)
    sensors = _sensor_columns(df)
    fleet_means = df[sensors].mean()
    engine_means = engine_df[sensors].mean()
    comparison: dict[str, dict[str, float]] = {}
    for sensor in sensors:
        engine_value = float(engine_means[sensor])
        fleet_value = float(fleet_means[sensor])
        comparison[sensor] = {
            "engine_mean": engine_value,
            "fleet_mean": fleet_value,
            "deviation": engine_value - fleet_value,
        }
    return comparison


def _sensor_slope(engine_df: pd.DataFrame, sensor: str) -> float:
    """Return the linear-regression slope of one sensor over cycles."""
    if len(engine_df) < 2:
        return 0.0
    result = linregress(engine_df["cycle"].to_numpy(), engine_df[sensor].to_numpy())
    return float(result.slope)


def sensor_trends(df: pd.DataFrame, engine_id: int) -> dict[str, float]:
    """Rank sensors by absolute rate of change (most-degrading first).

    Args:
        df: Preprocessed DataFrame.
        engine_id: Target engine.

    Returns:
        Ordered dict of {sensor: slope}, sorted by |slope| descending.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    engine_df = _engine_subset(df, engine_id)
    sensors = _sensor_columns(df)
    slopes = {sensor: _sensor_slope(engine_df, sensor) for sensor in sensors}
    return dict(sorted(slopes.items(), key=lambda kv: abs(kv[1]), reverse=True))


def degradation_rate(df: pd.DataFrame, engine_id: int) -> float:
    """Estimate how much faster this engine degrades than the fleet average.

    Computes the engine's mean absolute sensor slope and divides by the fleet
    median to produce a unit-less ratio. 1.0 ≈ normal, >1.0 = accelerated.

    Args:
        df: Preprocessed DataFrame containing all engines.
        engine_id: Target engine.

    Returns:
        Degradation ratio relative to fleet median.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    engine_df = _engine_subset(df, engine_id)
    sensors = _sensor_columns(df)
    engine_rate = sum(abs(_sensor_slope(engine_df, s)) for s in sensors) / len(sensors)
    fleet_rates = [
        sum(abs(_sensor_slope(grp, s)) for s in sensors) / len(sensors)
        for _, grp in df.groupby("unit_id") if len(grp) >= 2
    ]
    fleet_median = float(pd.Series(fleet_rates).median())
    if fleet_median <= 0:
        return 1.0
    return float(engine_rate / fleet_median)
