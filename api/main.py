"""FastAPI backend exposing the SEN pipeline over REST.

Endpoints:
    GET  /                          -> service info + endpoint index
    GET  /health                    -> service liveness probe
    GET  /engines                   -> list of engine_ids in the active dataset
    GET  /engine/{engine_id}/status -> latest RUL + alert status
    POST /analyze                   -> kicks off the full three-agent crew
    /ingest/*                       -> custom-dataset upload + mapping pipeline
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import active_dataset, get_active_dataframe, load_config
from api.auth import verify_api_key
from api.ingestion_routes import router as ingestion_router
from crews.maintenance_crew import run_pipeline
from ingestion.heuristic import (
    compute_engine_status,
    is_custom_dataset,
    load_custom_dataframe,
)
from tools.predict_tools import check_thresholds, predict_rul
from tools.stream_tools import stream_sensors

logger = logging.getLogger(__name__)


class EngineStatus(BaseModel):
    """Latest model prediction for one engine."""

    engine_id: int
    predicted_rul: float
    severity: str
    alert: bool
    threshold: float


class AnalyzeRequest(BaseModel):
    """Payload for POST /analyze."""

    engine_id: int = Field(..., gt=0, description="Positive engine_id to analyze")


class AnalyzeResponse(BaseModel):
    """Result of a full crew kickoff."""

    engine_id: int
    result: str


def _build_app() -> FastAPI:
    """Construct the FastAPI app with CORS middleware from config."""
    config = load_config()
    api_cfg = config["api"]
    app = FastAPI(
        title="SEN — Sensor Engine Network",
        description="Real-time predictive maintenance API.",
        version="1.0.0",
        dependencies=[Depends(verify_api_key)],
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_cfg.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = _build_app()
app.include_router(ingestion_router)


def _resolve_dataframe(dataset_id: str | None):
    """Return the active DataFrame for either a CMAPSS or custom dataset_id."""
    if dataset_id and is_custom_dataset(dataset_id):
        return load_custom_dataframe(dataset_id)
    return get_active_dataframe(dataset_id)


@app.get("/")
def root() -> dict[str, object]:
    """Service info + endpoint index for casual visitors."""
    return {
        "name": "SEN — Sensor Engine Network",
        "version": "1.0.0",
        "description": "Real-time predictive maintenance API for rotating machinery.",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "engines": "/engines",
            "engine_status": "/engine/{engine_id}/status",
            "analyze": "POST /analyze",
            "ingest_upload": "POST /ingest/upload",
            "ingest_schema": "POST /ingest/schema",
            "ingest_datasets": "GET /ingest/datasets",
            "ingest_delete": "DELETE /ingest/dataset/{id}",
            "ingest_stream": "POST /ingest/stream/{dataset_id}",
            "ingest_stream_latest": "GET /ingest/stream/{dataset_id}/{unit_id}/latest",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Service liveness probe."""
    return {"status": "ok"}


@app.get("/engines", response_model=list[int])
def list_engines(dataset: str | None = Query(default=None)) -> list[int]:
    """Return sorted list of engine_ids in the requested or active dataset."""
    df = _resolve_dataframe(dataset)
    return sorted(int(unit_id) for unit_id in df["unit_id"].unique())


def _latest_status(engine_id: int, dataset_id: str | None) -> EngineStatus:
    """Compute the latest RUL + alert payload for one engine_id."""
    df = _resolve_dataframe(dataset_id)
    if engine_id not in df["unit_id"].values:
        raise HTTPException(404, f"engine_id {engine_id} not found")
    if dataset_id and is_custom_dataset(dataset_id):
        status = compute_engine_status(df, engine_id)
        return EngineStatus(
            engine_id=status.engine_id,
            predicted_rul=status.predicted_rul,
            severity=status.severity if status.severity != "watch" else "watch",
            alert=status.alert,
            threshold=status.threshold,
        )
    windows = list(stream_sensors(df, engine_id))
    if not windows:
        raise HTTPException(422, f"engine {engine_id} has no full sensor window")
    rul = predict_rul(windows[-1], dataset_id=dataset_id)
    alert = check_thresholds(engine_id, rul)
    config = load_config()
    threshold = float(config["monitoring"]["rul_alert_threshold"])
    if alert is None:
        return EngineStatus(
            engine_id=engine_id, predicted_rul=rul,
            severity="healthy", alert=False, threshold=threshold,
        )
    return EngineStatus(
        engine_id=alert["engine_id"], predicted_rul=alert["rul"],
        severity=alert["severity"], alert=alert["alert"],
        threshold=alert["threshold"],
    )


@app.get("/engine/{engine_id}/status", response_model=EngineStatus)
def engine_status(
    engine_id: int, dataset: str | None = Query(default=None)
) -> EngineStatus:
    """Return the latest RUL + alert state for an engine in the chosen dataset."""
    return _latest_status(engine_id, dataset)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest, dataset: str | None = Query(default=None)
) -> AnalyzeResponse:
    """Kick off the full Monitor->Diagnostic->Advisor crew for one engine.

    The optional `dataset` query parameter routes the run to a specific
    custom (uploaded) dataset; the agent tools pick it up via the
    `active_dataset` ContextVar so their no-arg `get_active_dataframe()`
    calls return the right data.
    """
    df = _resolve_dataframe(dataset)
    if request.engine_id not in df["unit_id"].values:
        raise HTTPException(404, f"engine_id {request.engine_id} not found")
    logger.info(
        "API /analyze triggered for engine %d (dataset=%s)",
        request.engine_id,
        dataset or "<default>",
    )
    with active_dataset(dataset):
        result = run_pipeline(request.engine_id)
    return AnalyzeResponse(engine_id=request.engine_id, result=result)
