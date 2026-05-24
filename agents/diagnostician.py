"""DiagnosticAgent — root-cause analysis for flagged engines."""

from __future__ import annotations

import json
from typing import Any

from crewai import Agent
from crewai.tools import tool

from agents import get_active_dataframe, get_llm
from tools.diagnostic_tools import compare_to_fleet as _compare_to_fleet
from tools.diagnostic_tools import degradation_rate as _degradation_rate
from tools.diagnostic_tools import sensor_trends as _sensor_trends

DIAGNOSTIC_ROLE = "Engine Diagnostics Specialist"
DIAGNOSTIC_GOAL = (
    "Investigate flagged engines to determine root cause and severity of "
    "degradation"
)
DIAGNOSTIC_BACKSTORY = (
    "You are a former HPC test cell engineer who specializes in identifying "
    "root causes of turbofan degradation. You compare engine telemetry to "
    "fleet baselines, watch which sensors decline fastest, and quantify how "
    "abnormal the engine's degradation rate is."
)


@tool("Compare engine sensors to fleet")
def compare_engine_to_fleet(engine_id: int) -> str:
    """Return per-sensor comparison of one engine's means to fleet means as JSON."""
    df = get_active_dataframe()
    comparison: dict[str, Any] = _compare_to_fleet(df, engine_id)
    return json.dumps(comparison)


@tool("Rank engine sensors by rate of decline")
def engine_sensor_trends(engine_id: int) -> str:
    """Return engine sensors ranked by |slope| descending as JSON.

    Use this to identify which sensors are degrading fastest.
    """
    df = get_active_dataframe()
    trends: dict[str, float] = _sensor_trends(df, engine_id)
    return json.dumps(trends)


@tool("Compute engine degradation rate")
def engine_degradation_rate(engine_id: int) -> float:
    """Return the unit-less degradation ratio (1.0 = normal, >1.0 = accelerated)."""
    df = get_active_dataframe()
    return _degradation_rate(df, engine_id)


def build_diagnostic_agent() -> Agent:
    """Construct the DiagnosticAgent with its tools and Gemini 2.5 Flash LLM."""
    return Agent(
        role=DIAGNOSTIC_ROLE,
        goal=DIAGNOSTIC_GOAL,
        backstory=DIAGNOSTIC_BACKSTORY,
        tools=[
            compare_engine_to_fleet,
            engine_sensor_trends,
            engine_degradation_rate,
        ],
        llm=get_llm(),
        verbose=True,
        allow_delegation=False,
    )
