"""Shared helpers for SEN agents."""

from __future__ import annotations

import logging
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

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


# Per-request active dataset for the agent tools. The CrewAI tools call
# `get_active_dataframe()` with no arguments because they don't know which
# dataset the API request was for; the /analyze handler sets this ContextVar
# before kicking off the crew so the tools see the right data.
_active_dataset_ctx: ContextVar[str | None] = ContextVar(
    "sen_active_dataset", default=None
)

# Explicit cache keyed on the *resolved* dataset id. The old lru_cache keyed
# on the literal argument, which meant `get_active_dataframe()` and
# `get_active_dataframe("FD001")` were treated as different cache entries —
# and more importantly, the ContextVar fallback was invisible to the cache.
_DATAFRAME_CACHE: dict[str, pd.DataFrame] = {}


@contextmanager
def active_dataset(dataset_id: str | None) -> Iterator[None]:
    """Set the per-request active dataset for the duration of a `with` block."""
    token = _active_dataset_ctx.set(dataset_id)
    try:
        yield
    finally:
        _active_dataset_ctx.reset(token)


def _resolve_dataset_id(dataset_id: str | None) -> str:
    """Pick the dataset id to load: explicit arg > ContextVar > config default."""
    if dataset_id:
        return dataset_id
    ctx_value = _active_dataset_ctx.get()
    if ctx_value:
        return ctx_value
    return load_config()["data"]["active_dataset"]


def _load_dataframe(target: str) -> pd.DataFrame:
    """Load the processed CSV for `target` from the custom store or CMAPSS dir."""
    # Custom datasets live in the ingestion store; check there first.
    # Import locally to avoid a hard import cycle between agents/ and ingestion/.
    from ingestion.heuristic import is_custom_dataset
    from ingestion.store import get_store

    if is_custom_dataset(target):
        meta = get_store().get_meta(target)
        if meta is not None:
            csv_path = get_store().get_processed_path(target)
            if not csv_path.exists():
                raise FileNotFoundError(
                    f"Processed custom dataset missing: {csv_path}"
                )
            logger.info("Loaded custom dataset %s from %s", target, csv_path)
            return pd.read_csv(csv_path)
        logger.warning(
            "Custom dataset_id %r not found in store; falling back to CMAPSS path",
            target,
        )
    config = load_config()
    csv_name = config["data"]["processed_filename"].format(dataset_id=target)
    csv_path = REPO_ROOT / config["paths"]["data_processed"] / csv_name
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Processed dataset missing: {csv_path}. Run preprocess.py first."
        )
    return pd.read_csv(csv_path)


def get_active_dataframe(dataset_id: str | None = None) -> pd.DataFrame:
    """Load (and cache) the preprocessed CSV for the active or requested dataset.

    Resolution order for the dataset id:
        1. Explicit `dataset_id` argument.
        2. Per-request `active_dataset(...)` context.
        3. `data.active_dataset` from config.yaml.

    Custom datasets (anything not in CMAPSS FD001-FD004) load from the
    ingestion store's processed.csv; otherwise the CMAPSS data/processed/ CSV.
    """
    target = _resolve_dataset_id(dataset_id)
    cached = _DATAFRAME_CACHE.get(target)
    if cached is not None:
        return cached
    df = _load_dataframe(target)
    _DATAFRAME_CACHE[target] = df
    return df


def invalidate_dataframe_cache(dataset_id: str | None = None) -> None:
    """Drop a cached DataFrame (or the whole cache if `dataset_id` is None)."""
    if dataset_id is None:
        _DATAFRAME_CACHE.clear()
        return
    _DATAFRAME_CACHE.pop(dataset_id, None)
