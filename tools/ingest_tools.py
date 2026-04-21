"""
tools/ingest_tools.py — DataEngineerAgent tools for loading, validating,
cleaning, and labeling NASA CMAPSS datasets (FD001–FD004).
"""

import logging
import pickle
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — must be set before pyplot import
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

VALID_DATASETS = ("FD001", "FD002", "FD003", "FD004")


def _load_config() -> dict[str, Any]:
    """Load and return the parsed config.yaml as a dict."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _get_dataset_config(dataset_id: str) -> dict[str, Any]:
    """
    Return the per-dataset configuration block from config.yaml.

    Parameters
    ----------
    dataset_id : str
        One of 'FD001', 'FD002', 'FD003', 'FD004'.

    Returns
    -------
    dict[str, Any]
        Dataset-specific config (train_file, drop_sensors, keep_sensors, etc.).

    Raises
    ------
    ValueError
        If dataset_id is not a recognised CMAPSS sub-dataset.
    """
    if dataset_id not in VALID_DATASETS:
        raise ValueError(f"dataset_id must be one of {VALID_DATASETS}; got {dataset_id!r}")
    cfg = _load_config()
    return cfg["data"]["datasets"][dataset_id]


def _resolve_dataset_id(dataset_id: str | None) -> str:
    """
    Resolve dataset_id, falling back to config active_dataset if None.

    Parameters
    ----------
    dataset_id : str or None
        Explicit dataset ID, or None to use the config default.

    Returns
    -------
    str
        Resolved dataset ID (e.g. 'FD001').
    """
    if dataset_id is not None:
        if dataset_id not in VALID_DATASETS:
            raise ValueError(f"dataset_id must be one of {VALID_DATASETS}; got {dataset_id!r}")
        return dataset_id
    return _load_config()["data"]["active_dataset"]


def load_dataset(dataset_name: str, dataset_id: str | None = None) -> pd.DataFrame:
    """
    Load a raw CMAPSS text file and attach column headers.

    Parameters
    ----------
    dataset_name : str
        One of 'train', 'test', or 'rul'.
    dataset_id : str or None
        Target dataset ('FD001'–'FD004'). Defaults to config active_dataset.

    Returns
    -------
    pd.DataFrame
        Parsed DataFrame with named columns.

    Raises
    ------
    ValueError
        If dataset_name is not a recognised split name.
    FileNotFoundError
        If the raw data file does not exist on disk.
    """
    if dataset_name not in ("train", "test", "rul"):
        raise ValueError(f"dataset_name must be 'train', 'test', or 'rul'; got {dataset_name!r}")

    dataset_id = _resolve_dataset_id(dataset_id)
    cfg = _load_config()
    ds_cfg = cfg["data"]["datasets"][dataset_id]

    file_map = {
        "train": ds_cfg["train_file"],
        "test":  ds_cfg["test_file"],
        "rul":   ds_cfg["rul_file"],
    }
    file_path = _PROJECT_ROOT / cfg["data"]["raw_dir"] / file_map[dataset_name]
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    if dataset_name == "rul":
        df = pd.read_csv(file_path, sep=r"\s+", header=None, names=["RUL"])
    else:
        df = pd.read_csv(file_path, sep=r"\s+", header=None, names=cfg["data"]["columns"])

    logger.info(
        "Loaded '%s' dataset (%s): %d rows × %d cols",
        dataset_name, dataset_id, len(df), len(df.columns),
    )
    return df


def validate_sensors(df: pd.DataFrame) -> dict[str, Any]:
    """
    Validate sensor columns for data quality issues.

    Dynamically detects constant/near-constant sensors, missing values,
    and infinite values. No hardcoded drop list — works for any CMAPSS dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataset DataFrame with sensor columns present.

    Returns
    -------
    dict[str, Any]
        Report with keys: missing_values, constant_sensors, infinite_values,
        total_rows, total_sensors.

    Raises
    ------
    TypeError
        If df is not a pandas DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")

    sensor_cols = [c for c in df.columns if c.startswith("s")]
    missing = {col: int(n) for col, n in df[sensor_cols].isnull().sum().items() if n > 0}
    constant = df[sensor_cols].columns[df[sensor_cols].std() < 1e-6].tolist()
    infinite = {col: int(np.isinf(df[col]).sum()) for col in sensor_cols if np.isinf(df[col]).any()}

    report = {
        "missing_values":  missing,
        "constant_sensors": constant,
        "infinite_values": infinite,
        "total_rows":    len(df),
        "total_sensors": len(sensor_cols),
    }
    logger.info(
        "Validation: %d missing cols, %d constant sensors, %d infinite cols",
        len(missing), len(constant), len(infinite),
    )
    return report


