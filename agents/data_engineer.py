"""
agents/data_engineer.py — DataEngineerAgent definition and its CrewAI tools.

Tools save processed data to data/processed/ so downstream agents can load from disk.
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


@tool("Ingest and Clean CMAPSS Dataset")
def ingest_and_clean_tool(dataset_name: str, dataset_id: str = "FD001") -> str:
    """
    Load a raw CMAPSS text file (train/test/rul), validate sensors, clean it,
    generate piecewise linear RUL labels, and save to data/processed/train_{dataset_id}_clean.csv.
    Pass dataset_name as 'train' for the training pipeline.
    Pass dataset_id as 'FD001', 'FD002', 'FD003', or 'FD004'.
    """
    from tools.ingest_tools import clean_data, generate_rul_labels, load_dataset, validate_sensors
    cfg = _load_config()
    df = load_dataset(dataset_name, dataset_id=dataset_id)
    report = validate_sensors(df)
    cleaned = clean_data(df, dataset_id=dataset_id)
    labeled = generate_rul_labels(cleaned, cap=cfg["rul"]["cap"])
    save_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"{dataset_name}_{dataset_id}_clean.csv"
    save_path.parent.mkdir(parents=True, exist_ok=True)
    labeled.to_csv(save_path, index=False)
    return (
        f"Dataset '{dataset_name}' ({dataset_id}) ingested: {len(labeled)} rows, "
        f"{labeled['unit_id'].nunique()} engines, "
        f"RUL range {labeled['RUL'].min()}–{labeled['RUL'].max()} cycles. "
        f"Constant sensors removed: {report['constant_sensors']}. "
        f"Saved to {save_path}."
    )


@tool("Visualize Engine Sensor Trends")
def visualize_engine_trends_tool(engine_id: str, dataset_id: str = "FD001") -> str:
    """
    Generate and save a sensor trend chart for a specific engine.
    Requires ingest_and_clean_tool to have been run first so the clean CSV exists.
    Input: engine_id as a string integer (e.g. '1'), dataset_id as 'FD001'–'FD004'.
    """
    import pandas as pd
    from tools.ingest_tools import visualize_trends
    cfg = _load_config()
    data_path = _PROJECT_ROOT / cfg["data"]["processed_dir"] / f"train_{dataset_id}_clean.csv"
    df = pd.read_csv(data_path)
    chart_path = visualize_trends(df, engine_id=int(engine_id), dataset_id=dataset_id)
    return f"Sensor trend chart saved for engine {engine_id} ({dataset_id}): {chart_path}"


def build_data_engineer_agent() -> Agent:
    """
    Instantiate and return the DataEngineerAgent.

    Returns
    -------
    Agent
        CrewAI Agent configured with data ingestion tools and Gemini LLM.
    """
    return Agent(
        role="Senior Aerospace Data Engineer",
        goal="Ingest, validate, clean, and prepare turbofan sensor data for ML prediction",
        backstory=(
            "You are a veteran data engineer with 15 years processing aerospace sensor "
            "telemetry from turbofan test cells. You ensure data quality, remove faulty "
            "sensors, normalize readings, and prepare clean datasets for ML pipelines."
        ),
        tools=[ingest_and_clean_tool, visualize_engine_trends_tool],
        llm=_get_llm(),
        verbose=True,
    )
