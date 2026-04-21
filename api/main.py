"""
api/main.py — FastAPI REST layer for the SEN maintenance pipeline.

Endpoints:
    GET  /health                  — Liveness check.
    GET  /datasets                — List available CMAPSS datasets and metadata.
    GET  /engines                 — List all engine IDs in the processed dataset.
    GET  /engine/{id}/status      — RUL prediction + alert status for one engine.
    GET  /engine/{id}/sensors     — Normalized sensor history for one engine.
    POST /analyze                 — Run direct deep analysis for one engine.
    GET  /fleet                   — Health snapshot for all engines in a dataset.
    POST /api/chat                — Proxy chat messages to Gemini.

All data endpoints accept an optional `dataset` query parameter (FD001–FD004).

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
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

_PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
sys.path.insert(0, str(_PROJECT_ROOT))

logger = logging.getLogger(__name__)
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

VALID_DATASETS = ("FD001", "FD002", "FD003", "FD004")


def _load_config() -> dict:
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


app = FastAPI(
    title="SEN — Sensor Engine Network",
    description="Real-time turbofan engine health monitoring via 4-agent AI pipeline.",
    version="2.0.0",
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
    dataset: str = "FD001"


class AnalyzeResponse(BaseModel):
    engine_id: int
    dataset: str
    result: str


class EngineStatus(BaseModel):
    engine_id: int
    predicted_rul: float
    severity: str
    alert: bool


class HealthResponse(BaseModel):
    status: str


class DatasetInfo(BaseModel):
    dataset_id: str
    engines: int
    fault_modes: int
    operating_conditions: int
    n_features: int
    available: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_dataset(dataset: str) -> str:
    """Validate and return dataset ID, raising 400 if invalid."""
    if dataset not in VALID_DATASETS:
        raise HTTPException(status_code=400, detail=f"Invalid dataset '{dataset}'. Must be one of {VALID_DATASETS}.")
    return dataset


def _clean_csv_path(dataset_id: str = "FD001") -> Path:
    cfg = _load_config()
    return _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"


def _get_engine_ids(dataset_id: str = "FD001") -> list[int]:
    import pandas as pd
    path = _clean_csv_path(dataset_id)
    if not path.exists():
        raise FileNotFoundError(f"Clean dataset not found for {dataset_id} — run ingest first.")
    df = pd.read_csv(path)
    return sorted(int(x) for x in df["unit_id"].unique())


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check."""
    return HealthResponse(status="ok")


@app.get("/datasets", response_model=list[DatasetInfo])
def list_datasets() -> list[DatasetInfo]:
    """Return metadata for all CMAPSS datasets and whether their clean CSV is available."""
    cfg = _load_config()
    results = []
    for ds_id, ds_cfg in cfg["data"]["datasets"].items():
        csv_path = _clean_csv_path(ds_id)
        results.append(DatasetInfo(
            dataset_id=ds_id,
            engines=_engine_count(ds_id, ds_cfg),
            fault_modes=ds_cfg["fault_modes"],
            operating_conditions=ds_cfg["operating_conditions"],
            n_features=ds_cfg["n_features"],
            available=csv_path.exists(),
        ))
    return results


def _engine_count(ds_id: str, ds_cfg: dict) -> int:
    """Return engine count from clean CSV if available, else from known dataset sizes."""
    csv_path = _clean_csv_path(ds_id)
    if csv_path.exists():
        import pandas as pd
        return int(pd.read_csv(csv_path)["unit_id"].nunique())
    known = {"FD001": 100, "FD002": 260, "FD003": 100, "FD004": 249}
    return known.get(ds_id, 0)


@app.get("/engines", response_model=list[int])
def list_engines(dataset: str = Query("FD001", description="CMAPSS dataset ID")) -> list[int]:
    """Return all engine IDs available in the processed dataset."""
    dataset = _resolve_dataset(dataset)
    try:
        return _get_engine_ids(dataset)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/engine/{engine_id}/status", response_model=EngineStatus)
