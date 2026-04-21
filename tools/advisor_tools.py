"""
tools/advisor_tools.py — MaintenanceAdvisorAgent tools for recommendations and reports.

Estimates time to critical failure, generates natural language maintenance
recommendations via Gemini, and produces formal PDF reports using ReportLab.
Supports all CMAPSS datasets (FD001–FD004).
"""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict[str, Any]:
    """Load and return parsed config.yaml."""
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def time_to_critical(rul: float, degradation_rate: float, critical_rul: float = 20.0) -> dict[str, Any]:
    """
    Estimate cycles remaining until the engine reaches a critical RUL threshold.

    Parameters
    ----------
    rul : float
        Current predicted RUL in cycles.
    degradation_rate : float
        Engine degradation rate ratio vs fleet (from diagnostic_tools.degradation_rate).
    critical_rul : float
        RUL threshold considered critical (default 20 cycles).

    Returns
    -------
    dict[str, Any]
        cycles_to_critical, adjusted_rul, urgency label.

    Raises
    ------
    TypeError
        If rul or degradation_rate are not numeric.
    ValueError
        If degradation_rate is not positive.
    """
    if not isinstance(rul, (float, int)):
        raise TypeError(f"rul must be numeric, got {type(rul)}")
    if not isinstance(degradation_rate, (float, int)):
        raise TypeError(f"degradation_rate must be numeric, got {type(degradation_rate)}")
    if degradation_rate <= 0:
        raise ValueError(f"degradation_rate must be positive, got {degradation_rate}")

    adjusted_rul = rul / degradation_rate
    cycles_to_critical = max(0.0, adjusted_rul - critical_rul)
    urgency = "IMMEDIATE" if cycles_to_critical < 10 else "SOON" if cycles_to_critical < 30 else "SCHEDULED"

    logger.info("Time to critical: %.1f cycles (urgency=%s)", cycles_to_critical, urgency)
    return {
        "rul":                round(float(rul), 2),
        "adjusted_rul":       round(float(adjusted_rul), 2),
        "cycles_to_critical": round(float(cycles_to_critical), 2),
        "urgency":            urgency,
    }


def recommend_action(diagnosis: dict[str, Any]) -> str:
    """
    Generate a natural language maintenance recommendation using Gemini 2.5 Flash.

    This is the only function in the tools layer that calls the Gemini API.

    Parameters
    ----------
    diagnosis : dict[str, Any]
        Combined diagnostic context including engine_id, rul, severity,
        degradation ratio, and declining sensors.

    Returns
    -------
    str
        Natural language maintenance recommendation from Gemini.

    Raises
    ------
    TypeError
        If diagnosis is not a dict.
    KeyError
        If the Gemini API call fails unexpectedly.
    """
    if not isinstance(diagnosis, dict):
        raise TypeError(f"diagnosis must be a dict, got {type(diagnosis)}")

    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY not set in environment")

    cfg = _load_config()
    model_name = cfg["llm"]["model"].replace("gemini/", "")
    dataset_id = diagnosis.get("dataset_id", "FD001")

    prompt = (
        f"You are a turbofan engine maintenance expert. Based on the following diagnostic data "
        f"from the CMAPSS {dataset_id} dataset, provide a concise (3-5 sentences) actionable "
        f"maintenance recommendation.\n\n"
        f"Engine ID: {diagnosis.get('engine_id', 'N/A')}\n"
        f"Dataset: {dataset_id}\n"
        f"Predicted RUL: {diagnosis.get('rul', 'N/A')} cycles\n"
        f"Severity: {diagnosis.get('severity', 'N/A')}\n"
        f"Degradation ratio vs fleet: {diagnosis.get('ratio', 'N/A')}\n"
        f"Top declining sensors: {diagnosis.get('ranked_declining', [])[:3]}\n"
        f"Urgency: {diagnosis.get('urgency', 'N/A')}\n\n"
        f"Recommendation:"
    )

    from google import genai
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(model=model_name, contents=prompt)
    recommendation = response.text.strip()
    logger.info("Gemini recommendation generated for engine %s (%s)", diagnosis.get("engine_id"), dataset_id)
    return recommendation


def generate_report(
    engine_id: int,
    diagnosis: dict[str, Any],
    recommendation: str,
    dataset_id: str | None = None,
) -> Path:
    """
    Create a PDF maintenance report using ReportLab and save it to data/processed/reports/.

    Parameters
    ----------
    engine_id : int
        Engine being reported on.
    diagnosis : dict[str, Any]
        Diagnostic data dict (from DiagnosticAgent output).
    recommendation : str
        Natural language recommendation (from recommend_action).
    dataset_id : str or None
        Target dataset for filename namespacing. Defaults to config active_dataset.

    Returns
    -------
    Path
        Absolute path to the saved PDF report.

    Raises
    ------
    TypeError
        If engine_id is not an int, diagnosis not a dict, or recommendation not a str.
    """
    if not isinstance(engine_id, int):
        raise TypeError(f"engine_id must be an int, got {type(engine_id)}")
    if not isinstance(diagnosis, dict):
        raise TypeError(f"diagnosis must be a dict, got {type(diagnosis)}")
    if not isinstance(recommendation, str):
        raise TypeError(f"recommendation must be a str, got {type(recommendation)}")

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.lib import colors
    import datetime

    if dataset_id is None:
        dataset_id = _load_config()["data"]["active_dataset"]

    reports_dir = _PROJECT_ROOT / _load_config()["data"]["processed_dir"] / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / f"engine_{engine_id}_{dataset_id}_report.pdf"

    doc = SimpleDocTemplate(str(output_path), pagesize=letter,
                            leftMargin=inch, rightMargin=inch,
                            topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"SEN — Engine Maintenance Report ({dataset_id})", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Engine ID: {engine_id} | Dataset: {dataset_id}", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * inch))

    diag_data = [["Parameter", "Value"]] + [
        [str(k), str(round(v, 3) if isinstance(v, float) else v)]
        for k, v in diagnosis.items() if k not in ("engine_id", "dataset_id")
    ]
    table = Table(diag_data, colWidths=[2.5 * inch, 3.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EBF3FB")]),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("Maintenance Recommendation", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph(recommendation, styles["Normal"]))

    doc.build(story)
    logger.info("PDF report saved: %s", output_path)
    return output_path
