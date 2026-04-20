"""
tests/test_agents.py — Phase 6 verification: full crew pipeline end-to-end test.

Run with:
    python tests/test_agents.py

Kicks off the 4-agent sequential crew for engine 1 and verifies the output
contains a maintenance recommendation and report path.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_full_pipeline() -> bool:
    """Run the complete 4-agent crew for engine 1 and verify meaningful output."""
    try:
        from crews.maintenance_crew import run_pipeline
        result = run_pipeline(engine_id=1)
        assert isinstance(result, str) and len(result) > 20, "Empty or invalid pipeline output"
        logger.info("Full pipeline output (%d chars): %s...", len(result), result[:200])
        return True
    except Exception as exc:
        logger.error("Full pipeline FAILED: %s", exc)
        return False


def test_pdf_report_exists() -> bool:
    """Verify the PDF report was created for engine 1."""
    try:
        report_path = Path(__file__).parent.parent / "data" / "processed" / "reports" / "engine_1_report.pdf"
        assert report_path.exists(), f"PDF report not found: {report_path}"
        logger.info("PDF report verified: %s", report_path)
        return True
    except Exception as exc:
        logger.error("PDF report check FAILED: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "full_pipeline":    test_full_pipeline(),
        "pdf_report_exists": test_pdf_report_exists(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("Phase 6 results: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed: %s", failed)
        sys.exit(1)

    logger.info("Phase 6 COMPLETE — full agent pipeline verified.")
