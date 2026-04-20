"""
tests/test_api.py — Phase 7 verification: FastAPI endpoint tests.

Run with:
    python tests/test_api.py

Tests /health, /engines, /engine/{id}/status, and 404 handling.
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


def test_list_engines() -> bool:
    """GET /engines should return all 100 engine IDs."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/engines")
        assert resp.status_code == 200
        ids = resp.json()
        assert isinstance(ids, list) and len(ids) == 100
        assert 1 in ids and 100 in ids
        logger.info("GET /engines: OK — %d engines", len(ids))
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
        resp = client.get("/engine/1/status")
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


def test_engine_not_found() -> bool:
    """GET /engine/9999/status should return 404."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app

        client = TestClient(app)
        resp = client.get("/engine/9999/status")
        assert resp.status_code == 404
        logger.info("GET /engine/9999/status: 404 as expected")
        return True
    except Exception as exc:
        logger.error("404 test FAILED: %s", exc)
        return False


if __name__ == "__main__":
    results = {
        "health":           test_health(),
        "list_engines":     test_list_engines(),
        "engine_status":    test_engine_status(),
        "engine_not_found": test_engine_not_found(),
    }

    passed = sum(results.values())
    total = len(results)
    logger.info("Phase 7 results: %d/%d passed", passed, total)

    if passed < total:
        failed = [k for k, v in results.items() if not v]
        logger.error("Failed: %s", failed)
        sys.exit(1)

    logger.info("Phase 7 COMPLETE — FastAPI endpoints verified.")