def clean_data(df: pd.DataFrame, dataset_id: str | None = None) -> pd.DataFrame:
    """
    Drop dataset-specific constant sensors and normalize kept sensors to [0, 1].

    Reads drop_sensors and keep_sensors from the per-dataset config block.
    Saves the fitted MinMaxScaler to data/processed/scaler_{dataset_id}.pkl.

    Parameters
    ----------
    df : pd.DataFrame
        Raw dataset DataFrame with sensor columns present.
    dataset_id : str or None
        Target dataset ('FD001'–'FD004'). Defaults to config active_dataset.

    Returns
    -------
    pd.DataFrame
        Cleaned DataFrame: constant sensors removed, kept sensors normalized.

    Raises
    ------
    TypeError
        If df is not a pandas DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")

    dataset_id = _resolve_dataset_id(dataset_id)
    cfg = _load_config()
    ds_cfg = cfg["data"]["datasets"][dataset_id]

    drop_cols = [c for c in ds_cfg["drop_sensors"] if c in df.columns]
    keep_cols = [c for c in ds_cfg["keep_sensors"] if c in df.columns]

    cleaned = df.drop(columns=drop_cols).copy()
    scaler = MinMaxScaler()
    cleaned[keep_cols] = scaler.fit_transform(cleaned[keep_cols])

    processed_dir = _PROJECT_ROOT / cfg["data"]["processed_dir"]
    processed_dir.mkdir(parents=True, exist_ok=True)
    with (processed_dir / f"scaler_{dataset_id}.pkl").open("wb") as fh:
        pickle.dump(scaler, fh)

    logger.info(
        "Cleaned (%s): dropped %d sensors, normalized %d sensors",
        dataset_id, len(drop_cols), len(keep_cols),
    )
    return cleaned


def generate_rul_labels(df: pd.DataFrame, cap: int = 130) -> pd.DataFrame:
    """
    Apply piecewise linear RUL labeling to each engine's cycle data.

    RUL = min(max_cycle_for_engine − current_cycle, cap).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing 'unit_id' and 'cycle' columns.
    cap : int
        Maximum RUL value to assign (default 130 per CMAPSS convention).

    Returns
    -------
    pd.DataFrame
        Input DataFrame with a new 'RUL' column appended.

    Raises
    ------
    TypeError
        If df is not a pandas DataFrame.
    ValueError
        If required columns are absent.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    missing_cols = {"unit_id", "cycle"} - set(df.columns)
    if missing_cols:
        raise ValueError(f"DataFrame missing required columns: {missing_cols}")

    labeled = df.copy()
    max_cycles = labeled.groupby("unit_id")["cycle"].max()
    labeled["RUL"] = labeled.apply(
        lambda row: min(int(max_cycles[row["unit_id"]] - row["cycle"]), cap), axis=1
    )
    logger.info("RUL labels generated: cap=%d, engines=%d", cap, labeled["unit_id"].nunique())
    return labeled


def visualize_trends(df: pd.DataFrame, engine_id: int, dataset_id: str | None = None) -> Path:
    """
    Plot all kept sensor readings over time for one engine and save the chart.

    Parameters
    ----------
    df : pd.DataFrame
        Cleaned DataFrame with 'unit_id', 'cycle', and sensor columns present.
    engine_id : int
        The engine unit_id to visualize.
    dataset_id : str or None
        Target dataset ('FD001'–'FD004'). Defaults to config active_dataset.

    Returns
    -------
    Path
        Absolute path to the saved PNG chart file.

    Raises
    ------
    TypeError
        If df is not a DataFrame or engine_id is not an integer.
    ValueError
        If engine_id is not present in the DataFrame.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"df must be a pandas DataFrame, got {type(df)}")
    if not isinstance(engine_id, (int, np.integer)):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"engine_id {engine_id} not found in DataFrame")

    dataset_id = _resolve_dataset_id(dataset_id)
    cfg = _load_config()
    ds_cfg = cfg["data"]["datasets"][dataset_id]

    sensor_cols = [c for c in ds_cfg["keep_sensors"] if c in df.columns]
    engine_df = df[df["unit_id"] == engine_id].sort_values("cycle")

    fig, axes = plt.subplots(len(sensor_cols), 1, figsize=(12, len(sensor_cols) * 1.5), sharex=True)
    if len(sensor_cols) == 1:
        axes = [axes]
    for ax, col in zip(axes, sensor_cols):
        ax.plot(engine_df["cycle"], engine_df[col], linewidth=0.8)
        ax.set_ylabel(col, fontsize=7)
        ax.tick_params(labelsize=6)
    axes[-1].set_xlabel("Cycle")
    fig.suptitle(f"Engine {engine_id} ({dataset_id}) — Sensor Trends", fontsize=11)
    plt.tight_layout()

    charts_dir = _PROJECT_ROOT / cfg["data"]["processed_dir"] / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    output_path = charts_dir / f"engine_{engine_id}_{dataset_id}_trends.png"
    fig.savefig(output_path, dpi=100)
    plt.close(fig)

    logger.info("Saved sensor trend chart: %s", output_path)
    return output_path
