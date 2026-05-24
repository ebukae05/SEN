"""MaintenanceAdvisorAgent — recommendations and formal PDF reports."""

from __future__ import annotations

import json
from typing import Any

from crewai import Agent
from crewai.tools import tool

from agents import get_llm
from tools.advisor_tools import generate_report as _generate_report
from tools.advisor_tools import recommend_action as _recommend_action
from tools.advisor_tools import time_to_critical as _time_to_critical

ADVISOR_ROLE = "Maintenance Planning Advisor"
ADVISOR_GOAL = (
    "Generate actionable maintenance recommendations and formal PDF reports"
)
ADVISOR_BACKSTORY = (
    "You are a maintenance planning lead with 20 years of experience "
    "scheduling MRO actions. You translate technical diagnoses into concrete "
    "shop-floor recommendations and produce formal PDF reports that line "
    "managers can act on the same shift."
)


@tool("Estimate cycles until critical")
def estimate_time_to_critical(rul: float, degradation_rate: float) -> float:
    """Return cycles before the engine reaches the critical RUL threshold."""
    return _time_to_critical(rul, degradation_rate)


@tool("Generate maintenance recommendation text")
def generate_recommendation(diagnosis_json: str) -> str:
    """Call Gemini to generate a maintenance recommendation from a diagnosis.

    Pass the full diagnosis as a JSON string (engine_id, rul, severity, etc.).
    """
    diagnosis: dict[str, Any] = json.loads(diagnosis_json)
    return _recommend_action(diagnosis)


@tool("Create a maintenance PDF report")
def create_pdf_report(
    engine_id: int, diagnosis_json: str, recommendation: str
) -> str:
    """Write a PDF report to outputs/reports/ and return its file path."""
    diagnosis: dict[str, Any] = json.loads(diagnosis_json)
    path = _generate_report(engine_id, diagnosis, recommendation)
    return str(path)


def build_advisor_agent() -> Agent:
    """Construct the MaintenanceAdvisorAgent with its tools and LLM."""
    return Agent(
        role=ADVISOR_ROLE,
        goal=ADVISOR_GOAL,
        backstory=ADVISOR_BACKSTORY,
        tools=[
            estimate_time_to_critical,
            generate_recommendation,
            create_pdf_report,
        ],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
