"""In-memory streaming buffers for real-time sensor ingestion.

Skeleton for the `POST /ingest/stream/{dataset_id}` endpoint: each call appends
one reading to a per-(dataset_id, unit_id) rolling buffer and triggers the
existing heuristic so the caller gets an immediate RUL/severity update.

Buffers are process-local — fine for a single-replica Railway deploy, will
need Redis or similar when SEN scales horizontally.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Mapping

import pandas as pd

from agents import load_config
from ingestion.alerts import maybe_dispatch
from ingestion.heuristic import HeuristicStatus, compute_engine_status

logger = logging.getLogger(__name__)


@dataclass
class StreamSnapshot:
    """Current buffer + (optional) heuristic status for one streamed unit."""

    dataset_id: str
    unit_id: int
    buffer_size: int
    window_size: int
    status: HeuristicStatus | None


_BUFFERS: dict[tuple[str, int], deque[dict[str, float]]] = {}
_LOCK = Lock()


def _buffer_capacity() -> int:
    """Return how many readings to retain per (dataset, unit) buffer.

    Four windows of headroom so the heuristic has enough history to fit a slope
    even if a few cycles get dropped or arrive late.
    """
    return int(load_config()["monitoring"]["window_size"]) * 4


def _window_size() -> int:
    """Cached pointer to the configured monitoring window size."""
    return int(load_config()["monitoring"]["window_size"])


def reset_buffers() -> None:
    """Clear all in-memory buffers. Tests use this between cases."""
    with _LOCK:
        _BUFFERS.clear()


def append_reading(
    dataset_id: str,
    unit_id: int,
    cycle: int,
    sensors: Mapping[str, float],
) -> StreamSnapshot:
    """Append one reading to the buffer for (dataset_id, unit_id).

    Returns a StreamSnapshot with the post-append buffer size and, if at least
    two readings exist for the unit, the latest heuristic status.
    """
    key = (dataset_id, unit_id)
    row = {"cycle": float(cycle), **{k: float(v) for k, v in sensors.items()}}
    with _LOCK:
        buf = _BUFFERS.setdefault(key, deque(maxlen=_buffer_capacity()))
        buf.append(row)
        size = len(buf)
        rows = list(buf)
    logger.info(
        "stream append dataset=%s unit=%d cycle=%d buffer_size=%d",
        dataset_id,
        unit_id,
        cycle,
        size,
    )
    status: HeuristicStatus | None = None
    if size >= 2:
        df = pd.DataFrame(rows)
        df.insert(0, "unit_id", unit_id)
        status = compute_engine_status(df, unit_id)
        maybe_dispatch(
            dataset_id=dataset_id,
            unit_id=unit_id,
            cycle=cycle,
            severity=status.severity,
            predicted_rul=status.predicted_rul,
            threshold=status.threshold,
        )
    return StreamSnapshot(
        dataset_id=dataset_id,
        unit_id=unit_id,
        buffer_size=size,
        window_size=_window_size(),
        status=status,
    )


def get_snapshot(dataset_id: str, unit_id: int) -> StreamSnapshot:
    """Return the current snapshot for (dataset_id, unit_id) without appending."""
    key = (dataset_id, unit_id)
    with _LOCK:
        buf = _BUFFERS.get(key)
        rows = list(buf) if buf is not None else []
    size = len(rows)
    status: HeuristicStatus | None = None
    if size >= 2:
        df = pd.DataFrame(rows)
        df.insert(0, "unit_id", unit_id)
        status = compute_engine_status(df, unit_id)
    return StreamSnapshot(
        dataset_id=dataset_id,
        unit_id=unit_id,
        buffer_size=size,
        window_size=_window_size(),
        status=status,
    )
