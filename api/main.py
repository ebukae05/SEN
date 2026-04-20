"""
api/main.py — FastAPI REST layer for the SEN maintenance pipeline.

Endpoints:
    GET  /health              — Liveness check.
    GET  /engines             — List all engine IDs in the processed dataset.
    GET  /engine/{id}/status  — RUL prediction + alert status for one engine.
    POST /analyze             — Run the full 4-agent crew for one engine.

Run with:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict:
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


app = FastAPI(
    title="SEN — Sensor Engine Network",
    description="Real-time turbofan engine health monitoring via 4-agent AI pipeline.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    engine_id: int


class AnalyzeResponse(BaseModel):
    engine_id: int
    result: str


class EngineStatus(BaseModel):
    engine_id: int
    predicted_rul: float
    severity: str
    alert: bool


class HealthResponse(BaseModel):
    status: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_csv_path() -> Path:
    cfg = _load_config()
    return _PROJECT_ROOT / cfg["data"]["processed_dir"] / "train_clean.csv"


def _get_engine_ids() -> list[int]:
    import pandas as pd
    path = _clean_csv_path()
    if not path.exists():
        raise FileNotFoundError("Clean dataset not found — run ingest first.")
    df = pd.read_csv(path)
    return sorted(int(x) for x in df["unit_id"].unique())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check."""
    return HealthResponse(status="ok")


@app.get("/engines", response_model=list[int])
def list_engines() -> list[int]:
    """Return all engine IDs available in the processed dataset."""
    try:
        return _get_engine_ids()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/engine/{engine_id}/status", response_model=EngineStatus)
def engine_status(engine_id: int) -> EngineStatus:
    """Predict RUL and alert status for a single engine using the CNN-LSTM model."""
    try:
        if engine_id not in _get_engine_ids():
            raise HTTPException(status_code=404, detail=f"Engine {engine_id} not found.")

        import pandas as pd
        from tools.stream_tools import stream_sensors
        from tools.predict_tools import predict_rul, check_thresholds

        cfg = _load_config()
        df = pd.read_csv(_clean_csv_path())
        windows = list(stream_sensors(df, engine_id=engine_id, window_size=cfg["model"]["sequence_length"]))
        if not windows:
            raise HTTPException(status_code=422, detail=f"Engine {engine_id} has insufficient data.")

        rul = predict_rul(windows[-1])
        alert_info = check_thresholds(engine_id, rul, threshold=cfg["monitor"]["rul_alert_threshold"])

        return EngineStatus(
            engine_id=engine_id,
            predicted_rul=round(rul, 2),
            severity=alert_info["severity"],
            alert=alert_info["alert"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Status check failed for engine %d", engine_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run the full 4-agent sequential maintenance pipeline for the given engine.

    Note: This call takes ~2-3 minutes due to LLM rate limiting (5 RPM free tier).
    """
    try:
        from crews.maintenance_crew import run_pipeline
        result = run_pipeline(engine_id=request.engine_id)
        return AnalyzeResponse(engine_id=request.engine_id, result=result)
    except Exception as exc:
        logger.exception("Pipeline failed for engine %d", request.engine_id)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Fleet snapshot endpoint ───────────────────────────────────────────────────

class EngineSnapshot(BaseModel):
    id: int
    name: str
    rul: float
    rulHistory: list[float]
    healthPercent: int
    cycleCount: int
    status: str


@app.get("/fleet", response_model=list[EngineSnapshot])
def fleet_snapshot() -> list[EngineSnapshot]:
    """
    Return a health snapshot for every engine using ground-truth RUL at the 75%
    lifecycle mark — fast, no CNN-LSTM inference required.
    """
    try:
        import pandas as pd
        cfg        = _load_config()
        threshold  = cfg["monitor"]["rul_alert_threshold"]
        df         = pd.read_csv(_clean_csv_path())
        engines    = []

        for eid in sorted(df["unit_id"].unique()):
            edf        = df[df["unit_id"] == eid].sort_values("cycle").reset_index(drop=True)
            idx        = int(len(edf) * 0.75)
            rul        = float(edf.iloc[idx]["RUL"])
            history    = [float(v) for v in edf["RUL"].iloc[max(0, idx - 9): idx + 1].tolist()]
            cycle      = int(edf.iloc[idx]["cycle"])
            health_pct = min(100, int(rul / 130 * 100))

            if rul < threshold * 0.40:
                status = "critical"
            elif rul < threshold * 0.70:
                status = "warning"
            elif rul < threshold:
                status = "caution"
            else:
                status = "healthy"

            engines.append(EngineSnapshot(
                id=int(eid),
                name=f"Engine {int(eid):03d}",
                rul=round(rul, 1),
                rulHistory=history,
                healthPercent=health_pct,
                cycleCount=cycle,
                status=status,
            ))

        return engines
    except Exception as exc:
        logger.exception("Fleet snapshot failed")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Chat endpoint (React frontend → Gemini) ───────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    system_prompt: str
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    response: str


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Proxy chat messages to Gemini via the Google GenAI API."""
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        # Build a single prompt: system context + conversation history
        history = "\n".join(
            f"{'User' if m.role == 'user' else 'Assistant'}: {m.content}"
            for m in request.messages
        )
        full_prompt = f"{request.system_prompt}\n\n{history}\n\nAssistant:"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=full_prompt,
        )
        return ChatResponse(response=response.text.strip())
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc))
