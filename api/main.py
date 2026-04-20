"""
api/main.py — FastAPI REST layer for the SEN maintenance pipeline.

Endpoints:
    GET  /health                  — Liveness check.
    GET  /engines                 — List all engine IDs in the processed dataset.
    GET  /engine/{id}/status      — RUL prediction + alert status for one engine.
    GET  /engine/{id}/sensors     — Normalized sensor history for one engine.
    POST /analyze                 — Run the full 4-agent crew for one engine.
    GET  /fleet                   — Health snapshot for all 100 engines.
    POST /api/chat                — Proxy chat messages to Gemini.

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

_ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
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
    Run a direct deep analysis for the given engine.

    Bypasses CrewAI orchestration: runs all diagnostic tools directly,
    then makes a single Gemini call for the maintenance recommendation.
    Typically completes in 10-30 seconds instead of 2-3 minutes.
    """
    try:
        result = _run_direct_analysis(request.engine_id)
        return AnalyzeResponse(engine_id=request.engine_id, result=result)
    except Exception as exc:
        logger.exception("Analysis failed for engine %d", request.engine_id)
        raise HTTPException(status_code=500, detail=str(exc))


def _run_direct_analysis(engine_id: int) -> str:
    """
    Execute the full diagnostic pipeline without CrewAI — direct tool calls only.

    Steps: load data -> predict RUL -> check thresholds -> fleet comparison ->
    sensor trends -> degradation rate -> time to critical -> Gemini recommendation
    -> PDF report.

    Parameters
    ----------
    engine_id : int
        The engine unit_id to analyse.

    Returns
    -------
    str
        Formatted analysis report combining all diagnostic results and the
        Gemini-generated maintenance recommendation.
    """
    import pandas as pd
    from tools.stream_tools import stream_sensors
    from tools.predict_tools import predict_rul, check_thresholds
    from tools.diagnostic_tools import compare_to_fleet, sensor_trends, degradation_rate
    from tools.advisor_tools import time_to_critical, recommend_action, generate_report

    cfg = _load_config()
    csv_path = _clean_csv_path()
    if not csv_path.exists():
        raise FileNotFoundError("Clean dataset not found — run ingest first.")

    df = pd.read_csv(csv_path)
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"Engine {engine_id} not found in dataset.")

    # Step 1: RUL prediction via CNN-LSTM at 75% lifecycle mark
    # (matches the fleet snapshot point so dashboard RUL and analysis RUL agree)
    logger.info("Direct analysis — engine %d — predicting RUL", engine_id)
    windows = list(stream_sensors(df, engine_id=engine_id, window_size=cfg["model"]["sequence_length"]))
    if not windows:
        raise ValueError(f"Engine {engine_id} has insufficient data for prediction.")
    window_idx = int(len(windows) * 0.75)
    rul = predict_rul(windows[window_idx])

    # Step 2: Threshold check
    alert_info = check_thresholds(engine_id, rul, threshold=cfg["monitor"]["rul_alert_threshold"])
    severity = alert_info["severity"]

    # Step 3: Fleet comparison
    logger.info("Direct analysis — engine %d — running diagnostics", engine_id)
    fleet_result = compare_to_fleet(df, engine_id)
    outlier_sensors = fleet_result["outlier_sensors"]

    # Step 4: Sensor trend analysis
    trend_result = sensor_trends(df, engine_id)
    top_declining = trend_result["ranked_declining"][:3]

    # Step 5: Degradation rate
    deg_result = degradation_rate(df, engine_id)
    ratio = deg_result["ratio"]
    deg_severity = deg_result["severity"]

    # Step 6: Time to critical
    crit_result = time_to_critical(rul, ratio)
    urgency = crit_result["urgency"]
    cycles_to_critical = crit_result["cycles_to_critical"]

    # Step 7: Single Gemini call for recommendation
    logger.info("Direct analysis — engine %d — requesting Gemini recommendation", engine_id)
    diagnosis = {
        "engine_id": engine_id,
        "rul": round(rul, 2),
        "severity": severity,
        "ratio": ratio,
        "ranked_declining": top_declining,
        "urgency": urgency,
    }
    recommendation = recommend_action(diagnosis)

    # Step 8: PDF report
    full_diagnosis = {
        **diagnosis,
        "cycles_to_critical": cycles_to_critical,
        "degradation_severity": deg_severity,
        "outlier_sensors": outlier_sensors,
    }
    pdf_path = generate_report(engine_id, full_diagnosis, recommendation)
    logger.info("Direct analysis — engine %d — complete", engine_id)

    # Format the output
    report = (
        f"=== SEN Deep Analysis — Engine {engine_id} ===\n\n"
        f"PREDICTED RUL: {round(rul, 2)} cycles\n"
        f"SEVERITY: {severity}\n"
        f"DEGRADATION RATIO: {ratio}x fleet average ({deg_severity})\n"
        f"CYCLES TO CRITICAL: {cycles_to_critical}\n"
        f"URGENCY: {urgency}\n\n"
        f"FLEET COMPARISON:\n"
        f"  Outlier sensors: {', '.join(outlier_sensors) if outlier_sensors else 'None'}\n\n"
        f"TOP DECLINING SENSORS:\n"
    )
    for sensor in top_declining:
        slope = trend_result["slopes"][sensor]
        label = sensorLabels.get(sensor, sensor)
        report += f"  {sensor} ({label}): slope = {slope}\n"
    report += (
        f"\nMAINTENANCE RECOMMENDATION:\n"
        f"{recommendation}\n\n"
        f"PDF Report: {pdf_path.name}\n"
    )
    return report


