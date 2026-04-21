"""
crews/maintenance_crew.py — Sequential 4-agent maintenance pipeline crew.

Wires DataEngineerAgent → MonitorAgent → DiagnosticAgent → MaintenanceAdvisorAgent
into a CrewAI sequential pipeline. Each agent receives the prior agent's output
as context before executing its tasks.

Supports all CMAPSS datasets (FD001–FD004) via the dataset_id parameter.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from crewai import Crew, Process, Task

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from agents.advisor import build_advisor_agent
from agents.data_engineer import build_data_engineer_agent
from agents.diagnostician import build_diagnostician_agent
from agents.monitor import build_monitor_agent

logger = logging.getLogger(__name__)


def _build_tasks(
    data_engineer: Any,
    monitor: Any,
    diagnostician: Any,
    advisor: Any,
) -> list[Task]:
    """
    Define all four pipeline tasks with agent assignments and context chaining.

    Parameters
    ----------
    data_engineer, monitor, diagnostician, advisor : Agent
        The four CrewAI agents to assign to each task.

    Returns
    -------
    list[Task]
        Ordered list of tasks for the sequential crew.
    """
    ingest_task = Task(
        description=(
            "Load and clean the CMAPSS {dataset_id} training dataset by calling the ingest tool "
            "with dataset_name='train' and dataset_id='{dataset_id}'. "
            "Then visualize sensor trends for engine {engine_id} using dataset_id='{dataset_id}'."
        ),
        expected_output=(
            "A data quality summary including: number of engines, total rows, sensors removed, "
            "RUL range, and confirmation the clean CSV was saved."
        ),
        agent=data_engineer,
    )

    monitor_task = Task(
        description=(
            "Predict the RUL for engine {engine_id} in the {dataset_id} dataset using the CNN-LSTM model. "
            "Pass dataset_id='{dataset_id}' to the prediction tool. "
            "Then check whether the predicted RUL is below the alert threshold. "
            "Report the exact predicted RUL value and alert status."
        ),
        expected_output=(
            "Predicted RUL in cycles for engine {engine_id} ({dataset_id}) and alert severity "
            "(NORMAL / CAUTION / WARNING / CRITICAL)."
        ),
        agent=monitor,
        context=[ingest_task],
    )

    diagnose_task = Task(
        description=(
            "Run a full diagnostic analysis on engine {engine_id} in the {dataset_id} dataset: "
            "1) Compare it to the fleet average (pass dataset_id='{dataset_id}'). "
            "2) Identify the top 3 fastest-declining sensors. "
            "3) Calculate its degradation rate ratio vs the fleet. "
            "Summarise severity and root cause."
        ),
        expected_output=(
            "Diagnostic summary for engine {engine_id} ({dataset_id}): fleet deviation, "
            "top declining sensors, degradation ratio, and overall severity rating."
        ),
        agent=diagnostician,
        context=[monitor_task],
    )

    advise_task = Task(
        description=(
            "Using the RUL, degradation ratio, severity, top declining sensors, and urgency "
            "from the diagnostic and monitoring results for engine {engine_id} ({dataset_id}): "
            "1) Calculate the criticality timeline. "
            "2) Generate a maintenance recommendation and PDF report "
            "(pass dataset_id='{dataset_id}' to the report tool). "
            "Provide the urgency level and the path to the saved PDF."
        ),
        expected_output=(
            "Maintenance recommendation for engine {engine_id} ({dataset_id}), urgency level, "
            "and the file path to the generated PDF report."
        ),
        agent=advisor,
        context=[diagnose_task, monitor_task],
    )

    return [ingest_task, monitor_task, diagnose_task, advise_task]


def build_crew() -> Crew:
    """
    Assemble and return the full 4-agent sequential maintenance crew.

    Returns
    -------
    Crew
        CrewAI Crew ready for kickoff.
    """
    data_engineer = build_data_engineer_agent()
    monitor = build_monitor_agent()
    diagnostician = build_diagnostician_agent()
    advisor = build_advisor_agent()
    tasks = _build_tasks(data_engineer, monitor, diagnostician, advisor)
    return Crew(
        agents=[data_engineer, monitor, diagnostician, advisor],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        max_rpm=4,
    )


def run_pipeline(engine_id: int = 1, dataset_id: str = "FD001") -> str:
    """
    Run the full maintenance pipeline for a given engine and dataset.

    Parameters
    ----------
    engine_id : int
        The engine unit_id to analyse (default 1).
    dataset_id : str
        CMAPSS dataset to use ('FD001'–'FD004', default 'FD001').

    Returns
    -------
    str
        Final crew output — the advisor's maintenance recommendation and report path.
    """
    logger.info("Starting SEN maintenance pipeline for engine %d (%s)", engine_id, dataset_id)
    crew = build_crew()
    result = crew.kickoff(inputs={"engine_id": str(engine_id), "dataset_id": dataset_id})
    logger.info("Pipeline complete for engine %d (%s)", engine_id, dataset_id)
    return str(result)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    engine = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    dataset = sys.argv[2] if len(sys.argv) > 2 else "FD001"
    print(run_pipeline(engine, dataset))
