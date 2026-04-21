"""
agents/advisor.py — MaintenanceAdvisorAgent definition and its CrewAI tools.

Estimates time to critical failure, generates Gemini-powered recommendations,
and produces formal PDF maintenance reports.
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


@tool("Estimate Time to Critical Failure")
def criticality_tool(rul: str, degradation_ratio: str) -> str:
    """
    Estimate how many cycles remain before the engine reaches a critical RUL threshold.
    Input: rul as string float (predicted RUL in cycles), degradation_ratio as string float
    (engine degradation rate ratio vs fleet, from the degradation rate tool).
    """
    from tools.advisor_tools import time_to_critical
    result = time_to_critical(rul=float(rul), degradation_rate=float(degradation_ratio))
    return (
        f"Adjusted RUL: {result['adjusted_rul']} cycles. "
        f"Cycles to critical threshold: {result['cycles_to_critical']}. "
        f"Urgency: {result['urgency']}."
    )


@tool("Generate Maintenance Recommendation and PDF Report")
def maintenance_report_tool(
    engine_id: str,
    rul: str,
    severity: str,
    degradation_ratio: str,
    top_declining_sensors: str,
    urgency: str,
    dataset_id: str = "FD001",
) -> str:
    """
    Generate a Gemini-powered maintenance recommendation and save a PDF report.
    Inputs: engine_id (string int), rul (string float), severity (NORMAL/MODERATE/HIGH),
    degradation_ratio (string float), top_declining_sensors (comma-separated sensor names),
    urgency (IMMEDIATE/SOON/SCHEDULED), dataset_id ('FD001'–'FD004').
    """
    from tools.advisor_tools import generate_report, recommend_action
    diagnosis = {
        "engine_id":         int(engine_id),
        "dataset_id":        dataset_id,
        "rul":               float(rul),
        "severity":          severity,
        "ratio":             float(degradation_ratio),
        "ranked_declining":  [s.strip() for s in top_declining_sensors.split(",")],
        "urgency":           urgency,
    }
    recommendation = recommend_action(diagnosis)
    report_path = generate_report(
        engine_id=int(engine_id),
        diagnosis=diagnosis,
        recommendation=recommendation,
        dataset_id=dataset_id,
    )
    return (
        f"Recommendation for Engine {engine_id} ({dataset_id}): {recommendation[:200]}... "
        f"Full PDF report saved to: {report_path}"
    )


def build_advisor_agent() -> Agent:
    """
    Instantiate and return the MaintenanceAdvisorAgent.

    Returns
    -------
    Agent
        CrewAI Agent configured with advisory tools and Gemini LLM.
    """
    return Agent(
        role="Maintenance Planning Advisor",
        goal="Generate actionable maintenance recommendations and formal PDF reports",
        backstory=(
            "You are a maintenance planning expert who translates diagnostic findings "
            "into clear, prioritized action plans for MRO teams. Your recommendations "
            "balance operational safety with cost efficiency and scheduling constraints."
        ),
        tools=[criticality_tool, maintenance_report_tool],
        llm=_get_llm(),
        verbose=True,
    )
