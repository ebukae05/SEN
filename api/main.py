"""FastAPI backend exposing the SEN pipeline over REST.

Endpoints:
    GET  /                        -> service info + endpoint index
    GET  /health                  -> service liveness probe
    GET  /engines                 -> list of engine_ids in the active dataset
    GET  /engine/{engine_id}/status -> latest RUL + alert status
    POST /analyze                 -> kicks off the full three-agent crew
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents import get_active_dataframe, load_config
from crews.maintenance_crew import run_pipeline
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


@app.get("/")
def root() -> dict[str, object]:
    """Service info + endpoint index for casual visitors."""
    return {
        "name": "SEN — Sensor Engine Network",
        "version": "1.0.0",
        "description": "Real-time predictive maintenance API for turbofan engines.",
        "docs": "/docs",
        "endpoints": {
            "health": "/health",
            "engines": "/engines",
            "engine_status": "/engine/{engine_id}/status",
            "analyze": "POST /analyze",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    """Service liveness probe."""
    return {"status": "ok"}


@app.get("/engines", response_model=list[int])
def list_engines() -> list[int]:
    """Return sorted list of engine_ids in the active processed dataset."""
    df = get_active_dataframe()
    return sorted(int(unit_id) for unit_id in df["unit_id"].unique())


def _latest_status(engine_id: int) -> EngineStatus:
    """Compute the latest RUL + alert payload for one engine_id."""
    df = get_active_dataframe()
    if engine_id not in df["unit_id"].values:
        raise HTTPException(404, f"engine_id {engine_id} not found")
    windows = list(stream_sensors(df, engine_id))
    if not windows:
        raise HTTPException(422, f"engine {engine_id} has no full sensor window")
    rul = predict_rul(windows[-1])
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
def engine_status(engine_id: int) -> EngineStatus:
    """Return the latest CNN-LSTM RUL prediction + alert state."""
    return _latest_status(engine_id)


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """Kick off the full Monitor->Diagnostic->Advisor crew for one engine."""
    df = get_active_dataframe()
    if request.engine_id not in df["unit_id"].values:
        raise HTTPException(404, f"engine_id {request.engine_id} not found")
    logger.info("API /analyze triggered for engine %d", request.engine_id)
    result = run_pipeline(request.engine_id)
    return AnalyzeResponse(engine_id=request.engine_id, result=result)
