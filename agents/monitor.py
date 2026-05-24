"""MonitorAgent — real-time RUL prediction and engine alerting."""

from __future__ import annotations

import json
from typing import Any

from crewai import Agent
from crewai.tools import tool

from agents import get_active_dataframe, get_llm
from tools.predict_tools import check_thresholds as _check_thresholds
from tools.predict_tools import predict_rul as _predict_rul
from tools.stream_tools import stream_sensors as _stream_sensors

MONITOR_ROLE = "Real-Time Engine Health Monitor"
MONITOR_GOAL = (
    "Stream sensor data through the CNN-LSTM model and flag engines "
    "approaching failure"
)
MONITOR_BACKSTORY = (
    "You are a flight-line engineer responsible for catching engine issues "
    "before they become incidents. You trust the CNN-LSTM model's RUL "
    "predictions, and you escalate aggressively when the predicted RUL drops "
    "below the configured alert threshold."
)


@tool("Predict latest RUL for an engine")
def predict_engine_rul(engine_id: int) -> float:
    """Run CNN-LSTM inference on the most recent sensor window for the engine.

    Use this to get the current Remaining Useful Life (in cycles).
    """
    df = get_active_dataframe()
    windows = list(_stream_sensors(df, engine_id))
    if not windows:
        raise ValueError(f"No sensor windows available for engine {engine_id}")
    return _predict_rul(windows[-1])


@tool("Check whether an engine should be alerted")
def check_engine_alert(engine_id: int, rul: float) -> str:
    """Compare an RUL value to the alert threshold; return JSON describing the alert.

    Returns a JSON string with engine_id, rul, threshold, severity, and alert.
    If the engine is healthy, severity is 'healthy' and alert is false.
    """
    alert: dict[str, Any] | None = _check_thresholds(engine_id, rul)
    if alert is None:
        return json.dumps({
            "engine_id": engine_id, "rul": rul, "alert": False, "severity": "healthy",
        })
    return json.dumps(alert)


def build_monitor_agent() -> Agent:
    """Construct the MonitorAgent with its tools and Gemini 2.5 Flash LLM."""
    return Agent(
        role=MONITOR_ROLE,
        goal=MONITOR_GOAL,
        backstory=MONITOR_BACKSTORY,
        tools=[predict_engine_rul, check_engine_alert],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
