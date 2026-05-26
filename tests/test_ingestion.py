"""Tests for the ingestion subsystem (store + pipeline)."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ingestion.pipeline import (
    UploadPreview,
    process_upload,
    save_upload_and_preview,
)
from ingestion.store import (
    LocalFilesystemStore,
    SensorMapping,
    SensorSchema,
    set_store,
)


@pytest.fixture
def store(tmp_path: Path) -> LocalFilesystemStore:
    """Return a LocalFilesystemStore rooted at a temp directory."""
    backend = LocalFilesystemStore(tmp_path / "custom")
    set_store(backend)
    return backend


def _make_csv(path: Path, units: int = 3, rows_per_unit: int = 60) -> bytes:
    """Build a small synthetic dataset and write it to disk; also return raw bytes."""
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
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path.read_bytes()


def _make_schema(upload_id: str) -> SensorSchema:
    """Construct a valid SensorSchema for the synthetic CSV above."""
    return SensorSchema(
        upload_id=upload_id,
        asset_id="test-compressor",
        asset_type="centrifugal_compressor",
        industry="oil_gas",
        cycle_column="cycle",
        unit_id_column="unit_id",
        rul_column="rul",
        mappings=[
            SensorMapping(column_name="unit_id", role="unit_id"),
            SensorMapping(column_name="cycle", role="cycle"),
            SensorMapping(
                column_name="vib_de",
                role="sensor",
                display_name="Drive-End Vibration",
                type_tag="vibration",
                unit="mm/s",
            ),
            SensorMapping(
                column_name="vib_nde",
                role="sensor",
                display_name="Non-Drive-End Vibration",
                type_tag="vibration",
                unit="mm/s",
            ),
            SensorMapping(
                column_name="bearing_temp",
                role="sensor",
                display_name="Bearing Temperature",
                type_tag="temperature",
                unit="C",
            ),
            SensorMapping(column_name="rul", role="rul"),
        ],
    )


class TestUploadPreview:
    """save_upload_and_preview happy and error paths."""

    def test_preview_returns_columns_and_quality(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv")
        preview: UploadPreview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        assert preview.row_count == 180
        assert preview.format == "csv"
        assert "unit_id" in preview.columns
        assert "bearing_temp" in preview.columns
        assert preview.quality.is_valid is True
        assert preview.quality.engines_loaded == 3
        assert preview.suggestions["unit_id"] == "unit_id"
        assert preview.suggestions["cycle"] == "cycle"
        assert preview.suggestions["rul"] == "rul"
        assert preview.suggestions["vib_de"] == "sensor"

    def test_oversized_upload_rejected(self, store: LocalFilesystemStore) -> None:
        oversized = b"x" * (60 * 1024 * 1024)
        with pytest.raises(ValueError, match="max allowed"):
            save_upload_and_preview(oversized, "huge.csv", store)


class TestProcessUpload:
    """process_upload happy and validation-rejection paths."""

    def test_happy_path_creates_dataset(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv")
        preview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        schema = _make_schema(preview.upload_id)
        result = process_upload(schema, store)
        assert result.status == "ready"
        assert result.dataset_id.startswith("test-compressor-")
        assert result.meta.engine_count == 3
        assert result.meta.sensor_count == 3
        assert result.meta.has_rul is True
        processed_path = store.get_processed_path(result.dataset_id)
        assert processed_path.exists()
        df = pd.read_csv(processed_path)
        assert set(df.columns) >= {"unit_id", "cycle", "vib_de", "vib_nde", "bearing_temp", "RUL"}
        # Sensors should be in [0, 1] after MinMaxScaler.
        assert df[["vib_de", "vib_nde", "bearing_temp"]].max().max() <= 1.0
        assert df[["vib_de", "vib_nde", "bearing_temp"]].min().min() >= 0.0

    def test_too_few_sensors_rejected(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv")
        preview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        schema = _make_schema(preview.upload_id)
        schema.mappings = [
            m for m in schema.mappings if m.column_name not in {"vib_nde", "bearing_temp"}
        ]
        result = process_upload(schema, store)
        assert result.status == "failed"
        assert any("sensor columns required" in e for e in result.errors)

    def test_short_engine_rejected(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv", units=2, rows_per_unit=20)
        preview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        schema = _make_schema(preview.upload_id)
        result = process_upload(schema, store)
        assert result.status == "failed"
        assert any("fewer than" in e for e in result.errors)

    def test_unsupervised_path_generates_rul(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv")
        preview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        schema = _make_schema(preview.upload_id)
        schema.rul_column = None
        schema.mappings = [m for m in schema.mappings if m.role != "rul"]
        result = process_upload(schema, store)
        assert result.status == "ready"
        assert result.meta.has_rul is False
        df = pd.read_csv(store.get_processed_path(result.dataset_id))
        assert "RUL" in df.columns


class TestStoreRoundtrip:
    """LocalFilesystemStore list + get_meta + delete."""

    def test_list_and_delete(
        self, store: LocalFilesystemStore, tmp_path: Path
    ) -> None:
        csv_bytes = _make_csv(tmp_path / "sample.csv")
        preview = save_upload_and_preview(csv_bytes, "sample.csv", store)
        schema = _make_schema(preview.upload_id)
        result = process_upload(schema, store)
        assert store.list_datasets()[0].dataset_id == result.dataset_id
        assert store.get_meta(result.dataset_id) is not None
        assert store.delete_dataset(result.dataset_id) is True
        assert store.get_meta(result.dataset_id) is None
        assert store.list_datasets() == []
