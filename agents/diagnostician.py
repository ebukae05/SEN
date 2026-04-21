"""
agents/diagnostician.py — DiagnosticAgent definition and its CrewAI tools.

Investigates flagged engines using fleet comparison, sensor trend analysis,
and degradation rate quantification.
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


@tool("Compare Engine to Fleet Average")
def fleet_comparison_tool(engine_id: str, dataset_id: str = "FD001") -> str:
    """
    Compare a specific engine's mean sensor readings against the full fleet average.
    Returns sensors that deviate significantly from fleet norms.
    Input: engine_id as a string integer (e.g. '1'), dataset_id as 'FD001'–'FD004'.
    """
    import pandas as pd
    from tools.diagnostic_tools import compare_to_fleet
    cfg = _load_config()
    data_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"
    df = pd.read_csv(data_path)
    result = compare_to_fleet(df, engine_id=int(engine_id), dataset_id=dataset_id)
    return (
        f"Engine {engine_id} vs fleet ({dataset_id}): {len(result['outlier_sensors'])} sensors deviate >0.1. "
        f"Outliers: {result['outlier_sensors']}."
    )


@tool("Analyse Engine Sensor Trends")
def sensor_trend_tool(engine_id: str, dataset_id: str = "FD001") -> str:
    """
    Identify which sensors are declining fastest for a specific engine using linear regression.
    Returns top 3 fastest-declining sensors and their slopes.
    Input: engine_id as a string integer (e.g. '1'), dataset_id as 'FD001'–'FD004'.
    """
    import pandas as pd
    from tools.diagnostic_tools import sensor_trends
    cfg = _load_config()
    data_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"
    df = pd.read_csv(data_path)
    result = sensor_trends(df, engine_id=int(engine_id), dataset_id=dataset_id)
    top3 = result["ranked_declining"][:3]
    slopes = {s: result["slopes"][s] for s in top3}
    return f"Engine {engine_id} ({dataset_id}) top declining sensors: {slopes}."


@tool("Calculate Engine Degradation Rate")
def degradation_rate_tool(engine_id: str, dataset_id: str = "FD001") -> str:
    """
    Calculate the engine's degradation rate compared to the fleet average using linear regression.
    Returns the rate ratio and severity label (NORMAL / MODERATE / HIGH).
    Input: engine_id as a string integer (e.g. '1'), dataset_id as 'FD001'–'FD004'.
    """
    import pandas as pd
    from tools.diagnostic_tools import degradation_rate
    cfg = _load_config()
    data_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"
    df = pd.read_csv(data_path)
    result = degradation_rate(df, engine_id=int(engine_id), dataset_id=dataset_id)
    return (
        f"Engine {engine_id} degradation ({dataset_id}): rate={result['engine_rate']:.6f}, "
        f"fleet={result['fleet_rate']:.6f}, ratio={result['ratio']:.3f}, "
        f"severity={result['severity']}."
    )


def build_diagnostician_agent() -> Agent:
    """
    Instantiate and return the DiagnosticAgent.

    Returns
    -------
    Agent
        CrewAI Agent configured with diagnostic tools and Gemini LLM.
    """
    return Agent(
        role="Engine Diagnostics Specialist",
        goal="Investigate flagged engines to determine root cause of degradation",
        backstory=(
            "You are a senior propulsion engineer who has diagnosed thousands of "
            "turbofan engine anomalies. You use sensor data patterns, fleet baselines, "
            "and degradation models to pinpoint failing components and assess severity."
        ),
        tools=[fleet_comparison_tool, sensor_trend_tool, degradation_rate_tool],
        llm=_get_llm(),
        verbose=True,
    )
