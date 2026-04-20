"""
tests/test_dashboard.py — Phase 8 verification: Dash app structure tests.

Run with:
    python tests/test_dashboard.py

Verifies the app layout, fleet data computation, and callback outputs
without spinning up a live server.
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


def test_app_import() -> bool:
    """Dashboard app can be imported and Dash instance exists."""
    try:
        from dashboard.app import app
        assert app is not None
        logger.info("Dashboard import: OK")
        return True
    except Exception as exc:
        logger.error("Dashboard import FAILED: %s", exc)
        return False


def test_fleet_data() -> bool:
    """Fleet RUL DataFrame has 100 engines with expected columns."""
    try:
        from dashboard.app import _fleet_df
        assert len(_fleet_df) == 100, f"Expected 100 engines, got {len(_fleet_df)}"
        for col in ("engine_id", "predicted_rul", "severity"):
            assert col in _fleet_df.columns, f"Missing column: {col}"
        valid_severities = {"NORMAL", "CAUTION", "WARNING", "CRITICAL"}
        assert set(_fleet_df["severity"].unique()).issubset(valid_severities)
        logger.info(
            "Fleet data: OK — %d engines, severities=%s",
            len(_fleet_df),
            dict(_fleet_df["severity"].value_counts()),
        )
        return True
    except Exception as exc:
        logger.error("Fleet data FAILED: %s", exc)
        return False


def test_layout_components() -> bool:
    """App layout contains the expected top-level component IDs."""
    try:
        from dashboard.app import app
        layout_str = str(app.layout)
        for component_id in ("summary-cards", "tabs", "tab-content"):
            assert component_id in layout_str, f"Missing component: {component_id}"
        logger.info("Layout components: OK")
        return True
    except Exception as exc:
        logger.error("Layout components FAILED: %s", exc)
        return False


def test_rul_range() -> bool:
    """All predicted RUL values are non-negative."""
    try:
        from dashboard.app import _fleet_df
        assert (_fleet_df["predicted_rul"] >= 0).all(), "Negative RUL values found"
        min_rul = _fleet_df["predicted_rul"].min()
        max_rul = _fleet_df["predicted_rul"].max()
        logger.info("RUL range: OK — min=%.1f, max=%.1f", min_rul, max_rul)
        return True
    except Exception as exc:
        logger.error("RUL range FAILED: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "app_import":        test_app_import(),
        "fleet_data":        test_fleet_data(),
        "layout_components": test_layout_components(),
        "rul_range":         test_rul_range(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("Phase 8 results: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed: %s", failed)
        sys.exit(1)

    logger.info("Phase 8 COMPLETE — Dash dashboard verified.")
