"""Tests for the SEN FastAPI backend.

Covers /health, /engines, /engine/{id}/status, and /analyze. The /analyze
endpoint fires the live three-agent crew and is gated behind RUN_LIVE_CREW=1
so the suite stays fast and offline-friendly by default.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents import get_active_dataframe  # noqa: E402
from api.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI test client (in-process, no socket)."""
    return TestClient(app)


@pytest.fixture(scope="module")
def known_engine_id() -> int:
    """A real engine_id from the active processed dataset."""
    return int(get_active_dataframe()["unit_id"].min())


class TestHealth:
    """GET /health."""

    def test_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestEngines:
    """GET /engines."""

    def test_returns_sorted_int_list(
        self, client: TestClient, known_engine_id: int
    ) -> None:
        response = client.get("/engines")
        assert response.status_code == 200
        engine_ids = response.json()
        assert isinstance(engine_ids, list)
        assert len(engine_ids) > 0
        assert all(isinstance(eid, int) for eid in engine_ids)
        assert engine_ids == sorted(engine_ids)
        assert known_engine_id in engine_ids


class TestEngineStatus:
    """GET /engine/{engine_id}/status."""

    def test_returns_status_for_known_engine(
        self, client: TestClient, known_engine_id: int
    ) -> None:
        response = client.get(f"/engine/{known_engine_id}/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["engine_id"] == known_engine_id
        assert isinstance(payload["predicted_rul"], float)
        assert payload["severity"] in {"healthy", "watch", "critical"}
        assert isinstance(payload["alert"], bool)
        assert payload["threshold"] > 0

    def test_unknown_engine_returns_404(self, client: TestClient) -> None:
        response = client.get("/engine/999999/status")
        assert response.status_code == 404


class TestAnalyzeValidation:
    """POST /analyze input validation (no LLM call)."""

    def test_zero_engine_id_rejected(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"engine_id": 0})
        assert response.status_code == 422

    def test_negative_engine_id_rejected(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"engine_id": -5})
        assert response.status_code == 422

    def test_missing_engine_id_rejected(self, client: TestClient) -> None:
        response = client.post("/analyze", json={})
        assert response.status_code == 422

    def test_unknown_engine_returns_404(self, client: TestClient) -> None:
        response = client.post("/analyze", json={"engine_id": 999999})
        assert response.status_code == 404


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_CREW") != "1",
    reason="set RUN_LIVE_CREW=1 to exercise the live crew via /analyze",
)
class TestAnalyzeLive:
    """POST /analyze full crew kickoff against live Gemini."""

    def test_analyze_known_engine(
        self, client: TestClient, known_engine_id: int
    ) -> None:
        response = client.post(
            "/analyze", json={"engine_id": known_engine_id}
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["engine_id"] == known_engine_id
        assert isinstance(payload["result"], str)
        assert len(payload["result"]) > 0
