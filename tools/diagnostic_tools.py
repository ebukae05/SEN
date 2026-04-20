"""
tools/diagnostic_tools.py — DiagnosticAgent tools for engine degradation analysis.

Compares flagged engines against fleet averages, identifies declining sensors,
and quantifies degradation rate using linear regression.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from scipy.stats import linregress

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def compare_to_fleet(df: pd.DataFrame, engine_id: int) -> dict[str, Any]:
    """
    Compare a single engine's mean sensor readings against the fleet average.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with sensor columns and 'unit_id' present.
    engine_id : int
        The engine to compare.

    Returns
    -------
    dict[str, Any]
        Per-sensor delta (engine_mean − fleet_mean) and a summary flag.

    Raises
    ------
    TypeError
        If df is not a DataFrame or engine_id is not an int.
    ValueError
        If engine_id is not found in the DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not found in DataFrame")

    cfg = _load_config()
    sensor_cols = [c for c in cfg["data"]["keep_sensors"] if c in df.columns]
    fleet_means = df[sensor_cols].mean()
    engine_means = df[df["unit_id"] == engine_id][sensor_cols].mean()
    deltas = (engine_means - fleet_means).to_dict()
    outlier_sensors = [s for s, d in deltas.items() if abs(d) > 0.1]
    logger.info("Engine %d vs fleet: %d sensors deviate >0.1", engine_id, len(outlier_sensors))
    return {"engine_id": int(engine_id), "deltas": deltas, "outlier_sensors": outlier_sensors}


def sensor_trends(df: pd.DataFrame, engine_id: int) -> dict[str, Any]:
    """
    Identify which sensors are declining fastest for a given engine.

    Uses linear regression slope over cycles to rank sensors by degradation speed.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with sensor columns, 'unit_id', and 'cycle' present.
    engine_id : int
        The engine to analyse.

    Returns
    -------
    dict[str, Any]
        Slopes per sensor (negative = declining) and ranked list of top degraders.

    Raises
    ------
    TypeError
        If df is not a DataFrame or engine_id is not an int.
    ValueError
        If engine_id is not found in the DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not found in DataFrame")

    cfg = _load_config()
    sensor_cols = [c for c in cfg["data"]["keep_sensors"] if c in df.columns]
    engine_df = df[df["unit_id"] == engine_id].sort_values("cycle")
    cycles = engine_df["cycle"].values.astype(float)
    slopes = {}
    for col in sensor_cols:
        result = linregress(cycles, engine_df[col].values)
        slopes[col] = round(float(result.slope), 6)
    ranked = sorted(slopes, key=lambda s: slopes[s])
    logger.info("Engine %d: fastest declining sensor = %s (slope=%.6f)", engine_id, ranked[0], slopes[ranked[0]])
    return {"engine_id": int(engine_id), "slopes": slopes, "ranked_declining": ranked}


def degradation_rate(df: pd.DataFrame, engine_id: int) -> dict[str, Any]:
    """
    Calculate the engine's overall degradation rate vs the fleet normal.

    Computes the mean absolute slope across all 14 sensors for the target engine
    and for the full fleet, then expresses the engine rate as a ratio.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with sensor columns, 'unit_id', and 'cycle' present.
    engine_id : int
        The engine to evaluate.

    Returns
    -------
    dict[str, Any]
        engine_rate, fleet_rate, ratio, and severity label.

    Raises
    ------
    TypeError
        If df is not a DataFrame or engine_id is not an int.
    ValueError
        If engine_id is not found in the DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not found in DataFrame")

    cfg = _load_config()
    sensor_cols = [c for c in cfg["data"]["keep_sensors"] if c in df.columns]

    def _mean_abs_slope(sub_df: pd.DataFrame) -> float:
        cycles = sub_df["cycle"].values.astype(float)
        slopes = [abs(linregress(cycles, sub_df[c].values).slope) for c in sensor_cols]
        return float(np.mean(slopes))

    engine_rate = _mean_abs_slope(df[df["unit_id"] == engine_id].sort_values("cycle"))
    fleet_rate = float(np.mean([
        _mean_abs_slope(df[df["unit_id"] == uid].sort_values("cycle"))
        for uid in df["unit_id"].unique()
    ]))
    ratio = engine_rate / fleet_rate if fleet_rate > 0 else 1.0
    severity = "HIGH" if ratio > 1.5 else "MODERATE" if ratio > 1.1 else "NORMAL"
    logger.info("Engine %d degradation: rate=%.6f, fleet=%.6f, ratio=%.2f (%s)",
                engine_id, engine_rate, fleet_rate, ratio, severity)
    return {
        "engine_id":   int(engine_id),
        "engine_rate": round(engine_rate, 6),
        "fleet_rate":  round(fleet_rate, 6),
        "ratio":       round(ratio, 3),
        "severity":    severity,
    }
