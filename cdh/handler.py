"""Command and Data Handling (CDH) layer.

Sits between raw sensor inputs and SEN's internal preprocessing pipeline.
Accepts CSV, JSON, and Excel (.xlsx) files; standardizes them into SEN's
internal Pandas DataFrame format; flags quality issues; and prioritizes
engines by RUL when multiple are present.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import yaml

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


@dataclass
class DataQualityReport:
    """Structured summary of validation results from CDH processing."""

    is_valid: bool = True
    rows_loaded: int = 0
    engines_loaded: int = 0
    missing_values: int = 0
    out_of_range_values: int = 0
    missing_required_columns: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def detect_format(file_path: Path) -> str:
    """Infer the input format from the file extension.

    Args:
        file_path: Path to the input file.

    Returns:
        One of 'csv', 'json', 'xlsx'.

    Raises:
        ValueError: If the extension is not in the supported list.
    """
    if not isinstance(file_path, Path):
        raise TypeError("file_path must be a pathlib.Path")
    extension = file_path.suffix.lower().lstrip(".")
    supported = set(_load_config()["cdh"]["supported_formats"])
    if extension not in supported:
        raise ValueError(
            f"Unsupported format '{extension}'. Supported: {sorted(supported)}"
        )
    return extension


def _load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file into a DataFrame."""
    return pd.read_csv(file_path)


def _load_json(file_path: Path) -> pd.DataFrame:
    """Load a JSON file (records orientation) into a DataFrame."""
    return pd.read_json(file_path, orient="records")


def _load_xlsx(file_path: Path) -> pd.DataFrame:
    """Load an Excel .xlsx file into a DataFrame via openpyxl."""
    return pd.read_excel(file_path, engine="openpyxl")


_LOADERS: dict[str, Callable[[Path], pd.DataFrame]] = {
    "csv": _load_csv,
    "json": _load_json,
    "xlsx": _load_xlsx,
}


def load_file(file_path: Path) -> pd.DataFrame:
    """Load a file into a DataFrame, dispatching by detected format.

    Args:
        file_path: Path to the input file.

    Returns:
        Raw DataFrame parsed from the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the format is unsupported or the file cannot be parsed.
    """
    if not isinstance(file_path, Path):
        raise TypeError("file_path must be a pathlib.Path")
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")
    fmt = detect_format(file_path)
    try:
        return _LOADERS[fmt](file_path)
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"File is empty: {file_path}") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Could not parse {fmt} file {file_path}: {exc}") from exc


def apply_schema(
    df: pd.DataFrame, schema_map: dict[str, str] | None
) -> pd.DataFrame:
    """Rename columns from user-defined names to SEN's internal names.

    Args:
        df: Raw DataFrame straight from load_file.
        schema_map: Mapping of user column names to SEN column names. If None,
            the DataFrame is returned unchanged.

    Returns:
        DataFrame with columns renamed per schema_map.

    Raises:
        ValueError: If schema_map references columns absent from df.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if schema_map is None:
        return df
    unknown = [user_col for user_col in schema_map if user_col not in df.columns]
    if unknown:
        raise ValueError(f"Schema map references missing columns: {unknown}")
    return df.rename(columns=schema_map)


def validate_required_columns(
    df: pd.DataFrame, required: list[str]
) -> list[str]:
    """Return the list of required columns absent from the DataFrame.

    Args:
        df: DataFrame to validate.
        required: List of columns that must be present.

    Returns:
        Empty list if all required columns are present; otherwise the missing names.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    return [column for column in required if column not in df.columns]


def _numeric_columns(df: pd.DataFrame) -> list[str]:
    """Return the names of numeric columns in df."""
    return df.select_dtypes(include="number").columns.tolist()


def _flag_out_of_range(
    df: pd.DataFrame, low: float, high: float
) -> int:
    """Count cell values outside [low, high] across numeric columns."""
    numeric_cols = _numeric_columns(df)
    if not numeric_cols:
        return 0
    mask = (df[numeric_cols] < low) | (df[numeric_cols] > high)
    return int(mask.to_numpy().sum())


def check_data_quality(
    df: pd.DataFrame, cdh_config: dict[str, Any]
) -> DataQualityReport:
    """Produce a structured quality report for a standardized DataFrame."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    report = DataQualityReport(rows_loaded=len(df))
    missing_required = validate_required_columns(df, cdh_config["required_columns"])
    if missing_required:
        report.is_valid = False
        report.missing_required_columns = missing_required
        report.errors.append(f"Missing required columns: {missing_required}")
    report.missing_values = int(df.isna().sum().sum())
    if report.missing_values:
        report.warnings.append(f"{report.missing_values} missing sensor readings")
    low, high = cdh_config["out_of_range"]["min"], cdh_config["out_of_range"]["max"]
    report.out_of_range_values = _flag_out_of_range(df, low, high)
    if report.out_of_range_values:
        report.warnings.append(
            f"{report.out_of_range_values} values outside [{low}, {high}]"
        )
    if "unit_id" in df.columns:
        report.engines_loaded = int(df["unit_id"].nunique())
    return report


def _engine_rank(
    df: pd.DataFrame, rul_map: dict[int, float] | None
) -> list[int]:
    """Return engines ordered by failure-risk priority (highest risk first)."""
    if rul_map:
        return sorted(rul_map.keys(), key=lambda uid: rul_map[uid])
    logger.warning("No RUL map provided; using max-cycle heuristic")
    max_cycles = df.groupby("unit_id")["cycle"].max()
    return max_cycles.sort_values(ascending=False).index.tolist()


def prioritize_engines(
    df: pd.DataFrame, rul_map: dict[int, float] | None = None
) -> pd.DataFrame:
    """Re-order rows so engines closer to failure come first (RUL asc; cycle desc fallback)."""
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if "unit_id" not in df.columns:
        raise ValueError("DataFrame must contain 'unit_id' to prioritize")
    ranked = _engine_rank(df, rul_map)
    rank_lookup = {unit_id: rank for rank, unit_id in enumerate(ranked)}
    df = df.copy()
    df["_priority"] = df["unit_id"].map(rank_lookup).fillna(len(ranked))
    return (
        df.sort_values("_priority", kind="stable")
        .drop(columns="_priority")
        .reset_index(drop=True)
    )


def _log_report(report: DataQualityReport) -> None:
    """Emit a report's errors and warnings to the module logger."""
    for error_msg in report.errors:
        logger.error(error_msg)
    for warning_msg in report.warnings:
        logger.warning(warning_msg)


def handle(
    file_path: Path,
    schema_map: dict[str, str] | None = None,
    rul_map: dict[int, float] | None = None,
) -> tuple[pd.DataFrame, DataQualityReport]:
    """Run the full CDH pipeline: detect → load → adapt → validate → prioritize."""
    if not isinstance(file_path, Path):
        raise TypeError("file_path must be a pathlib.Path")
    config = _load_config()
    raw_df = load_file(file_path)
    logger.info("Loaded %d rows from %s", len(raw_df), file_path)
    adapted_df = apply_schema(raw_df, schema_map)
    report = check_data_quality(adapted_df, config["cdh"])
    _log_report(report)
    if not report.is_valid:
        return adapted_df, report
    ordered_df = prioritize_engines(adapted_df, rul_map)
    return ordered_df, report
