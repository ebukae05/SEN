"""Persistent storage for uploaded custom datasets.

A `StoreBackend` is an abstract interface; `LocalFilesystemStore` is the
default implementation backed by the project's `data/custom/` directory.
Swapping to S3 or a database is a one-class change — the API and pipeline
layers only depend on the abstract interface.

Directory layout per dataset (LocalFilesystemStore):
    data/custom/<dataset_id>/
        raw.<ext>        original upload (csv/json/xlsx)
        schema.json      sensor schema contract
        meta.json        dataset metadata
        processed.csv    normalized + RUL-labeled output
        scaler.pkl       fitted MinMaxScaler
        weights.pt       per-tenant CNN-LSTM weights (optional, post-training)
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    """Load and cache config.yaml from the project root."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"config.yaml not found at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as cfg_file:
        return yaml.safe_load(cfg_file)


@dataclass
class SensorMapping:
    """One row in the user's sensor schema."""

    column_name: str
    role: str
    display_name: str = ""
    type_tag: str = "custom"
    unit: str = ""
    warning_threshold: float | None = None
    critical_threshold: float | None = None


@dataclass
class SensorSchema:
    """Full sensor schema contract for one uploaded dataset."""

    upload_id: str
    asset_id: str
    asset_type: str
    industry: str
    cycle_column: str
    unit_id_column: str
    rul_column: str | None
    mappings: list[SensorMapping]
    tenant_id: str = "default"


@dataclass
class DatasetMeta:
    """Persisted metadata about an uploaded dataset.

    `status` lifecycle:
        pending -> ready (after ingestion)
        ready -> training -> trained | training_failed (post Goal-3 fine-tuning)
        failed (ingestion never produced a usable dataset)
    """

    dataset_id: str
    asset_id: str
    asset_type: str
    industry: str
    tenant_id: str = "default"
    source: str = "custom"
    status: str = "pending"
    created_at: str = ""
    sensor_count: int = 0
    engine_count: int = 0
    row_count: int = 0
    has_rul: bool = False
    sensor_display_names: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    training_rmse: float | None = None
    trained_at: str | None = None
    n_features_trained: int | None = None
    training_error: str | None = None


def _slugify(text: str) -> str:
    """Lowercase, replace non-alphanumerics with hyphens, trim."""
    out = []
    prev_dash = False
    for char in text.lower().strip():
        if char.isalnum():
            out.append(char)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or "dataset"


def make_dataset_id(asset_id: str) -> str:
    """Build a URL-safe dataset_id from an asset_id plus a short uuid."""
    slug = _slugify(asset_id)
    suffix = uuid.uuid4().hex[:6]
    return f"{slug}-{suffix}"