def engine_status(
    engine_id: int,
    dataset: str = Query("FD001", description="CMAPSS dataset ID"),
) -> EngineStatus:
    """Predict RUL and alert status for a single engine using the CNN-LSTM model."""
    dataset = _resolve_dataset(dataset)
    try:
        if engine_id not in _get_engine_ids(dataset):
            raise HTTPException(status_code=404, detail=f"Engine {engine_id} not found in {dataset}.")

        import pandas as pd
        from tools.stream_tools import stream_sensors
        from tools.predict_tools import predict_rul, check_thresholds

        cfg = _load_config()
        df = pd.read_csv(_clean_csv_path(dataset))
        windows = list(stream_sensors(df, engine_id=engine_id, window_size=cfg["model"]["sequence_length"], dataset_id=dataset))
        if not windows:
            raise HTTPException(status_code=422, detail=f"Engine {engine_id} has insufficient data.")

        rul = predict_rul(windows[-1], dataset_id=dataset)
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
        logger.exception("Status check failed for engine %d (%s)", engine_id, dataset)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """
    Run a direct deep analysis for the given engine.

    Bypasses CrewAI orchestration: runs all diagnostic tools directly,
    then makes a single Gemini call for the maintenance recommendation.
    Typically completes in 10-30 seconds instead of 2-3 minutes.
    """
    dataset = _resolve_dataset(request.dataset)
    try:
        result = _run_direct_analysis(request.engine_id, dataset)
        return AnalyzeResponse(engine_id=request.engine_id, dataset=dataset, result=result)
    except Exception as exc:
        logger.exception("Analysis failed for engine %d (%s)", request.engine_id, dataset)
        raise HTTPException(status_code=500, detail=str(exc))


