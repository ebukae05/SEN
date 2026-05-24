"""Deterministic CMAPSS preprocessing.

Loads a raw CMAPSS dataset, dynamically drops the lowest-variance (constant
and near-constant) sensors, normalizes the remainder to [0, 1] via
MinMaxScaler, generates piecewise-linear RUL labels, and writes the cleaned
CSV + fitted scaler to data/processed/.

Run as a script:
    python preprocess.py --dataset FD001
    python preprocess.py --all
"""

from __future__ import annotations

import argparse
import logging
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from sklearn.preprocessing import MinMaxScaler

REPO_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = REPO_ROOT / "config.yaml"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


def _sensor_columns(config: dict[str, Any]) -> list[str]:
    """Return all sensor column names (s1..sN) from the schema."""
    prefix = config["data"]["schema"]["sensor_prefix"]
    count = config["data"]["schema"]["sensor_count"]
    return [f"{prefix}{i}" for i in range(1, count + 1)]


def load_raw(dataset_id: str, config: dict[str, Any]) -> pd.DataFrame:
    """Read the whitespace-delimited CMAPSS train file and apply column headers.

    Args:
        dataset_id: One of 'FD001' through 'FD004'.
        config: Loaded config dict.

    Returns:
        DataFrame with named columns (unit_id, cycle, op1-3, s1-s21).
    """
    if dataset_id not in config["data"]["datasets"]:
        raise ValueError(f"Unknown dataset_id: {dataset_id}")
    raw_dir = REPO_ROOT / config["paths"]["data_raw"]
    file_path = raw_dir / config["data"]["datasets"][dataset_id]["train"]
    if not file_path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {file_path}")
    columns = config["data"]["schema"]["columns"]
    df = pd.read_csv(file_path, sep=r"\s+", header=None, names=columns)
    logger.info("Loaded %s: %d rows, %d engines", dataset_id, len(df), df["unit_id"].nunique())
    return df


def identify_constant_sensors(
    df: pd.DataFrame, sensor_cols: list[str], keep_count: int
) -> list[str]:
    """Return the names of the lowest-variance sensors that should be dropped.

    Sensors are ranked by variance ascending; the bottom (total - keep_count)
    are returned. This is dynamic per dataset and converges to keep_count
    retained sensors.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if keep_count <= 0 or keep_count > len(sensor_cols):
        raise ValueError(f"keep_count {keep_count} out of range")
    variances = df[sensor_cols].var().sort_values(ascending=True)
    drop_count = len(sensor_cols) - keep_count
    return variances.index[:drop_count].tolist()


def drop_sensors(df: pd.DataFrame, sensors_to_drop: list[str]) -> pd.DataFrame:
    """Return a copy of df with the given sensor columns removed."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    logger.info("Dropping %d constant/near-constant sensors: %s",
                len(sensors_to_drop), sensors_to_drop)
    return df.drop(columns=sensors_to_drop)


def normalize_sensors(
    df: pd.DataFrame, sensor_cols: list[str], feature_range: tuple[float, float]
) -> tuple[pd.DataFrame, MinMaxScaler]:
    """Fit MinMaxScaler on the given sensor columns and return scaled df + scaler.

    Args:
        df: DataFrame with sensor columns to normalize.
        sensor_cols: Names of columns to normalize.
        feature_range: Target range as (low, high).

    Returns:
        Tuple of (DataFrame with normalized sensor columns, fitted scaler).
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    missing = [col for col in sensor_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Cannot normalize missing columns: {missing}")
    scaler = MinMaxScaler(feature_range=feature_range)
    df = df.copy()
    df[sensor_cols] = scaler.fit_transform(df[sensor_cols])
    return df, scaler


def generate_rul_labels(df: pd.DataFrame, cap: int) -> pd.DataFrame:
    """Add a piecewise-linear RUL label column to df.

    True RUL for each row is max_cycle_for_engine - current_cycle. The label
    is clipped at `cap` so very-healthy engines all get the same target.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if cap <= 0:
        raise ValueError(f"RUL cap must be positive, got {cap}")
    df = df.copy()
    max_cycle = df.groupby("unit_id")["cycle"].transform("max")
    df["RUL"] = (max_cycle - df["cycle"]).clip(upper=cap)
    return df


def save_processed(
    df: pd.DataFrame, scaler: MinMaxScaler, dataset_id: str, config: dict[str, Any]
) -> tuple[Path, Path]:
    """Persist the cleaned DataFrame as CSV and the scaler as pickle."""
    processed_dir = REPO_ROOT / config["paths"]["data_processed"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    csv_path = processed_dir / config["data"]["processed_filename"].format(
        dataset_id=dataset_id
    )
    scaler_path = processed_dir / config["data"]["scaler_filename"].format(
        dataset_id=dataset_id
    )
    df.to_csv(csv_path, index=False)
    with scaler_path.open("wb") as scaler_file:
        pickle.dump(scaler, scaler_file)
    logger.info("Wrote %s (%d rows) and %s", csv_path, len(df), scaler_path)
    return csv_path, scaler_path


def preprocess_dataset(dataset_id: str) -> pd.DataFrame:
    """Run the full preprocessing pipeline for one CMAPSS dataset.

    Steps: load → identify constants → drop → normalize → label → save.

    Returns:
        The cleaned DataFrame (also written to disk).
    """
    config = _load_config()
    raw_df = load_raw(dataset_id, config)
    sensor_cols = _sensor_columns(config)
    keep_count = config["preprocessing"]["expected_sensor_count_after_drop"]
    to_drop = identify_constant_sensors(raw_df, sensor_cols, keep_count)
    dropped_df = drop_sensors(raw_df, to_drop)
    kept_sensors = [col for col in sensor_cols if col not in to_drop]
    low, high = config["preprocessing"]["normalize_range"]
    normalized_df, scaler = normalize_sensors(dropped_df, kept_sensors, (low, high))
    labeled_df = generate_rul_labels(normalized_df, config["preprocessing"]["rul_cap"])
    save_processed(labeled_df, scaler, dataset_id, config)
    return labeled_df


def _configure_logging(config: dict[str, Any]) -> None:
    """Apply the project logging configuration."""
    logging.basicConfig(
        level=config["logging"]["level"],
        format=config["logging"]["format"],
        datefmt=config["logging"]["datefmt"],
    )


def main() -> None:
    """Command-line entry point. Use --dataset FD001 or --all."""
    config = _load_config()
    _configure_logging(config)
    parser = argparse.ArgumentParser(description="SEN CMAPSS preprocessing")
    parser.add_argument("--dataset", choices=list(config["data"]["datasets"]))
    parser.add_argument("--all", action="store_true", help="Process FD001-FD004")
    args = parser.parse_args()
    if args.all:
        targets = list(config["data"]["datasets"])
    elif args.dataset:
        targets = [args.dataset]
    else:
        parser.error("Specify --dataset <id> or --all")
    for dataset_id in targets:
        preprocess_dataset(dataset_id)


if __name__ == "__main__":
    main()
