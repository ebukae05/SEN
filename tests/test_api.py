"""Tests for the SEN FastAPI backend.

Covers /health, /engines, /engine/{id}/status, /analyze, and the /ingest/*
ingestion endpoints. The /analyze endpoint fires the live three-agent crew
and is gated behind RUN_LIVE_CREW=1 so the suite stays fast and
offline-friendly by default.
"""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TEST_API_KEY = "test-key-for-pytest-only"
os.environ.setdefault("SEN_API_KEY", TEST_API_KEY)

from agents import get_active_dataframe  # noqa: E402
from api.main import app  # noqa: E402
from ingestion.store import LocalFilesystemStore, set_store  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    """FastAPI test client (in-process, no socket).

    Pre-loaded with the X-API-Key header so the existing endpoint tests
    don't need to know about auth. Tests that care about auth use a fresh
    TestClient instance directly.
    """
    tc = TestClient(app)
    tc.headers.update({"X-API-Key": TEST_API_KEY})
    return tc


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


class TestAuth:
    """API key authentication on protected vs. public endpoints."""

    def test_health_is_public(self) -> None:
        # No header attached — /health is in security.public_endpoints
        tc = TestClient(app)
        response = tc.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_engines_without_key_returns_401(self) -> None:
        tc = TestClient(app)
        response = tc.get("/engines")
        assert response.status_code == 401

    def test_engines_with_valid_key_returns_200(self) -> None:
        tc = TestClient(app)
        response = tc.get("/engines", headers={"X-API-Key": TEST_API_KEY})
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_engines_with_invalid_key_returns_401(self) -> None:
        tc = TestClient(app)
        response = tc.get("/engines", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401


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


@pytest.fixture
def isolated_store(tmp_path: Path) -> LocalFilesystemStore:
    """Swap the global ingestion store for a temp-dir-backed one."""
    store = LocalFilesystemStore(tmp_path / "custom")
    set_store(store)
    return store


def _csv_bytes(units: int = 3, rows_per_unit: int = 60) -> bytes:
    """Return small synthetic CSV bytes suitable for /ingest tests."""
    rows = []
    for unit_id in range(1, units + 1):
        for cycle in range(1, rows_per_unit + 1):
            rows.append(
                {
                    "unit_id": unit_id,
                    "cycle": cycle,
                    "vib_de": 1.0 + 0.01 * cycle,
                    "vib_nde": 0.9 + 0.005 * cycle,
                    "bearing_temp": 60 + 0.2 * cycle,
                    "rul": max(0, rows_per_unit - cycle),
                }
            )
    buf = io.BytesIO()
    pd.DataFrame(rows).to_csv(buf, index=False)
    return buf.getvalue()


class TestIngestUpload:
    """POST /ingest/upload."""

    def test_returns_preview(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        response = client.post(
            "/ingest/upload",
            files={"file": ("sample.csv", _csv_bytes(), "text/csv")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["row_count"] == 180
        assert "unit_id" in body["columns"]
        assert body["quality"]["engines_loaded"] == 3
        assert body["suggestions"]["unit_id"] == "unit_id"

    def test_empty_upload_rejected(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        response = client.post(
            "/ingest/upload",
            files={"file": ("empty.csv", b"", "text/csv")},
        )
        assert response.status_code == 400


class TestIngestSchema:
    """POST /ingest/schema."""

    def test_happy_path_creates_dataset(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        upload = client.post(
            "/ingest/upload",
            files={"file": ("sample.csv", _csv_bytes(), "text/csv")},
        ).json()
        payload = {
            "upload_id": upload["upload_id"],
            "asset_id": "compressor-A",
            "asset_type": "centrifugal_compressor",
            "industry": "oil_gas",
            "cycle_column": "cycle",
            "unit_id_column": "unit_id",
            "rul_column": "rul",
            "mappings": [
                {"column_name": "unit_id", "role": "unit_id"},
                {"column_name": "cycle", "role": "cycle"},
                {"column_name": "vib_de", "role": "sensor", "type_tag": "vibration"},
                {"column_name": "vib_nde", "role": "sensor", "type_tag": "vibration"},
                {"column_name": "bearing_temp", "role": "sensor", "type_tag": "temperature"},
                {"column_name": "rul", "role": "rul"},
            ],
        }
        response = client.post("/ingest/schema", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ready"
        assert body["meta"]["engine_count"] == 3
        assert body["meta"]["sensor_count"] == 3

    def test_too_few_sensors_returns_failed(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        upload = client.post(
            "/ingest/upload",
            files={"file": ("sample.csv", _csv_bytes(), "text/csv")},
        ).json()
        payload = {
            "upload_id": upload["upload_id"],
            "asset_id": "compressor-B",
            "asset_type": "centrifugal_compressor",
            "industry": "oil_gas",
            "cycle_column": "cycle",
            "unit_id_column": "unit_id",
            "rul_column": None,
            "mappings": [
                {"column_name": "unit_id", "role": "unit_id"},
                {"column_name": "cycle", "role": "cycle"},
                {"column_name": "vib_de", "role": "sensor", "type_tag": "vibration"},
            ],
        }
        response = client.post("/ingest/schema", json=payload)
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "failed"
        assert any("sensor columns required" in e for e in body["errors"])


class TestIngestDatasets:
    """GET /ingest/datasets and DELETE /ingest/dataset/{id}."""

    def test_list_includes_cmapss(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        response = client.get("/ingest/datasets")
        assert response.status_code == 200
        ids = [d["dataset_id"] for d in response.json()]
        assert "FD001" in ids

    def test_delete_cmapss_rejected(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        response = client.delete("/ingest/dataset/FD001")
        assert response.status_code == 400

    def test_delete_missing_returns_404(
        self, client: TestClient, isolated_store: LocalFilesystemStore
    ) -> None:
        response = client.delete("/ingest/dataset/nonexistent-xxxxxx")
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