# Sensor labels for formatted output
sensorLabels = {
    "s2": "Total temp at LPC outlet",
    "s3": "Total temp at HPC outlet",
    "s4": "Total temp at LPT outlet",
    "s7": "Total pressure at HPC outlet",
    "s8": "Physical fan speed",
    "s9": "Physical core speed",
    "s11": "Static pressure at HPC outlet",
    "s12": "Ratio of fuel flow to Ps30",
    "s13": "Corrected fan speed",
    "s14": "Corrected core speed",
    "s15": "Bypass ratio",
    "s17": "Bleed enthalpy",
    "s20": "HPT coolant bleed",
    "s21": "LPT coolant bleed",
}


# ── Sensor history endpoint ───────────────────────────────────────────────────

SENSOR_COLS = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]


class SensorReading(BaseModel):
    """One cycle's worth of normalized sensor values for a single engine."""
    cycle: int
    s2: float
    s3: float
    s4: float
    s7: float
    s8: float
    s9: float
    s11: float
    s12: float
    s13: float
    s14: float
    s15: float
    s17: float
    s20: float
    s21: float


@app.get("/engine/{engine_id}/sensors", response_model=list[SensorReading])
def engine_sensors(engine_id: int, last_n: int = 50) -> list[SensorReading]:
    """
    Return the last N cycles of normalized sensor readings for one engine.

    Args:
        engine_id: Target engine unit ID.
        last_n:    How many of the most recent cycles to return (default 50).
    """
    try:
        import pandas as pd

        path = _clean_csv_path()
        if not path.exists():
            raise HTTPException(status_code=503, detail="Clean dataset not found — run ingest first.")

        df  = pd.read_csv(path)
        ids = sorted(int(x) for x in df["unit_id"].unique())
        if engine_id not in ids:
            raise HTTPException(status_code=404, detail=f"Engine {engine_id} not found.")

        edf = (
            df[df["unit_id"] == engine_id]
            .sort_values("cycle")
            .tail(last_n)
            .reset_index(drop=True)
        )

        return [
            SensorReading(cycle=int(row["cycle"]), **{col: round(float(row[col]), 6) for col in SENSOR_COLS})
            for _, row in edf.iterrows()
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Sensor history failed for engine %d", engine_id)
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
        cfg = _load_config()
        model_name = cfg["llm"]["model"].replace("gemini/", "")
        response = client.models.generate_content(
            model=model_name,
            contents=full_prompt,
        )
        return ChatResponse(response=response.text.strip())
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=500, detail=str(exc))
