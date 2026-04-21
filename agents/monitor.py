"""
agents/monitor.py — MonitorAgent definition and its CrewAI tools.

Loads the clean CSV produced by DataEngineerAgent, streams sensor windows,
runs CNN-LSTM inference, and flags engines approaching failure.
Supports all CMAPSS datasets (FD001–FD004).
"""

import logging
import os
import sys
from pathlib import Path

import yaml
from crewai import Agent, LLM
from crewai.tools import tool
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _get_llm() -> LLM:
    """Instantiate the Gemini LLM from config."""
    cfg = _load_config()["llm"]
    return LLM(model=cfg["model"], api_key=os.getenv("GOOGLE_API_KEY"), temperature=cfg["temperature"])


@tool("Predict Engine RUL")
def predict_engine_rul_tool(engine_id: str, dataset_id: str = "FD001") -> str:
    """
    Load the most recent sensor window for a specific engine from the clean CSV,
    run CNN-LSTM inference, and return the predicted Remaining Useful Life in cycles.
    Input: engine_id as a string integer (e.g. '1'), dataset_id as 'FD001'–'FD004'.
    """
    import numpy as np
    import pandas as pd
    from tools.predict_tools import predict_rul
    cfg = _load_config()
    data_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"
    df = pd.read_csv(data_path)
    seq_len = cfg["model"]["sequence_length"]
    ds_cfg = cfg["data"]["datasets"][dataset_id]
    sensor_cols = ds_cfg["keep_sensors"]
    engine_df = df[df["unit_id"] == int(engine_id)].sort_values("cycle")
    if len(engine_df) < seq_len:
        return f"Engine {engine_id} has insufficient data ({len(engine_df)} cycles, need {seq_len})."
    window = engine_df[sensor_cols].values[-seq_len:].astype(np.float32)
    rul = predict_rul(window, dataset_id=dataset_id)
    return f"Engine {engine_id} ({dataset_id}): predicted RUL = {rul:.1f} cycles."


@tool("Check Engine Alert Threshold")
def check_engine_alert_tool(engine_id: str, rul: str) -> str:
    """
    Check whether a predicted RUL falls below the configured alert threshold.
    Input: engine_id as string integer, rul as string float (e.g. '45.3').
    Returns alert status and severity level.
    """
    from tools.predict_tools import check_thresholds
    result = check_thresholds(engine_id=int(engine_id), rul=float(rul))
    status = "ALERT" if result["alert"] else "OK"
    return (
        f"Engine {engine_id}: {status} | Severity={result['severity']} | "
        f"RUL={result['rul']} cycles | Threshold={result['threshold']} cycles."
    )


def build_monitor_agent() -> Agent:
    """
    Instantiate and return the MonitorAgent.

    Returns
    -------
    Agent
        CrewAI Agent configured with prediction and threshold tools and Gemini LLM.
    """
    return Agent(
        role="Real-Time Engine Health Monitor",
        goal="Stream sensor data, run RUL predictions, and flag engines approaching failure",
        backstory=(
            "You are an automated health monitoring system embedded in an aerospace MRO "
            "facility. You continuously watch engine telemetry, run predictive models, "
            "and immediately escalate when an engine's remaining life drops below safe limits."
        ),
        tools=[predict_engine_rul_tool, check_engine_alert_tool],
        llm=_get_llm(),
        verbose=True,
    )