def _now_iso() -> str:
    """Current UTC timestamp as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StoreBackend(ABC):
    """Abstract storage backend for uploaded datasets."""

    @abstractmethod
    def save_upload(self, file_bytes: bytes, filename: str) -> tuple[str, Path]:
        """Persist a raw upload and return (upload_id, file_path)."""

    @abstractmethod
    def get_upload_path(self, upload_id: str) -> Path:
        """Return the on-disk path for a previously saved upload."""

    @abstractmethod
    def discard_upload(self, upload_id: str) -> None:
        """Delete a temp upload that was never promoted to a dataset."""

    @abstractmethod
    def create_dataset(
        self, schema: SensorSchema, raw_filename: str
    ) -> tuple[str, Path]:
        """Promote an upload to a dataset_id; returns (dataset_id, dataset_dir)."""

    @abstractmethod
    def save_schema(self, dataset_id: str, schema: SensorSchema) -> None:
        """Persist the sensor schema for a dataset."""

    @abstractmethod
    def save_meta(self, meta: DatasetMeta) -> None:
        """Persist the metadata record for a dataset."""

    @abstractmethod
    def get_meta(self, dataset_id: str) -> DatasetMeta | None:
        """Return metadata for one dataset, or None if missing."""

    @abstractmethod
    def get_schema(self, dataset_id: str) -> SensorSchema | None:
        """Return the saved schema for a dataset, or None if missing."""

    @abstractmethod
    def list_datasets(self) -> list[DatasetMeta]:
        """Return metadata for every persisted custom dataset."""

    @abstractmethod
    def get_processed_path(self, dataset_id: str) -> Path:
        """Return the processed CSV path for a dataset (may not yet exist)."""

    @abstractmethod
    def get_scaler_path(self, dataset_id: str) -> Path:
        """Return the scaler pickle path for a dataset."""

    @abstractmethod
    def get_weights_path(self, dataset_id: str) -> Path:
        """Return the per-dataset model-weights path (may not yet exist)."""

    @abstractmethod
    def delete_dataset(self, dataset_id: str) -> bool:
        """Remove all artifacts for a dataset. Returns True if anything was removed."""


class LocalFilesystemStore(StoreBackend):
    """File-backed StoreBackend using `data/custom/` under the repo root."""

    UPLOADS_DIR = "_uploads"
    META_FILE = "meta.json"
    SCHEMA_FILE = "schema.json"
    PROCESSED_FILE = "processed.csv"
    SCALER_FILE = "scaler.pkl"
    WEIGHTS_FILE = "weights.pt"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.uploads_dir = root / self.UPLOADS_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_bytes: bytes, filename: str) -> tuple[str, Path]:
        upload_id = uuid.uuid4().hex
        ext = Path(filename).suffix.lower().lstrip(".")
        if not ext:
            raise ValueError(f"Filename {filename!r} has no extension")
        target = self.uploads_dir / f"{upload_id}.{ext}"
        target.write_bytes(file_bytes)
        logger.info("Saved upload %s (%d bytes) to %s", upload_id, len(file_bytes), target)
        return upload_id, target

    def get_upload_path(self, upload_id: str) -> Path:
        matches = list(self.uploads_dir.glob(f"{upload_id}.*"))
        if not matches:
            raise FileNotFoundError(f"Upload not found: {upload_id}")
        return matches[0]

    def discard_upload(self, upload_id: str) -> None:
        for match in self.uploads_dir.glob(f"{upload_id}.*"):
            match.unlink(missing_ok=True)

    def create_dataset(
        self, schema: SensorSchema, raw_filename: str
    ) -> tuple[str, Path]:
        dataset_id = make_dataset_id(schema.asset_id)
        dataset_dir = self.root / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=False)
        src = self.get_upload_path(schema.upload_id)
        dest = dataset_dir / f"raw{src.suffix}"
        shutil.move(str(src), dest)
        return dataset_id, dataset_dir

    def _dataset_dir(self, dataset_id: str) -> Path:
        return self.root / dataset_id

    def save_schema(self, dataset_id: str, schema: SensorSchema) -> None:
        path = self._dataset_dir(dataset_id) / self.SCHEMA_FILE
        payload = asdict(schema)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_meta(self, meta: DatasetMeta) -> None:
        path = self._dataset_dir(meta.dataset_id) / self.META_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        if not meta.created_at:
            meta.created_at = _now_iso()
        path.write_text(json.dumps(asdict(meta), indent=2), encoding="utf-8")

    def get_meta(self, dataset_id: str) -> DatasetMeta | None:
        path = self._dataset_dir(dataset_id) / self.META_FILE
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return DatasetMeta(**data)

    def get_schema(self, dataset_id: str) -> SensorSchema | None:
        path = self._dataset_dir(dataset_id) / self.SCHEMA_FILE
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        mappings = [SensorMapping(**row) for row in data.pop("mappings", [])]
        return SensorSchema(mappings=mappings, **data)

    def list_datasets(self) -> list[DatasetMeta]:
        results: list[DatasetMeta] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir() or child.name == self.UPLOADS_DIR:
                continue
            meta = self.get_meta(child.name)
            if meta is not None:
                results.append(meta)
        return results

    def get_processed_path(self, dataset_id: str) -> Path:
        return self._dataset_dir(dataset_id) / self.PROCESSED_FILE

    def get_scaler_path(self, dataset_id: str) -> Path:
        return self._dataset_dir(dataset_id) / self.SCALER_FILE

    def get_weights_path(self, dataset_id: str) -> Path:
        return self._dataset_dir(dataset_id) / self.WEIGHTS_FILE

    def delete_dataset(self, dataset_id: str) -> bool:
        dataset_dir = self._dataset_dir(dataset_id)
        if not dataset_dir.exists():
            return False
        shutil.rmtree(dataset_dir)
        logger.info("Deleted dataset %s", dataset_id)
        return True


_STORE: StoreBackend | None = None


def get_store() -> StoreBackend:
    """Return the process-wide store instance (lazy-initialized)."""
    global _STORE
    if _STORE is None:
        config = _load_config()
        root = REPO_ROOT / config["ingestion"]["custom_data_dir"]
        _STORE = LocalFilesystemStore(root)
    return _STORE


def set_store(store: StoreBackend) -> None:
    """Override the global store (test-only)."""
    global _STORE
    _STORE = store
