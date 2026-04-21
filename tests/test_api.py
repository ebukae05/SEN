"""
tests/test_api.py — Phase 7 verification: FastAPI endpoint tests.

Run with:
    python tests/test_api.py

Tests /health, /datasets, /engines, /engine/{id}/status, /fleet,
/engine/{id}/sensors, and 404 handling across datasets.
POST /analyze is excluded from automated tests (burns LLM quota).
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

EXPECTED_ENGINES = {"FD001": 100, "FD002": 260, "FD003": 100, "FD004": 249}
EXPECTED_SENSORS = {"FD001": 14, "FD002": 16, "FD003": 14, "FD004": 16}


def test_health() -> bool:
    """GET /health should return 200 with status=ok."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        logger.info("GET /health: OK")
        return True
    except Exception as exc:
        logger.error("GET /health FAILED: %s", exc)
        return False


def test_datasets() -> bool:
    """GET /datasets should return metadata for all 4 CMAPSS datasets."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/datasets")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4, f"Expected 4 datasets, got {len(data)}"
        ids = {d["dataset_id"] for d in data}
        assert ids == {"FD001", "FD002", "FD003", "FD004"}
        logger.info("GET /datasets: OK — %s", ids)
        return True
    except Exception as exc:
        logger.error("GET /datasets FAILED: %s", exc)
        return False


def test_list_engines() -> bool:
    """GET /engines should return correct engine count per dataset."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        for ds, expected in EXPECTED_ENGINES.items():
            resp = client.get(f"/engines?dataset={ds}")
            assert resp.status_code == 200
            ids = resp.json()
            assert isinstance(ids, list) and len(ids) == expected, \
                f"{ds}: expected {expected} engines, got {len(ids)}"
        logger.info("GET /engines: OK — all 4 datasets correct")
        return True
    except Exception as exc:
        logger.error("GET /engines FAILED: %s", exc)
        return False


def test_engine_status() -> bool:
    """GET /engine/1/status should return valid RUL and severity."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/engine/1/status?dataset=FD001")
        assert resp.status_code == 200
        data = resp.json()
        assert "predicted_rul" in data and "severity" in data and "alert" in data
        assert data["severity"] in {"NORMAL", "CAUTION", "WARNING", "CRITICAL"}
        assert isinstance(data["alert"], bool)
        logger.info(
            "GET /engine/1/status: OK — RUL=%.1f, severity=%s, alert=%s",
            data["predicted_rul"],
            data["severity"],
            data["alert"],
        )
        return True
    except Exception as exc:
        logger.error("GET /engine/1/status FAILED: %s", exc)
        return False


def test_fleet() -> bool:
    """GET /fleet should return correct engine count per dataset."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        for ds, expected in EXPECTED_ENGINES.items():
            resp = client.get(f"/fleet?dataset={ds}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == expected, f"{ds}: expected {expected}, got {len(data)}"
        logger.info("GET /fleet: OK — all 4 datasets correct")
        return True
    except Exception as exc:
        logger.error("GET /fleet FAILED: %s", exc)
        return False


def test_sensors() -> bool:
    """GET /engine/1/sensors should return correct sensor count per dataset."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        for ds, expected in EXPECTED_SENSORS.items():
            resp = client.get(f"/engine/1/sensors?last_n=2&dataset={ds}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) > 0, f"{ds}: no readings returned"
            n_sensors = len(data[0]["sensors"])
            assert n_sensors == expected, f"{ds}: expected {expected} sensors, got {n_sensors}"
        logger.info("GET /engine/1/sensors: OK — sensor counts correct across datasets")
        return True
    except Exception as exc:
        logger.error("GET /engine/1/sensors FAILED: %s", exc)
        return False


def test_engine_not_found() -> bool:
    """GET /engine/9999/status should return 404."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/engine/9999/status?dataset=FD001")
        assert resp.status_code == 404
        logger.info("GET /engine/9999/status: 404 as expected")
        return True
    except Exception as exc:
        logger.error("404 test FAILED: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "health":           test_health(),
        "datasets":         test_datasets(),
        "list_engines":     test_list_engines(),
        "engine_status":    test_engine_status(),
        "fleet":            test_fleet(),
        "sensors":          test_sensors(),
        "engine_not_found": test_engine_not_found(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("API tests: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed: %s", failed)
        sys.exit(1)

    logger.info("All API tests PASSED.")
