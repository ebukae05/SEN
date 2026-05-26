"""Ingestion subsystem for user-uploaded sensor datasets.

This package layers on top of the CDH layer (cdh/handler.py) to provide:
    - Persistent storage of uploaded datasets and their sensor schemas
    - A two-step preview/process pipeline driven by the upload wizard
    - Heuristic RUL/severity inference for non-CMAPSS data (the trained
      CNN-LSTM expects exactly 14 sensors per dataset)
"""

from __future__ import annotations

from ingestion.store import (
    DatasetMeta,
    LocalFilesystemStore,
    SensorMapping,
    SensorSchema,
    StoreBackend,
    get_store,
)

__all__ = [
    "DatasetMeta",
    "LocalFilesystemStore",
    "SensorMapping",
    "SensorSchema",
    "StoreBackend",
    "get_store",
]
