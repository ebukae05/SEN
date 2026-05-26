"""Two-step ingestion pipeline: preview, then process.

`preview` runs an uploaded file through the CDH layer with no schema mapping
to surface columns and quality issues for the wizard's mapping step.
`process` applies the user's sensor schema, validates it against the
ingestion rules, normalizes sensors, and persists the processed CSV and
fitted scaler for downstream inference.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from sklearn.preprocessing import MinMaxScaler

from cdh.handler import (
    DataQualityReport,
    check_data_quality,
    detect_format,
    load_file,
)
from ingestion.store import (
    DatasetMeta,
    SensorMapping,
    SensorSchema,
    StoreBackend,
    get_store,
)
from preprocess import generate_rul_labels, normalize_sensors

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
class UploadPreview:
    """Result of the first wizard step — what the user needs to start mapping."""

    upload_id: str
    filename: str
    format: str
    row_count: int
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    quality: DataQualityReport
    suggestions: dict[str, str] = field(default_factory=dict)


@dataclass
class ProcessResult:
    """Outcome of the `process` step."""

    dataset_id: str
    status: str
    meta: DatasetMeta
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def save_upload_and_preview(
    file_bytes: bytes, filename: str, store: StoreBackend | None = None
) -> UploadPreview:
    """Persist an upload and return the wizard preview payload.

    Args:
        file_bytes: Raw upload bytes.
        filename: Original filename (used for format detection).
        store: Override the global store (test-only).

    Returns:
        UploadPreview describing detected columns and quality issues.
    """
    config = _load_config()
    max_bytes = int(config["ingestion"]["max_upload_mb"]) * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise ValueError(
            f"Upload is {len(file_bytes)} bytes; max allowed is {max_bytes}"
        )
    backend = store or get_store()
    upload_id, path = backend.save_upload(file_bytes, filename)
    try:
        preview = _build_preview(path, upload_id, filename)
    except Exception:
        backend.discard_upload(upload_id)
        raise
    return preview


def _build_preview(path: Path, upload_id: str, filename: str) -> UploadPreview:
    """Load a saved upload and build its preview payload (CDH validation only)."""
    config = _load_config()
    fmt = detect_format(path)
    df = load_file(path)
    sample_n = int(config["ingestion"]["preview_sample_rows"])
    quality = check_data_quality(df, config["cdh"])
    suggestions = _suggest_roles(df.columns.tolist())
    sample = df.head(sample_n).where(pd.notna(df.head(sample_n)), None).to_dict(orient="records")
    return UploadPreview(
        upload_id=upload_id,
        filename=filename,
        format=fmt,
        row_count=len(df),
        columns=df.columns.tolist(),
        sample_rows=sample,
        quality=quality,
        suggestions=suggestions,
    )


def _suggest_roles(columns: list[str]) -> dict[str, str]:
    """Heuristic auto-suggestion of role per column based on common names."""
    suggestions: dict[str, str] = {}
    for col in columns:
        lower = col.lower()
        if lower in {"unit_id", "engine_id", "asset_id", "machine_id", "id"}:
            suggestions[col] = "unit_id"
        elif lower in {"cycle", "time", "timestamp", "step"}:
            suggestions[col] = "cycle"
        elif lower in {"rul", "remaining_useful_life", "ttf", "time_to_failure"}:
            suggestions[col] = "rul"
        else:
            suggestions[col] = "sensor"
    return suggestions


def _validate_schema(schema: SensorSchema) -> list[str]:
    """Return a list of structural errors in the schema (empty = OK)."""
    config = _load_config()["ingestion"]
    errors: list[str] = []
    if not schema.unit_id_column:
        errors.append("unit_id_column is required")
    if not schema.cycle_column:
        errors.append("cycle_column is required")
    sensor_cols = [m for m in schema.mappings if m.role == "sensor"]
    if len(sensor_cols) < int(config["min_sensors"]):
        errors.append(
            f"At least {config['min_sensors']} sensor columns required; got {len(sensor_cols)}"
        )
    if schema.industry not in set(config["supported_industries"]):
        errors.append(f"Unsupported industry: {schema.industry}")
    if schema.asset_type not in set(config["supported_asset_types"]):
        errors.append(f"Unsupported asset_type: {schema.asset_type}")
    tags = set(config["sensor_type_tags"])
    for mapping in sensor_cols:
        if mapping.type_tag not in tags:
            errors.append(
                f"Sensor {mapping.column_name!r} has unknown type_tag {mapping.type_tag!r}"
            )
    return errors


def _build_rename_map(schema: SensorSchema) -> tuple[dict[str, str], list[str]]:
    """Return (rename_map, sensor_internal_names) for applying the schema.

    Sensors keep their user-supplied column_name as the internal name so that
    downstream consumers can match display_name back to columns.
    """
    rename_map: dict[str, str] = {}
    sensor_cols: list[str] = []
    if schema.unit_id_column:
        rename_map[schema.unit_id_column] = "unit_id"
    if schema.cycle_column:
        rename_map[schema.cycle_column] = "cycle"
    if schema.rul_column:
        rename_map[schema.rul_column] = "RUL"
    for mapping in schema.mappings:
        if mapping.role == "sensor":
            sensor_cols.append(mapping.column_name)
    return rename_map, sensor_cols


def _validate_data_quality(
    df: pd.DataFrame, sensor_cols: list[str]
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) from runtime data checks on the renamed df."""
    config = _load_config()["ingestion"]
    errors: list[str] = []
    warnings: list[str] = []
    if "unit_id" not in df.columns:
        errors.append("Renamed dataframe is missing unit_id column")
        return errors, warnings
    if "cycle" not in df.columns:
        errors.append("Renamed dataframe is missing cycle column")
        return errors, warnings
    min_rows = int(config["min_rows_per_unit"])
    short_units = df.groupby("unit_id").size().pipe(lambda s: s[s < min_rows]).index.tolist()
    if short_units:
        errors.append(
            f"{len(short_units)} unit(s) have fewer than {min_rows} rows; "
            f"first: {short_units[:5]}"
        )
    monotonic_failures = []
    for unit_id, group in df.groupby("unit_id"):
        if not group["cycle"].is_monotonic_increasing:
            monotonic_failures.append(int(unit_id))
    if monotonic_failures:
        errors.append(
            f"{len(monotonic_failures)} unit(s) have non-monotonic cycles; "
            f"first: {monotonic_failures[:5]}"
        )
    if sensor_cols:
        missing_pct = df[sensor_cols].isna().mean() * 100
        warn_threshold = float(config["missing_value_warn_pct"])
        for col, pct in missing_pct.items():
            if pct > warn_threshold:
                warnings.append(f"{col}: {pct:.1f}% missing values (forward-filled)")
    return errors, warnings


