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
from datetime import datetime, timezone
from typing import Any, Literal

import yaml
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
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
from ingestion.stream import (
    StreamSnapshot,
    append_reading,
    get_snapshot,
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
    training_rmse: float | None = None
    trained_at: str | None = None
    n_features_trained: int | None = None
    training_error: str | None = None


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
    custom = [_meta_to_out(meta) for meta in get_store().list_datasets()]
    out.extend(custom)
    logger.info(
        "GET /ingest/datasets -> %d total (%d CMAPSS + %d custom): %s",
        len(out),
        len(out) - len(custom),
        len(custom),
        [d.dataset_id for d in out],
    )
    return out


@router.delete("/dataset/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: str) -> None:
    """Delete a custom dataset. CMAPSS datasets cannot be deleted."""
    if not is_custom_dataset(dataset_id):
        raise HTTPException(400, "CMAPSS datasets cannot be deleted")
    if not get_store().delete_dataset(dataset_id):
        raise HTTPException(404, f"Dataset not found: {dataset_id}")


class StreamReadingIn(BaseModel):
    """One real-time reading published to /ingest/stream/{dataset_id}."""

    unit_id: int = Field(..., gt=0, description="Asset / engine identifier")
    cycle: int = Field(..., ge=0, description="Monotonic cycle index for the reading")
    sensors: dict[str, float] = Field(
        ..., description="Sensor name → numeric reading for this cycle"
    )


class StreamStatusOut(BaseModel):
    """RUL/severity snapshot returned alongside a stream append."""

    engine_id: int
    predicted_rul: float
    severity: str
    alert: bool
    threshold: float


class StreamSnapshotOut(BaseModel):
    """Response body for POST /ingest/stream/{dataset_id} and GET .../latest."""

    dataset_id: str
    unit_id: int
    buffer_size: int
    window_size: int
    status: StreamStatusOut | None = None


def _dataset_exists(dataset_id: str) -> bool:
    """Return True if dataset_id is a known CMAPSS or persisted custom dataset."""
    if not is_custom_dataset(dataset_id):
        return True
    return get_store().get_meta(dataset_id) is not None


def _snapshot_to_out(snapshot: StreamSnapshot) -> StreamSnapshotOut:
    """Convert a StreamSnapshot dataclass into its API shape."""
    status_out: StreamStatusOut | None = None
    if snapshot.status is not None:
        status_out = StreamStatusOut(
            engine_id=snapshot.status.engine_id,
            predicted_rul=snapshot.status.predicted_rul,
            severity=snapshot.status.severity,
            alert=snapshot.status.alert,
            threshold=snapshot.status.threshold,
        )
    return StreamSnapshotOut(
        dataset_id=snapshot.dataset_id,
        unit_id=snapshot.unit_id,
        buffer_size=snapshot.buffer_size,
        window_size=snapshot.window_size,
        status=status_out,
    )


@router.post("/stream/{dataset_id}", response_model=StreamSnapshotOut)
def stream_reading(dataset_id: str, payload: StreamReadingIn) -> StreamSnapshotOut:
    """Append a single sensor reading to the in-memory stream buffer.

    Returns the post-append buffer size and (once at least two readings exist
    for the unit) the latest heuristic RUL/severity for that unit.
    """
    if not _dataset_exists(dataset_id):
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    snapshot = append_reading(
        dataset_id, payload.unit_id, payload.cycle, payload.sensors
    )
    return _snapshot_to_out(snapshot)


@router.get(
    "/stream/{dataset_id}/{unit_id}/latest",
    response_model=StreamSnapshotOut,
)
def stream_latest(dataset_id: str, unit_id: int) -> StreamSnapshotOut:
    """Return the current in-memory snapshot for (dataset_id, unit_id)."""
    if not _dataset_exists(dataset_id):
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    snapshot = get_snapshot(dataset_id, unit_id)
    return _snapshot_to_out(snapshot)


class TrainTriggerOut(BaseModel):
    """Response body for POST /ingest/dataset/{id}/train (202 Accepted)."""

    dataset_id: str
    status: str
    message: str


class TrainingStatusOut(BaseModel):
    """Response body for GET /ingest/dataset/{id}/training."""

    dataset_id: str
    status: str
    training_rmse: float | None = None
    trained_at: str | None = None
    n_features_trained: int | None = None
    training_error: str | None = None


def _utc_now_iso() -> str:
    """Current UTC timestamp as an ISO-8601 string with seconds precision."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _run_training(dataset_id: str) -> None:
    """Background-task body: run train_custom and persist the outcome to meta.

    Catches all exceptions so failures land in ``meta.training_error`` rather
    than vanishing into the FastAPI background-task void. Successful runs bust
    the predict_tools model cache so the next inference loads fresh weights.
    """
    from models.train import train_custom

    store = get_store()
    try:
        result = train_custom(dataset_id)
    except Exception as exc:  # noqa: BLE001 — background tasks must record any failure
        logger.exception("Training failed for dataset %s", dataset_id)
        meta = store.get_meta(dataset_id)
        if meta is not None:
            meta.status = "training_failed"
            meta.training_error = str(exc)
            store.save_meta(meta)
        return
    meta = store.get_meta(dataset_id)
    if meta is None:
        logger.error("Meta vanished after training %s; weights orphaned", dataset_id)
        return
    meta.status = "trained"
    meta.training_rmse = float(result["rmse"])
    meta.trained_at = _utc_now_iso()
    meta.n_features_trained = int(result["n_features"])
    meta.training_error = None
    store.save_meta(meta)
    try:
        from tools.predict_tools import clear_model_cache

        clear_model_cache(dataset_id)
    except ImportError:
        pass
    logger.info("Training complete for %s: rmse=%.3f", dataset_id, result["rmse"])


@router.post(
    "/dataset/{dataset_id}/train",
    response_model=TrainTriggerOut,
    status_code=202,
)
def trigger_training(
    dataset_id: str, background_tasks: BackgroundTasks
) -> TrainTriggerOut:
    """Kick off per-tenant CNN-LSTM fine-tuning as a background task.

    Returns 202 immediately; poll ``GET /ingest/dataset/{id}/training`` for
    completion. Rejects CMAPSS datasets (pretrained), unknown datasets,
    in-flight trainings, and datasets without original RUL labels.
    """
    if not is_custom_dataset(dataset_id):
        raise HTTPException(
            400, "CMAPSS datasets ship pretrained; on-the-fly training is not supported"
        )
    store = get_store()
    meta = store.get_meta(dataset_id)
    if meta is None:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    if meta.status == "training":
        raise HTTPException(409, "Training already in progress for this dataset")
    if not meta.has_rul:
        raise HTTPException(
            422,
            "Dataset has no original RUL labels. Per-tenant training requires "
            "labeled run-to-failure data; unsupervised mode is not yet "
            "implemented.",
        )
    meta.status = "training"
    meta.training_error = None
    store.save_meta(meta)
    background_tasks.add_task(_run_training, dataset_id)
    logger.info("Queued training for dataset %s", dataset_id)
    return TrainTriggerOut(
        dataset_id=dataset_id,
        status="training",
        message="Training started; poll /ingest/dataset/{id}/training for completion",
    )


@router.get(
    "/dataset/{dataset_id}/training",
    response_model=TrainingStatusOut,
)
def get_training_status(dataset_id: str) -> TrainingStatusOut:
    """Return the current training status and last-completed training metrics."""
    if not is_custom_dataset(dataset_id):
        raise HTTPException(400, "CMAPSS datasets have no training lifecycle")
    meta = get_store().get_meta(dataset_id)
    if meta is None:
        raise HTTPException(404, f"Dataset not found: {dataset_id}")
    return TrainingStatusOut(
        dataset_id=dataset_id,
        status=meta.status,
        training_rmse=meta.training_rmse,
        trained_at=meta.trained_at,
        n_features_trained=meta.n_features_trained,
        training_error=meta.training_error,
    )
