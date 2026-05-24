"""Shared helpers for SEN agents."""

from __future__ import annotations

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from crewai import LLM
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
ENV_PATH = REPO_ROOT / ".env"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


@lru_cache(maxsize=1)
def get_llm() -> LLM:
    """Construct (and cache) the CrewAI LLM client pointing at Gemini 2.5 Flash."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    config = load_config()["llm"]
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        raise RuntimeError(f"Environment variable {config['api_key_env']} not set")
    return LLM(
        model=f"gemini/{config['model']}",
        api_key=api_key,
        temperature=config["temperature"],
    )


@lru_cache(maxsize=4)
def get_active_dataframe(dataset_id: str | None = None) -> pd.DataFrame:
    """Load (and cache) the preprocessed CSV for the active or requested dataset."""
    config = load_config()
    target = dataset_id or config["data"]["active_dataset"]
    csv_name = config["data"]["processed_filename"].format(dataset_id=target)
    csv_path = REPO_ROOT / config["paths"]["data_processed"] / csv_name
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed dataset missing: {csv_path}. Run preprocess.py first."
        )
    return pd.read_csv(csv_path)
