"""Alert dispatch for severity transitions on the streaming hot path.

Responsibilities:
    - Detect when a (dataset_id, unit_id) crosses into / out of a severity
      that the operator has configured as alertable.
    - Format a structured AlertEvent and dispatch it to every configured sink
      (Slack webhook, generic JSON webhook, in-memory log).
    - Enforce a cooldown per (dataset_id, unit_id, severity) so a flapping
      reading doesn't spam the channel.

Sinks are best-effort: a failing webhook logs a warning but never raises into
the streaming request. The recent-events log is always populated so the
frontend `/alerts` page has a working source of truth even when no webhook is
configured.
"""

from __future__ import annotations

import logging
import os
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Protocol

import httpx

from agents import load_config

logger = logging.getLogger(__name__)


@dataclass
class AlertEvent:
    """One severity transition observed on the streaming hot path."""

    dataset_id: str
    unit_id: int
    cycle: int
    previous_severity: str | None
    current_severity: str
    predicted_rul: float
    threshold: float
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for JSON serialization."""
        return asdict(self)

    def slack_blocks(self) -> dict[str, Any]:
        """Render the event as a Slack message payload (blocks API)."""
        emoji = {
            "critical": ":rotating_light:",
            "watch": ":warning:",
            "healthy": ":white_check_mark:",
        }.get(self.current_severity, ":bell:")
        prev = self.previous_severity or "unknown"
        return {
            "text": (
                f"{emoji} SEN alert — {self.dataset_id} unit {self.unit_id}: "
                f"{prev} → {self.current_severity} "
                f"(RUL {self.predicted_rul:.1f} / threshold {self.threshold:.1f})"
            )
        }


class AlertSink(Protocol):
    """Anything that can receive an AlertEvent."""

    name: str

    def send(self, event: AlertEvent) -> bool:
        """Deliver an event. Return True on success, False on failure."""
        ...


class LoggingSink:
    """Always-on sink that records events to the Python logger."""

    name = "logging"

    def send(self, event: AlertEvent) -> bool:
        """Log the event at WARNING level for critical, INFO otherwise."""
        level = logging.WARNING if event.current_severity == "critical" else logging.INFO
        logger.log(
            level,
            "ALERT %s/%d cycle=%d %s->%s rul=%.1f",
            event.dataset_id,
            event.unit_id,
            event.cycle,
            event.previous_severity,
            event.current_severity,
            event.predicted_rul,
        )
        return True


class SlackWebhookSink:
    """Post to a Slack incoming webhook URL."""

    name = "slack"

    def __init__(self, webhook_url: str, timeout: float = 5.0) -> None:
        """Bind the sink to a webhook URL and HTTP timeout."""
        self._url = webhook_url
        self._timeout = timeout

    def send(self, event: AlertEvent) -> bool:
        """POST a Slack message; swallow network errors and return False."""
        try:
            response = httpx.post(
                self._url, json=event.slack_blocks(), timeout=self._timeout
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Slack webhook failed: %s", exc)
            return False


class GenericWebhookSink:
    """POST the full event dict to an arbitrary webhook endpoint."""

    name = "webhook"

    def __init__(self, webhook_url: str, timeout: float = 5.0) -> None:
        """Bind the sink to a webhook URL and HTTP timeout."""
        self._url = webhook_url
        self._timeout = timeout

    def send(self, event: AlertEvent) -> bool:
        """POST the JSON event dict; swallow network errors and return False."""
        try:
            response = httpx.post(
                self._url, json=event.to_dict(), timeout=self._timeout
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as exc:
            logger.warning("Generic webhook failed: %s", exc)
            return False


class RecentEventsLog:
    """Thread-safe bounded log of dispatched events for the frontend feed."""

    def __init__(self, capacity: int) -> None:
        """Allocate the ring buffer."""
        self._events: deque[AlertEvent] = deque(maxlen=capacity)
        self._lock = Lock()

    def record(self, event: AlertEvent) -> None:
        """Append an event to the log."""
        with self._lock:
            self._events.append(event)

    def recent(self, limit: int | None = None) -> list[AlertEvent]:
        """Return events newest-first, optionally truncated to `limit`."""
        with self._lock:
            snapshot = list(self._events)
        snapshot.reverse()
        if limit is not None:
            return snapshot[:limit]
        return snapshot

    def clear(self) -> None:
        """Drop every recorded event. Tests reset state via this."""
        with self._lock:
            self._events.clear()


class AlertDispatcher:
    """Routes AlertEvents to every configured sink with per-key cooldown."""

    def __init__(
        self,
        sinks: list[AlertSink],
        log: RecentEventsLog,
        cooldown_seconds: float,
    ) -> None:
        """Bind sinks, the recent-events log, and the cooldown window."""
        self._sinks = sinks
        self._log = log
        self._cooldown = float(cooldown_seconds)
        self._last_fired: dict[tuple[str, int, str], float] = {}
        self._lock = Lock()

    @property
    def sinks(self) -> list[AlertSink]:
        """Expose the configured sinks (for diagnostics + tests)."""
        return list(self._sinks)

    @property
    def log(self) -> RecentEventsLog:
        """Expose the recent-events log (read-only by convention)."""
        return self._log

    def reset(self) -> None:
        """Forget cooldown state and clear the log. Tests use this."""
        with self._lock:
            self._last_fired.clear()
        self._log.clear()

    def _is_in_cooldown(self, key: tuple[str, int, str], now: float) -> bool:
        """Return True if `key` fired within the cooldown window."""
        last = self._last_fired.get(key)
        return last is not None and (now - last) < self._cooldown

    def dispatch(self, event: AlertEvent) -> dict[str, bool]:
        """Send `event` to all sinks unless suppressed by cooldown.

        Returns a `{sink_name: success}` map. An empty dict means the event
        was suppressed by cooldown.
        """
        key = (event.dataset_id, event.unit_id, event.current_severity)
        now = time.monotonic()
        with self._lock:
            if self._is_in_cooldown(key, now):
                logger.info(
                    "Alert suppressed by cooldown: %s/%d %s",
                    event.dataset_id,
                    event.unit_id,
                    event.current_severity,
                )
                return {}
            self._last_fired[key] = now
        self._log.record(event)
        return {sink.name: sink.send(event) for sink in self._sinks}


class SeverityTransitionDetector:
    """Tracks the last-seen severity per (dataset_id, unit_id)."""

    def __init__(self) -> None:
        """Allocate the tracking map and its lock."""
        self._last: dict[tuple[str, int], str] = {}
        self._lock = Lock()

    def observe(
        self, dataset_id: str, unit_id: int, severity: str
    ) -> str | None:
        """Record the latest severity and return the previous one (or None)."""
        key = (dataset_id, unit_id)
        with self._lock:
            previous = self._last.get(key)
            self._last[key] = severity
        return previous

    def reset(self) -> None:
        """Drop all tracked severities. Tests use this."""
        with self._lock:
            self._last.clear()


def _alerts_config() -> dict[str, Any]:
    """Return the `alerts` block from config.yaml, defaulting to disabled."""
    config = load_config()
    return config.get("alerts") or {"enabled": False}


def _build_sinks(cfg: dict[str, Any]) -> list[AlertSink]:
    """Construct the sink list from the alerts config + environment."""
    sinks: list[AlertSink] = [LoggingSink()]
    channels = cfg.get("channels") or {}

    slack_env = channels.get("slack_webhook_env")
    if slack_env:
        slack_url = os.environ.get(slack_env)
        if slack_url:
            sinks.append(SlackWebhookSink(slack_url))
        else:
            logger.info(
                "Slack webhook env var %s not set; sink disabled", slack_env
            )

    webhook_env = channels.get("generic_webhook_env")
    if webhook_env:
        webhook_url = os.environ.get(webhook_env)
        if webhook_url:
            sinks.append(GenericWebhookSink(webhook_url))
        else:
            logger.info(
                "Generic webhook env var %s not set; sink disabled", webhook_env
            )

    return sinks


_DISPATCHER: AlertDispatcher | None = None
_DETECTOR = SeverityTransitionDetector()
_DISPATCHER_LOCK = Lock()


def get_dispatcher() -> AlertDispatcher:
    """Return the process-wide AlertDispatcher, building it on first use."""
    global _DISPATCHER
    with _DISPATCHER_LOCK:
        if _DISPATCHER is None:
            cfg = _alerts_config()
            log_capacity = int(cfg.get("recent_log_capacity", 100))
            cooldown = float(cfg.get("cooldown_seconds", 300))
            _DISPATCHER = AlertDispatcher(
                sinks=_build_sinks(cfg),
                log=RecentEventsLog(log_capacity),
                cooldown_seconds=cooldown,
            )
        return _DISPATCHER


def get_detector() -> SeverityTransitionDetector:
    """Return the process-wide severity-transition detector."""
    return _DETECTOR


def reset_for_tests() -> None:
    """Tear down dispatcher + detector state. For tests only."""
    global _DISPATCHER
    with _DISPATCHER_LOCK:
        _DISPATCHER = None
    _DETECTOR.reset()


def maybe_dispatch(
    dataset_id: str,
    unit_id: int,
    cycle: int,
    severity: str,
    predicted_rul: float,
    threshold: float,
) -> AlertEvent | None:
    """Fire an alert if this reading transitions into a configured severity.

    Returns the dispatched AlertEvent, or None if alerts are disabled, the
    severity isn't in the configured `fire_on` list, or the severity didn't
    change since the last reading for this (dataset_id, unit_id).
    """
    cfg = _alerts_config()
    if not cfg.get("enabled", False):
        return None
    fire_on = set(cfg.get("fire_on") or [])
    if severity not in fire_on:
        _DETECTOR.observe(dataset_id, unit_id, severity)
        return None
    previous = _DETECTOR.observe(dataset_id, unit_id, severity)
    if previous == severity:
        return None
    event = AlertEvent(
        dataset_id=dataset_id,
        unit_id=unit_id,
        cycle=cycle,
        previous_severity=previous,
        current_severity=severity,
        predicted_rul=predicted_rul,
        threshold=threshold,
    )
    get_dispatcher().dispatch(event)
    return event
