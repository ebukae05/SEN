"""FastAPI routes for the custom-dataset ingestion pipeline.

Mounts under the /ingest prefix:
    POST   /ingest/upload         multipart upload → preview + quality report
    POST   /ingest/schema         apply user schema → preprocess → persist
    GET    /ingest/datasets       list CMAPSS + custom datasets
    DELETE /ingest/dataset/{id}   remove a custom dataset (CMAPSS undeletable)
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any, Literal

import yaml
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from agents import load_config
from ingestion.heuristic import is_custom_dataset
from ingestion.pipeline import (
    UploadPreview,
    process_upload,
    save_upload_and_preview,
)
from ingestion.store import (
    DatasetMeta,
    SensorMapping,
    SensorSchema,
    get_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class SensorMappingIn(BaseModel):
    """One row from the wizard's sensor mapping table."""

    column_name: str
    role: Literal["unit_id", "cycle", "sensor", "rul", "ignore"]
    display_name: str = ""
    type_tag: str = "custom"
    unit: str = ""
    warning_threshold: float | None = None
    critical_threshold: float | None = None


class SchemaPayload(BaseModel):
    """Body for POST /ingest/schema."""

    upload_id: str
    asset_id: str = Field(..., min_length=1)
    asset_type: str
    industry: str
    cycle_column: str
    unit_id_column: str
    rul_column: str | None = None
    mappings: list[SensorMappingIn]
    tenant_id: str = "default"


class QualityReportOut(BaseModel):
    """Serialized DataQualityReport for the wizard."""

    is_valid: bool
    rows_loaded: int
    engines_loaded: int
    missing_values: int
    out_of_range_values: int
    missing_required_columns: list[str]
    errors: list[str]
    warnings: list[str]


class UploadPreviewOut(BaseModel):
    """Response payload for POST /ingest/upload."""

    upload_id: str
    filename: str
    format: str
    row_count: int
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    quality: QualityReportOut
    suggestions: dict[str, str]


class DatasetMetaOut(BaseModel):
    """Serialized DatasetMeta + a small derived `label` field for UI."""

    dataset_id: str
    asset_id: str
    asset_type: str
    industry: str
    tenant_id: str
    source: str
    status: str
    created_at: str
    sensor_count: int
    engine_count: int
    row_count: int
    has_rul: bool
    sensor_display_names: dict[str, str] = {}
    label: str = ""
    error: str | None = None


class ProcessOut(BaseModel):
    """Response payload for POST /ingest/schema."""

    dataset_id: str
    status: str
    meta: DatasetMetaOut
    errors: list[str] = []
    warnings: list[str] = []


def _quality_to_out(quality: Any) -> QualityReportOut:
    """Convert a DataQualityReport dataclass into its API shape."""
    return QualityReportOut(**asdict(quality))


def _preview_to_out(preview: UploadPreview) -> UploadPreviewOut:
    """Convert an UploadPreview dataclass into its API shape."""
    return UploadPreviewOut(
        upload_id=preview.upload_id,
        filename=preview.filename,
        format=preview.format,
        row_count=preview.row_count,
        columns=preview.columns,
        sample_rows=preview.sample_rows,
        quality=_quality_to_out(preview.quality),
        suggestions=preview.suggestions,
    )


def _meta_to_out(meta: DatasetMeta) -> DatasetMetaOut:
    """Convert a DatasetMeta into the API shape, attaching a UI-friendly label."""
    label = meta.asset_id if meta.source == "custom" else meta.dataset_id
    return DatasetMetaOut(**asdict(meta), label=label)


def _cmapss_metas() -> list[DatasetMetaOut]:
    """Return DatasetMetaOut entries for the bundled CMAPSS datasets."""
    config = load_config()
    out: list[DatasetMetaOut] = []
    for dataset_id in config["data"]["datasets"]:
        out.append(
            DatasetMetaOut(
                dataset_id=dataset_id,
                asset_id=dataset_id,
                asset_type="turbofan_engine",
                industry="aerospace",
                tenant_id="default",
                source="cmapss",
                status="ready",
                created_at="",
                sensor_count=int(config["preprocessing"]["expected_sensor_count_after_drop"]),
                engine_count=0,
                row_count=0,
                has_rul=True,
                label=dataset_id,
            )
        )
    return out


@router.post("/upload", response_model=UploadPreviewOut)
async def upload_file(file: UploadFile = File(...)) -> UploadPreviewOut:
    """Accept a CSV/JSON/XLSX file and return preview + data quality report."""
    if not file.filename:
        raise HTTPException(400, "Upload is missing a filename")
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Uploaded file is empty")
    try:
        preview = save_upload_and_preview(contents, file.filename)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except yaml.YAMLError as exc:
        raise HTTPException(500, f"Config error: {exc}") from exc
    return _preview_to_out(preview)


@router.post("/schema", response_model=ProcessOut)
def submit_schema(payload: SchemaPayload) -> ProcessOut:
    """Apply a sensor schema to a previously uploaded file."""
    schema = SensorSchema(
        upload_id=payload.upload_id,
        asset_id=payload.asset_id,
        asset_type=payload.asset_type,
        industry=payload.industry,
        cycle_column=payload.cycle_column,
        unit_id_column=payload.unit_id_column,
        rul_column=payload.rul_column,
        tenant_id=payload.tenant_id,
        mappings=[SensorMapping(**m.model_dump()) for m in payload.mappings],
    )
    try:
        result = process_upload(schema)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    if result.status == "failed":
        return ProcessOut(
            dataset_id="",
            status="failed",
            meta=_meta_to_out(result.meta),
            errors=result.errors,
        )
    return ProcessOut(
        dataset_id=result.dataset_id,
        status=result.status,
        meta=_meta_to_out(result.meta),
        warnings=result.warnings,
    )


@router.get("/datasets", response_model=list[DatasetMetaOut])
def list_datasets() -> list[DatasetMetaOut]:
    """List all datasets: bundled CMAPSS first, then user-uploaded custom."""
    out = _cmapss_metas()
    out.extend(_meta_to_out(meta) for meta in get_store().list_datasets())
    return out


@router.delete("/dataset/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str) -> None:
    """Delete a custom dataset. CMAPSS datasets cannot be deleted."""
    if not is_custom_dataset(dataset_id):
        raise HTTPException(400, "CMAPSS datasets cannot be deleted")
    if not get_store().delete_dataset(dataset_id):
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
