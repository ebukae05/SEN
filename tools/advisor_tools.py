"""Advisor tools — convert diagnoses into recommendations and PDF reports.

Used by the MaintenanceAdvisorAgent. The only external API call is the
Gemini 2.5 Flash call in recommend_action.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
ENV_PATH = REPO_ROOT / ".env"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


def time_to_critical(rul: float, degradation_rate: float) -> float:
    """Estimate the cycles remaining before the engine reaches a critical RUL.

    Args:
        rul: Current predicted RUL in cycles.
        degradation_rate: Engine's degradation ratio vs fleet (1.0 = normal).

    Returns:
        Estimated cycles to critical, floored at zero.
    """
    if rul < 0:
        raise ValueError(f"rul cannot be negative, got {rul}")
    critical_threshold = _load_config()["monitoring"]["severity"]["critical_below"]
    if rul <= critical_threshold:
        return 0.0
    safe_rate = max(0.1, float(degradation_rate))
    return float((rul - critical_threshold) / safe_rate)


@lru_cache(maxsize=1)
def _get_llm() -> ChatGoogleGenerativeAI:
    """Construct (and cache) the Gemini chat client per config."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH)
    config = _load_config()["llm"]
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        raise RuntimeError(f"Environment variable {config['api_key_env']} is not set")
    return ChatGoogleGenerativeAI(
        model=config["model"],
        google_api_key=api_key,
        temperature=config["temperature"],
        max_output_tokens=config["max_output_tokens"],
    )


def _format_diagnosis(diagnosis: dict[str, Any]) -> str:
    """Render a diagnosis dict as a human-readable summary block."""
    lines = [f"- {key}: {value}" for key, value in diagnosis.items()]
    return "\n".join(lines)


def recommend_action(diagnosis: dict[str, Any]) -> str:
    """Call Gemini to produce a maintenance recommendation from a diagnosis.

    Args:
        diagnosis: Dict with engine_id, rul, degrading sensors, severity, etc.

    Returns:
        Natural-language recommendation string.
    """
    if not isinstance(diagnosis, dict):
        raise TypeError("diagnosis must be a dict")
    if not diagnosis:
        raise ValueError("diagnosis must not be empty")
    prompt = (
        "You are a senior aircraft maintenance engineer. Given the engine "
        "diagnosis below, write a concise, actionable recommendation in 3-5 "
        "sentences. Include urgency level, recommended action, and estimated "
        "downtime category (none/short/extended).\n\n"
        f"Diagnosis:\n{_format_diagnosis(diagnosis)}\n\nRecommendation:"
    )
    llm = _get_llm()
    response = llm.invoke(prompt)
    return response.content.strip()


def _build_pdf_story(
    engine_id: int, diagnosis: dict[str, Any], recommendation: str
) -> list:
    """Build the ReportLab flowable list for the maintenance report."""
    styles = getSampleStyleSheet()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story = [
        Paragraph(f"SEN Maintenance Report — Engine {engine_id}", styles["Title"]),
        Paragraph(f"Generated: {timestamp}", styles["Normal"]),
        Spacer(1, 18),
        Paragraph("Diagnosis", styles["Heading2"]),
    ]
    for key, value in diagnosis.items():
        story.append(Paragraph(f"<b>{key}:</b> {value}", styles["Normal"]))
    story.append(Spacer(1, 18))
    story.append(Paragraph("Recommendation", styles["Heading2"]))
    story.append(Paragraph(recommendation, styles["Normal"]))
    return story


def generate_report(
    engine_id: int, diagnosis: dict[str, Any], recommendation: str
) -> Path:
    """Render a PDF maintenance report and return its path.

    Args:
        engine_id: Engine the report describes.
        diagnosis: Diagnostic findings.
        recommendation: Recommendation text (e.g., from recommend_action).

    Returns:
        Path to the written PDF under outputs/reports/.
    """
    if not isinstance(diagnosis, dict):
        raise TypeError("diagnosis must be a dict")
    config = _load_config()
    reports_dir = REPO_ROOT / config["paths"]["outputs_reports"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = reports_dir / f"engine_{engine_id}_{stamp}.pdf"
    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER)
    doc.build(_build_pdf_story(engine_id, diagnosis, recommendation))
    logger.info("Wrote maintenance report to %s", pdf_path)
    return pdf_path
