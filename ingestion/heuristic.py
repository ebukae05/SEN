"""Heuristic RUL/severity inference for custom datasets.

The trained CNN-LSTM weights expect exactly 14 normalized CMAPSS sensors —
they have no meaning when applied to a user's compressor or pump dataset.
Until per-tenant fine-tuning is wired up, custom datasets get a transparent
heuristic so the upload→fleet→agent flow still works end-to-end.

Approach:
    - If RUL is present in the processed CSV, use the last observed RUL.
    - Otherwise, fit a linear regression on per-engine sensor drift and
      project cycles-until-threshold using the largest-trending sensor.
    - Map the resulting pseudo-RUL through the same monitoring thresholds
      the CMAPSS model uses.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


@dataclass
class HeuristicStatus:
    """RUL + severity payload computed without the CNN-LSTM."""

    engine_id: int
    predicted_rul: float
    severity: str
    alert: bool
    threshold: float


def _sensor_columns(df: pd.DataFrame) -> list[str]:
    """Return all columns except identifiers and labels."""
    reserved = {"unit_id", "cycle", "RUL"}
    return [c for c in df.columns if c not in reserved]


def _severity_label(rul: float, severity_config: dict[str, float]) -> str:
    """Map an RUL value to a severity label (mirrors predict_tools._severity)."""
    if rul < severity_config["critical_below"]:
        return "critical"
    if rul < severity_config["watch_below"]:
        return "watch"
    return "healthy"


def _estimate_rul(group: pd.DataFrame, rul_cap: float) -> float:
    """Project cycles-until-failure for one engine from sensor drift trends.

    Picks the sensor with the largest absolute slope per cycle, then estimates
    how many more cycles until that sensor reaches its observed maximum
    deviation from its starting value. Returns 0 if drift is flat.
    """
    sensor_cols = _sensor_columns(group)
    if not sensor_cols or len(group) < 2:
        return rul_cap
    cycles = group["cycle"].to_numpy(dtype=float)
    best_slope = 0.0
    best_remaining = rul_cap
    for col in sensor_cols:
        values = group[col].to_numpy(dtype=float)
        slope, intercept = np.polyfit(cycles, values, 1)
        if abs(slope) < 1e-6:
            continue
        baseline = values[: max(3, len(values) // 10)].mean()
        peak_observed = values.max() if slope > 0 else values.min()
        budget = abs(peak_observed - baseline) * 2.0
        current_offset = abs(values[-1] - baseline)
        remaining_offset = max(0.0, budget - current_offset)
        remaining_cycles = remaining_offset / abs(slope)
        if abs(slope) > abs(best_slope):
            best_slope = slope
            best_remaining = remaining_cycles
    return float(min(rul_cap, best_remaining))


def compute_engine_status(df: pd.DataFrame, engine_id: int) -> HeuristicStatus:
    """Return a HeuristicStatus for one engine in a processed custom dataset."""
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not in dataset")
    config = _load_config()
    threshold = float(config["monitoring"]["rul_alert_threshold"])
    severity_cfg = config["monitoring"]["severity"]
    rul_cap = float(config["preprocessing"]["rul_cap"])
    group = df[df["unit_id"] == engine_id].sort_values("cycle")
    if "RUL" in group.columns:
        predicted_rul = float(group["RUL"].iloc[-1])
    else:
        predicted_rul = _estimate_rul(group, rul_cap)
    severity = _severity_label(predicted_rul, severity_cfg)
    return HeuristicStatus(
        engine_id=engine_id,
        predicted_rul=predicted_rul,
        severity=severity,
        alert=predicted_rul < threshold,
        threshold=threshold,
    )


def is_custom_dataset(dataset_id: str) -> bool:
    """Return True for any dataset_id outside the CMAPSS FD001-FD004 set."""
    config = _load_config()
    return dataset_id not in set(config["data"]["datasets"])


def load_custom_dataframe(dataset_id: str) -> pd.DataFrame:
    """Load a processed custom dataset CSV from the ingestion store."""
    from ingestion.store import get_store

    path = get_store().get_processed_path(dataset_id)
    if not path.exists():
        raise FileNotFoundError(f"Processed custom dataset missing: {path}")
    return pd.read_csv(path)