def _apply_rename_with_drop(df: pd.DataFrame, rename_map: dict[str, str]) -> pd.DataFrame:
    """Rename columns in rename_map; drop columns not referenced anywhere."""
    keep = set(rename_map.keys())
    renamed = df[[c for c in df.columns if c in keep]].rename(columns=rename_map)
    return renamed


def _forward_fill_sensors(df: pd.DataFrame, sensor_cols: list[str]) -> pd.DataFrame:
    """Forward-fill missing sensor values within each unit_id group."""
    if not sensor_cols:
        return df
    df = df.copy()
    df[sensor_cols] = (
        df.groupby("unit_id", sort=False)[sensor_cols]
        .transform(lambda g: g.ffill().bfill())
    )
    return df


def process_upload(
    schema: SensorSchema, store: StoreBackend | None = None
) -> ProcessResult:
    """Apply a sensor schema to an upload and persist the processed dataset.

    Args:
        schema: User-defined SensorSchema referencing a saved upload_id.
        store: Override the global store (test-only).

    Returns:
        ProcessResult — dataset_id, status, persisted metadata, and any
        errors or warnings raised during processing.
    """
    config = _load_config()
    backend = store or get_store()
    structural_errors = _validate_schema(schema)
    if structural_errors:
        return _failed_result_no_dataset(schema, structural_errors)
    upload_path = backend.get_upload_path(schema.upload_id)
    raw_df = load_file(upload_path)
    rename_map, sensor_cols = _build_rename_map(schema)
    missing_cols = [c for c in rename_map if c not in raw_df.columns]
    if missing_cols:
        return _failed_result_no_dataset(
            schema, [f"Schema references missing columns: {missing_cols}"]
        )
    renamed = _apply_rename_with_drop(raw_df, rename_map)
    runtime_errors, runtime_warnings = _validate_data_quality(renamed, sensor_cols)
    if runtime_errors:
        return _failed_result_no_dataset(schema, runtime_errors)
    filled = _forward_fill_sensors(renamed, sensor_cols)
    low, high = config["preprocessing"]["normalize_range"]
    normalized, scaler = normalize_sensors(filled, sensor_cols, (low, high))
    if "RUL" not in normalized.columns:
        normalized = generate_rul_labels(normalized, config["preprocessing"]["rul_cap"])
        has_rul = False
    else:
        has_rul = True
    dataset_id, dataset_dir = backend.create_dataset(schema, upload_path.name)
    normalized.to_csv(backend.get_processed_path(dataset_id), index=False)
    with backend.get_scaler_path(dataset_id).open("wb") as scaler_file:
        pickle.dump(scaler, scaler_file)
    backend.save_schema(dataset_id, schema)
    meta = DatasetMeta(
        dataset_id=dataset_id,
        asset_id=schema.asset_id,
        asset_type=schema.asset_type,
        industry=schema.industry,
        tenant_id=schema.tenant_id,
        source="custom",
        status="ready",
        sensor_count=len(sensor_cols),
        engine_count=int(normalized["unit_id"].nunique()),
        row_count=int(len(normalized)),
        has_rul=has_rul,
        sensor_display_names={
            m.column_name: (m.display_name or m.column_name)
            for m in schema.mappings
            if m.role == "sensor"
        },
    )
    backend.save_meta(meta)
    logger.info(
        "Processed custom dataset %s: %d engines, %d sensors, %d rows",
        dataset_id, meta.engine_count, meta.sensor_count, meta.row_count,
    )
    return ProcessResult(
        dataset_id=dataset_id,
        status="ready",
        meta=meta,
        warnings=runtime_warnings,
    )


def _failed_result_no_dataset(
    schema: SensorSchema, errors: list[str]
) -> ProcessResult:
    """Build a failure ProcessResult that did not create a dataset_id."""
    meta = DatasetMeta(
        dataset_id="",
        asset_id=schema.asset_id,
        asset_type=schema.asset_type,
        industry=schema.industry,
        tenant_id=schema.tenant_id,
        status="failed",
        error="; ".join(errors),
    )
    return ProcessResult(dataset_id="", status="failed", meta=meta, errors=errors)
