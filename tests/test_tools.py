"""
tests/test_tools.py — Phase 2 verification tests for tools/ingest_tools.py.

Run with:
    python tests/test_tools.py
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

from tools.ingest_tools import (
    clean_data,
    generate_rul_labels,
    load_dataset,
    validate_sensors,
    visualize_trends,
)


def test_load_dataset() -> bool:
    """Verify load_dataset returns a correctly shaped DataFrame."""
    try:
        df = load_dataset("train")
        assert len(df) > 0, "DataFrame is empty"
        assert "unit_id" in df.columns, "Missing unit_id column"
        assert "cycle" in df.columns, "Missing cycle column"
        assert len(df.columns) == 26, f"Expected 26 cols, got {len(df.columns)}"
        logger.info("load_dataset: OK (%d rows, %d cols)", len(df), len(df.columns))
        return True
    except Exception as exc:
        logger.error("load_dataset FAILED: %s", exc)
        return False


def test_validate_sensors() -> bool:
    """Verify validate_sensors returns a report with all expected keys."""
    try:
        df = load_dataset("train")
        report = validate_sensors(df)
        for key in ("missing_values", "constant_sensors", "infinite_values", "total_rows", "total_sensors"):
            assert key in report, f"Missing key: {key}"
        assert report["total_sensors"] == 21, f"Expected 21 sensors, got {report['total_sensors']}"
        logger.info("validate_sensors: OK — constant sensors detected: %s", report["constant_sensors"])
        return True
    except Exception as exc:
        logger.error("validate_sensors FAILED: %s", exc)
        return False


def test_clean_data() -> bool:
    """Verify clean_data keeps 14 sensors and normalizes them to [0, 1]."""
    try:
        df = load_dataset("train")
        cleaned = clean_data(df)
        sensor_cols = [c for c in cleaned.columns if c.startswith("s")]
        assert len(sensor_cols) == 14, f"Expected 14 sensor cols, got {len(sensor_cols)}"
        for col in sensor_cols:
            assert cleaned[col].min() >= -1e-6, f"{col} min below 0: {cleaned[col].min()}"
            assert cleaned[col].max() <= 1 + 1e-6, f"{col} max above 1: {cleaned[col].max()}"
        logger.info("clean_data: OK (%d sensors, all in [0, 1])", len(sensor_cols))
        return True
    except Exception as exc:
        logger.error("clean_data FAILED: %s", exc)
        return False


def test_generate_rul_labels() -> bool:
    """Verify generate_rul_labels adds a RUL column capped at 130 with min 0."""
    try:
        df = load_dataset("train")
        cleaned = clean_data(df)
        labeled = generate_rul_labels(cleaned, cap=130)
        assert "RUL" in labeled.columns, "RUL column missing"
        assert labeled["RUL"].max() <= 130, f"RUL exceeds cap: {labeled['RUL'].max()}"
        assert labeled["RUL"].min() == 0, f"Min RUL should be 0, got {labeled['RUL'].min()}"
        logger.info("generate_rul_labels: OK (max=%d, min=%d)", labeled["RUL"].max(), labeled["RUL"].min())
        return True
    except Exception as exc:
        logger.error("generate_rul_labels FAILED: %s", exc)
        return False


def test_visualize_trends() -> bool:
    """Verify visualize_trends saves a PNG chart to data/processed/charts/."""
    try:
        df = load_dataset("train")
        cleaned = clean_data(df)
        chart_path = visualize_trends(cleaned, engine_id=1)
        assert chart_path.exists(), f"Chart file not saved: {chart_path}"
        assert chart_path.suffix == ".png", f"Expected .png, got {chart_path.suffix}"
        logger.info("visualize_trends: OK — chart at %s", chart_path)
        return True
    except Exception as exc:
        logger.error("visualize_trends FAILED: %s", exc)
        return False


from tools.stream_tools import stream_sensors
from tools.predict_tools import predict_rul, check_thresholds


def test_stream_sensors() -> bool:
    """Verify stream_sensors yields correctly shaped windows."""
    try:
        df = load_dataset("train")
        cleaned = clean_data(df)
        windows = list(stream_sensors(cleaned, engine_id=1, window_size=30))
        assert len(windows) > 0, "No windows yielded"
        assert windows[0].shape == (30, 14), f"Expected (30, 14), got {windows[0].shape}"
        logger.info("stream_sensors: OK — %d windows for engine 1", len(windows))
        return True
    except Exception as exc:
        logger.error("stream_sensors FAILED: %s", exc)
        return False


def test_predict_rul() -> bool:
    """Verify predict_rul returns a non-negative float for a valid window."""
    try:
        df = load_dataset("train")
        cleaned = clean_data(df)
        window = next(stream_sensors(cleaned, engine_id=1, window_size=30))
        rul = predict_rul(window)
        assert isinstance(rul, float), f"Expected float, got {type(rul)}"
        assert rul >= 0.0, f"RUL should be non-negative, got {rul}"
        logger.info("predict_rul: OK — predicted RUL=%.2f cycles", rul)
        return True
    except Exception as exc:
        logger.error("predict_rul FAILED: %s", exc)
        return False


def test_check_thresholds() -> bool:
    """Verify check_thresholds returns correct alert status for low and high RUL."""
    try:
        alert_result = check_thresholds(engine_id=1, rul=20.0, threshold=50)
        assert alert_result["alert"] is True, "Expected alert for RUL=20 < threshold=50"
        assert alert_result["severity"] != "NORMAL"

        safe_result = check_thresholds(engine_id=2, rul=100.0, threshold=50)
        assert safe_result["alert"] is False, "Expected no alert for RUL=100 > threshold=50"
        assert safe_result["severity"] == "NORMAL"

        logger.info("check_thresholds: OK — alert=%s, safe=%s",
                    alert_result["severity"], safe_result["severity"])
        return True
    except Exception as exc:
        logger.error("check_thresholds FAILED: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "load_dataset":        test_load_dataset(),
        "validate_sensors":    test_validate_sensors(),
        "clean_data":          test_clean_data(),
        "generate_rul_labels": test_generate_rul_labels(),
        "visualize_trends":    test_visualize_trends(),
        "stream_sensors":      test_stream_sensors(),
        "predict_rul":         test_predict_rul(),
        "check_thresholds":    test_check_thresholds(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("Phase 2+4 results: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed: %s", failed)
        sys.exit(1)

    logger.info("Phases 2+4 COMPLETE — all tools verified.")
