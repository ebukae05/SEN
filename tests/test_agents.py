"""Tests for the three CrewAI agents and the maintenance crew.

Covers:
    1. Shared helpers (load_config, get_llm, get_active_dataframe).
    2. Each agent's tool wrappers (predict, alert, diagnose, recommend, PDF).
    3. Agent construction (role/goal/tools wired correctly).
    4. End-to-end crew.kickoff() integration that calls the live Gemini API
       and verifies a PDF report is generated.

The full crew kickoff test is gated by RUN_LIVE_CREW=1 so the suite stays
fast and offline-friendly by default.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents import (  # noqa: E402
    get_active_dataframe, get_llm, load_config,
)
from agents.advisor import (  # noqa: E402
    build_advisor_agent, create_pdf_report, estimate_time_to_critical,
    generate_recommendation,
)
from agents.diagnostician import (  # noqa: E402
    build_diagnostic_agent, compare_engine_to_fleet,
    engine_degradation_rate, engine_sensor_trends,
)
from agents.monitor import (  # noqa: E402
    build_monitor_agent, check_engine_alert, predict_engine_rul,
)
from crews.maintenance_crew import (  # noqa: E402
    build_maintenance_crew, run_pipeline,
)


@pytest.fixture(scope="module")
def config() -> dict:
    """Loaded project config."""
    return load_config()


@pytest.fixture(scope="module")
def fd001_df(config: dict) -> pd.DataFrame:
    """Active processed dataframe (FD001)."""
    return get_active_dataframe()


@pytest.fixture(scope="module")
def sample_engine_id(fd001_df: pd.DataFrame) -> int:
    """A real engine_id present in the dataset."""
    return int(fd001_df["unit_id"].min())


def _invoke(tool_callable, *args, **kwargs):
    """Helper to call a CrewAI @tool-wrapped function with positional args.

    Supports either the underlying `.func` or the `.run` attribute exposed by
    crewai.tools.tool depending on version.
    """
    inner = getattr(tool_callable, "func", None)
    if inner is not None:
        return inner(*args, **kwargs)
    return tool_callable.run(*args, **kwargs)


class TestSharedHelpers:
    """load_config / get_llm / get_active_dataframe."""

    def test_load_config_has_llm_section(self, config: dict) -> None:
        assert "llm" in config
        assert config["llm"]["provider"] == "google"
        assert config["llm"]["model"] == "gemini-2.5-flash"

    def test_get_active_dataframe_returns_processed(
        self, fd001_df: pd.DataFrame
    ) -> None:
        assert not fd001_df.empty
        assert "unit_id" in fd001_df.columns
        assert "RUL" in fd001_df.columns

    def test_get_llm_constructs_client(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        llm = get_llm()
        assert "gemini" in str(llm.model).lower()


class TestMonitorTools:
    """MonitorAgent tool wrappers."""

    def test_predict_engine_rul_returns_float(
        self, sample_engine_id: int
    ) -> None:
        rul = _invoke(predict_engine_rul, sample_engine_id)
        assert isinstance(rul, float)
        assert 0.0 <= rul <= 200.0

    def test_check_engine_alert_healthy(self, sample_engine_id: int) -> None:
        payload = _invoke(check_engine_alert, sample_engine_id, 120.0)
        parsed = json.loads(payload)
        assert parsed["alert"] is False
        assert parsed["severity"] == "healthy"
        assert parsed["engine_id"] == sample_engine_id

    def test_check_engine_alert_critical(self, sample_engine_id: int) -> None:
        payload = _invoke(check_engine_alert, sample_engine_id, 10.0)
        parsed = json.loads(payload)
        assert parsed["alert"] is True
        assert parsed["severity"] in {"critical", "watch"}


class TestDiagnosticTools:
    """DiagnosticAgent tool wrappers."""

    def test_compare_engine_to_fleet_returns_json(
        self, sample_engine_id: int
    ) -> None:
        payload = _invoke(compare_engine_to_fleet, sample_engine_id)
        parsed = json.loads(payload)
        assert isinstance(parsed, dict)
        assert len(parsed) > 0

    def test_engine_sensor_trends_returns_ranked_json(
        self, sample_engine_id: int
    ) -> None:
        payload = _invoke(engine_sensor_trends, sample_engine_id)
        parsed = json.loads(payload)
        assert isinstance(parsed, dict)
        slopes = list(parsed.values())
        abs_slopes = [abs(s) for s in slopes]
        assert abs_slopes == sorted(abs_slopes, reverse=True)

    def test_engine_degradation_rate_returns_float(
        self, sample_engine_id: int
    ) -> None:
        rate = _invoke(engine_degradation_rate, sample_engine_id)
        assert isinstance(rate, float)
        assert rate >= 0.0


class TestAdvisorTools:
    """MaintenanceAdvisorAgent tool wrappers."""

    def test_estimate_time_to_critical_returns_float(self) -> None:
        cycles = _invoke(estimate_time_to_critical, 80.0, 1.5)
        assert isinstance(cycles, float)
        assert cycles >= 0.0

    def test_generate_recommendation_live_gemini(
        self, sample_engine_id: int
    ) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        diagnosis = {
            "engine_id": sample_engine_id,
            "rul": 25.0,
            "severity": "critical",
            "top_degrading_sensors": ["s11", "s4", "s12"],
            "degradation_rate": 1.8,
            "root_cause": "HPC efficiency loss",
        }
        text = _invoke(generate_recommendation, json.dumps(diagnosis))
        assert isinstance(text, str)
        assert len(text) > 20

    def test_create_pdf_report_writes_file(
        self, sample_engine_id: int, config: dict
    ) -> None:
        diagnosis = {
            "engine_id": sample_engine_id,
            "rul": 25.0,
            "severity": "critical",
            "top_degrading_sensors": ["s11", "s4", "s12"],
            "degradation_rate": 1.8,
            "root_cause": "HPC efficiency loss",
        }
        path = _invoke(
            create_pdf_report,
            sample_engine_id,
            json.dumps(diagnosis),
            "Schedule inspection within 5 cycles.",
        )
        pdf_path = Path(path)
        assert pdf_path.exists()
        assert pdf_path.suffix == ".pdf"
        assert pdf_path.stat().st_size > 0


class TestAgentConstruction:
    """Each builder wires role/goal/tools correctly."""

    def test_monitor_agent(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        agent = build_monitor_agent()
        assert "Monitor" in agent.role
        assert len(agent.tools) == 2
        assert agent.allow_delegation is False

    def test_diagnostic_agent(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        agent = build_diagnostic_agent()
        assert "Diagnostics" in agent.role
        assert len(agent.tools) == 3
        assert agent.allow_delegation is False

    def test_advisor_agent(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        agent = build_advisor_agent()
        assert "Advisor" in agent.role
        assert len(agent.tools) == 3
        assert agent.allow_delegation is False


class TestCrewConstruction:
    """Maintenance crew wiring."""

    def test_build_maintenance_crew(self) -> None:
        if not os.environ.get("GOOGLE_API_KEY"):
            pytest.skip("GOOGLE_API_KEY not set")
        crew = build_maintenance_crew()
        assert len(crew.agents) == 3
        assert len(crew.tasks) == 3
        assert crew.tasks[1].context == [crew.tasks[0]]
        assert crew.tasks[2].context == [crew.tasks[1]]

    def test_run_pipeline_rejects_bad_engine_id(self) -> None:
        with pytest.raises(ValueError):
            run_pipeline(0)
        with pytest.raises(ValueError):
            run_pipeline(-3)


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_CREW") != "1",
    reason="set RUN_LIVE_CREW=1 to run the live end-to-end crew kickoff",
)
class TestCrewKickoff:
    """Full sequential pipeline against the live Gemini API."""

    def test_kickoff_engine_one_produces_pdf(
        self, sample_engine_id: int
    ) -> None:
        reports_dir = REPO_ROOT / "outputs" / "reports"
        before = set(reports_dir.glob("*.pdf")) if reports_dir.exists() else set()
        result = run_pipeline(sample_engine_id)
        assert isinstance(result, str)
        assert len(result) > 0
        after = set(reports_dir.glob("*.pdf"))
        new_pdfs = after - before
        assert new_pdfs, "No new PDF report was generated by the crew"