def _run_direct_analysis(engine_id: int, dataset_id: str = "FD001") -> str:
    """
    Execute the full diagnostic pipeline without CrewAI — direct tool calls only.

    Parameters
    ----------
    engine_id : int
        The engine unit_id to analyse.
    dataset_id : str
        CMAPSS dataset to use.

    Returns
    -------
    str
        Formatted analysis report.
    """
    import pandas as pd
    from tools.stream_tools import stream_sensors
    from tools.predict_tools import predict_rul, check_thresholds
    from tools.diagnostic_tools import compare_to_fleet, sensor_trends, degradation_rate
    from tools.advisor_tools import time_to_critical, recommend_action, generate_report

    cfg = _load_config()
    csv_path = _clean_csv_path(dataset_id)
    if not csv_path.exists():
        raise FileNotFoundError(f"Clean dataset not found for {dataset_id} — run ingest first.")

    df = pd.read_csv(csv_path)
    if engine_id not in df["unit_id"].values:
        raise ValueError(f"Engine {engine_id} not found in {dataset_id}.")

    # Step 1: RUL prediction via CNN-LSTM at 75% lifecycle mark
    logger.info("Direct analysis — engine %d (%s) — predicting RUL", engine_id, dataset_id)
    windows = list(stream_sensors(df, engine_id=engine_id, window_size=cfg["model"]["sequence_length"], dataset_id=dataset_id))
    if not windows:
        raise ValueError(f"Engine {engine_id} has insufficient data for prediction.")
    window_idx = int(len(windows) * 0.75)
    rul = predict_rul(windows[window_idx], dataset_id=dataset_id)

    # Step 2: Threshold check
    alert_info = check_thresholds(engine_id, rul, threshold=cfg["monitor"]["rul_alert_threshold"])
    severity = alert_info["severity"]

    # Step 3: Fleet comparison
    logger.info("Direct analysis — engine %d (%s) — running diagnostics", engine_id, dataset_id)
    fleet_result = compare_to_fleet(df, engine_id, dataset_id=dataset_id)
    outlier_sensors = fleet_result["outlier_sensors"]

    # Step 4: Sensor trend analysis
    trend_result = sensor_trends(df, engine_id, dataset_id=dataset_id)
    top_declining = trend_result["ranked_declining"][:3]

    # Step 5: Degradation rate
    deg_result = degradation_rate(df, engine_id, dataset_id=dataset_id)
    ratio = deg_result["ratio"]
    deg_severity = deg_result["severity"]

    # Step 6: Time to critical
    crit_result = time_to_critical(rul, ratio)
    urgency = crit_result["urgency"]
    cycles_to_critical = crit_result["cycles_to_critical"]

    # Step 7: Single Gemini call for recommendation
    logger.info("Direct analysis — engine %d (%s) — requesting Gemini recommendation", engine_id, dataset_id)
    diagnosis = {
        "engine_id": engine_id,
        "dataset_id": dataset_id,
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
    pdf_path = generate_report(engine_id, full_diagnosis, recommendation, dataset_id=dataset_id)
    logger.info("Direct analysis — engine %d (%s) — complete", engine_id, dataset_id)

    # Format the output
    ds_cfg = cfg["data"]["datasets"][dataset_id]
    report = (
        f"=== SEN Deep Analysis — Engine {engine_id} ({dataset_id}) ===\n\n"
        f"DATASET: {dataset_id} ({ds_cfg['fault_modes']} fault mode(s), "
        f"{ds_cfg['operating_conditions']} operating condition(s))\n"
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
        label = SENSOR_LABELS.get(sensor, sensor)
        report += f"  {sensor} ({label}): slope = {slope}\n"
    report += (
        f"\nMAINTENANCE RECOMMENDATION:\n"
        f"{recommendation}\n\n"
        f"PDF Report: {pdf_path.name}\n"
    )
    return report


# Sensor labels for formatted output
SENSOR_LABELS = {
    "s2": "Total temp at LPC outlet",
    "s3": "Total temp at HPC outlet",
    "s4": "Total temp at LPT outlet",
    "s6": "Total pressure at fan inlet",
    "s7": "Total pressure at HPC outlet",
    "s8": "Physical fan speed",
    "s9": "Physical core speed",
    "s10": "Total pressure in bypass duct",
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

class SensorReading(BaseModel):
    """One cycle's worth of normalized sensor values for a single engine."""
    cycle: int
    sensors: dict[str, float]


@app.get("/engine/{engine_id}/sensors", response_model=list[SensorReading])
def engine_sensors(
    engine_id: int,
    last_n: int = 50,
    dataset: str = Query("FD001", description="CMAPSS dataset ID"),
) -> list[SensorReading]:
    """
    Return the last N cycles of normalized sensor readings for one engine.

    Args:
        engine_id: Target engine unit ID.
        last_n:    How many of the most recent cycles to return (default 50).
        dataset:   CMAPSS dataset ID (FD001–FD004).
    """
    dataset = _resolve_dataset(dataset)
    try:
        import pandas as pd

        path = _clean_csv_path(dataset)
        if not path.exists():
            raise HTTPException(status_code=503, detail=f"Clean dataset not found for {dataset} — run ingest first.")

        cfg = _load_config()
        ds_cfg = cfg["data"]["datasets"][dataset]
        sensor_cols = ds_cfg["keep_sensors"]

        df = pd.read_csv(path)
        ids = sorted(int(x) for x in df["unit_id"].unique())
        if engine_id not in ids:
            raise HTTPException(status_code=404, detail=f"Engine {engine_id} not found in {dataset}.")

        edf = (
            df[df["unit_id"] == engine_id]
            .sort_values("cycle")
            .tail(last_n)
            .reset_index(drop=True)
        )

        return [
            SensorReading(
                cycle=int(row["cycle"]),
                sensors={col: round(float(row[col]), 6) for col in sensor_cols if col in edf.columns},
            )
            for _, row in edf.iterrows()
        ]
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Sensor history failed for engine %d (%s)", engine_id, dataset)
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
def fleet_snapshot(
    dataset: str = Query("FD001", description="CMAPSS dataset ID"),
) -> list[EngineSnapshot]:
    """
    Return a health snapshot for every engine using ground-truth RUL at the 75%
    lifecycle mark — fast, no CNN-LSTM inference required.
    """
    dataset = _resolve_dataset(dataset)
    try:
        import pandas as pd
        cfg        = _load_config()
        threshold  = cfg["monitor"]["rul_alert_threshold"]
        csv_path   = _clean_csv_path(dataset)
        if not csv_path.exists():
            raise HTTPException(status_code=503, detail=f"Clean dataset not found for {dataset} — run ingest first.")

        df         = pd.read_csv(csv_path)
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
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Fleet snapshot failed (%s)", dataset)
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
