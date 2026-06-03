"""FastAPI routes for the alert subsystem.

Mounts under the /alerts prefix:
    GET    /alerts/recent       in-memory log of dispatched events
    POST   /alerts/test         force-fires a synthetic event through all sinks
    GET    /alerts/sinks        which sinks are configured (no secrets leaked)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ingestion.alerts import AlertEvent, get_dispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertEventOut(BaseModel):
    """Serialized AlertEvent for GET /alerts/recent."""

    dataset_id: str
    unit_id: int
    cycle: int
    previous_severity: str | None
    current_severity: str
    predicted_rul: float
    threshold: float
    timestamp: str


class TestAlertIn(BaseModel):
    """Body for POST /alerts/test — operator-driven webhook smoke check."""

    dataset_id: str = Field(default="FD001")
    unit_id: int = Field(default=1, gt=0)
    cycle: int = Field(default=0, ge=0)
    previous_severity: str | None = Field(default="healthy")
    current_severity: str = Field(default="critical")
    predicted_rul: float = Field(default=12.5)
    threshold: float = Field(default=50.0)


class TestAlertOut(BaseModel):
    """Result of POST /alerts/test — per-sink success map."""

    dispatched: bool
    results: dict[str, bool]
    event: AlertEventOut


class SinksOut(BaseModel):
    """Result of GET /alerts/sinks — names only, no URLs."""

    sinks: list[str]


def _event_to_out(event: AlertEvent) -> AlertEventOut:
    """Convert an AlertEvent dataclass into its API shape."""
    return AlertEventOut(**event.to_dict())


@router.get("/recent", response_model=list[AlertEventOut])
def recent_alerts(limit: int = 50) -> list[AlertEventOut]:
    """Return the most recent dispatched alerts (newest first)."""
    if limit <= 0:
        raise HTTPException(400, "limit must be positive")
    events = get_dispatcher().log.recent(limit=limit)
    return [_event_to_out(event) for event in events]


@router.post("/test", response_model=TestAlertOut)
def test_alert(payload: TestAlertIn) -> TestAlertOut:
    """Force-fire a synthetic alert through every configured sink.

    Bypasses the transition detector and the per-key cooldown by stamping a
    fresh `current_severity` value that won't collide with real traffic. Use
    this to validate webhook config without simulating a stream.
    """
    event = AlertEvent(
        dataset_id=payload.dataset_id,
        unit_id=payload.unit_id,
        cycle=payload.cycle,
        previous_severity=payload.previous_severity,
        current_severity=payload.current_severity,
        predicted_rul=payload.predicted_rul,
        threshold=payload.threshold,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    dispatcher = get_dispatcher()
    # Bypass cooldown for manual tests by reaching into the per-key map.
    key = (event.dataset_id, event.unit_id, event.current_severity)
    dispatcher._last_fired.pop(key, None)  # noqa: SLF001 — intentional test-fire
    results = dispatcher.dispatch(event)
    return TestAlertOut(
        dispatched=bool(results),
        results=results,
        event=_event_to_out(event),
    )


@router.get("/sinks", response_model=SinksOut)
def list_sinks() -> SinksOut:
    """List the configured sink names — useful for ops to confirm setup."""
    return SinksOut(sinks=[sink.name for sink in get_dispatcher().sinks])
