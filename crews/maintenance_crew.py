"""Sequential CrewAI Crew wiring the three agents into the SEN pipeline.

Pipeline:
    MonitorAgent (predict RUL, check alert)
        -> DiagnosticAgent (root cause, sensor trends, degradation rate)
            -> MaintenanceAdvisorAgent (recommendation + PDF report)
"""

from __future__ import annotations

import logging

from crewai import Crew, Process, Task

from agents.advisor import build_advisor_agent
from agents.diagnostician import build_diagnostic_agent
from agents.monitor import build_monitor_agent

logger = logging.getLogger(__name__)

MONITOR_TASK_DESCRIPTION = (
    "Predict the latest Remaining Useful Life (RUL) for engine {engine_id} "
    "using `predict_engine_rul`. Then call `check_engine_alert` with that "
    "RUL to determine alert status. Report the predicted RUL, the alert "
    "JSON, and a one-sentence summary describing whether the engine "
    "requires escalation."
)
MONITOR_EXPECTED_OUTPUT = (
    "A short structured report containing: engine_id, predicted_rul, "
    "severity (healthy/watch/critical), alert flag (true/false), and a "
    "one-sentence summary."
)

DIAGNOSTIC_TASK_DESCRIPTION = (
    "Using the MonitorAgent's report on engine {engine_id}, investigate the "
    "root cause. Call `compare_engine_to_fleet`, `engine_sensor_trends`, and "
    "`engine_degradation_rate`. Identify the three sensors degrading "
    "fastest. Conclude with a diagnosis JSON containing: engine_id, rul, "
    "severity, top_degrading_sensors (list of 3), degradation_rate, and a "
    "root_cause string."
)
DIAGNOSTIC_EXPECTED_OUTPUT = (
    "A diagnosis JSON object with keys: engine_id, rul, severity, "
    "top_degrading_sensors, degradation_rate, root_cause."
)

ADVISOR_TASK_DESCRIPTION = (
    "Using the DiagnosticAgent's diagnosis for engine {engine_id}, call "
    "`estimate_time_to_critical` using its rul and degradation_rate values. "
    "Then call `generate_recommendation` with the full diagnosis JSON to "
    "produce a maintenance recommendation. Finally call `create_pdf_report` "
    "with the engine_id, diagnosis JSON, and recommendation to write the "
    "formal report. Return the recommendation text and the PDF path."
)
ADVISOR_EXPECTED_OUTPUT = (
    "A final report containing: the recommendation text and the absolute "
    "path to the generated PDF report."
)


def build_maintenance_crew() -> Crew:
    """Construct the three-agent sequential Crew for one engine analysis."""
    monitor = build_monitor_agent()
    diagnostician = build_diagnostic_agent()
    advisor = build_advisor_agent()
    monitor_task = Task(
        description=MONITOR_TASK_DESCRIPTION,
        expected_output=MONITOR_EXPECTED_OUTPUT,
        agent=monitor,
    )
    diagnose_task = Task(
        description=DIAGNOSTIC_TASK_DESCRIPTION,
        expected_output=DIAGNOSTIC_EXPECTED_OUTPUT,
        agent=diagnostician,
        context=[monitor_task],
    )
    advise_task = Task(
        description=ADVISOR_TASK_DESCRIPTION,
        expected_output=ADVISOR_EXPECTED_OUTPUT,
        agent=advisor,
        context=[diagnose_task],
    )
    return Crew(
        agents=[monitor, diagnostician, advisor],
        tasks=[monitor_task, diagnose_task, advise_task],
        process=Process.sequential,
        verbose=True,
    )


def run_pipeline(engine_id: int) -> str:
    """Kick off the maintenance crew for one engine_id and return the final output."""
    if not isinstance(engine_id, int) or engine_id <= 0:
        raise ValueError(f"engine_id must be a positive int, got {engine_id!r}")
    crew = build_maintenance_crew()
    logger.info("Kicking off maintenance crew for engine %d", engine_id)
    result = crew.kickoff(inputs={"engine_id": engine_id})
    return str(result)
