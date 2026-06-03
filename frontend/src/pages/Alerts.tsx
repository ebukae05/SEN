import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Bell, Clock, WifiOff } from "lucide-react";
import { SeverityBadge } from "../components/SeverityBadge";
import { api } from "../lib/api";
import { cn } from "../lib/cn";
import { makeMockFleet } from "../lib/mock";
import type { AlertEvent, FleetEngine, Severity } from "../lib/types";

type AlertSource = "live" | "mock" | "loading";

interface DisplayAlert {
  key: string;
  dataset_id: string;
  unit_id: number;
  severity: Severity;
  previous_severity: Severity | null;
  title: string;
  detail: string;
  timestamp: string | null;
  cycles_ago: number | null;
}

export function Alerts() {
  const [events, setEvents] = useState<AlertEvent[] | null>(null);
  const [source, setSource] = useState<AlertSource>("loading");

  useEffect(() => {
    let cancelled = false;
    api
      .listRecentAlerts(50)
      .then((data) => {
        if (cancelled) return;
        setEvents(data);
        setSource("live");
      })
      .catch(() => {
        if (cancelled) return;
        setEvents(null);
        setSource("mock");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const mockFallback = useMemo(() => makeMockFleet(100), []);

  const alerts: DisplayAlert[] = useMemo(() => {
    if (source === "live" && events) {
      return events.map(eventToDisplay);
    }
    return mockFallback
      .filter((e) => e.severity !== "healthy")
      .sort((a, b) => a.predicted_rul - b.predicted_rul)
      .map(engineToDisplay);
  }, [source, events, mockFallback]);

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const warningCount = alerts.filter((a) => a.severity === "warning").length;

  return (
    <div className="relative flex-1 overflow-y-auto px-8 pt-6 pb-16">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <div className="flex flex-col items-start gap-3 pt-2">
          <span className="font-mono text-[11px] tracking-[0.35em] text-violet-glow uppercase">
            Active Alerts
          </span>
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-text">
            Threshold breaches and degradation warnings
          </h1>
          <p className="max-w-2xl text-[13px] text-text-dim">
            Severity transitions dispatched from the streaming hot path.
            Acknowledge to silence; resolve once maintenance is scheduled.
          </p>
          <div className="mt-2 flex items-center gap-2 font-mono text-[11px] text-text-faint">
            <span className="rounded-md border border-status-red/25 bg-status-red/10 px-2 py-0.5 text-status-red">
              {criticalCount} critical
            </span>
            <span className="rounded-md border border-status-amber/25 bg-status-amber/10 px-2 py-0.5 text-status-amber">
              {warningCount} warning
            </span>
            <span className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-text-dim">
              {alerts.length} total
            </span>
            {source === "mock" && (
              <span className="flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2 py-0.5 text-text-faint">
                <WifiOff className="h-3 w-3" />
                mock fallback
              </span>
            )}
          </div>
        </div>

        <div className="lift rounded-xl border border-border bg-surface/70 backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-violet-glow" />
              <span className="text-[13px] font-semibold text-text">
                Alert queue
              </span>
              <span className="font-mono text-[11px] text-text-faint">
                {source === "live" ? "newest first" : "sorted by urgency"}
              </span>
            </div>
            <button
              type="button"
              className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] text-text-dim hover:border-border-strong hover:text-text"
            >
              Acknowledge all
            </button>
          </div>
          {source === "loading" ? (
            <div className="px-4 py-10 text-center text-[12px] text-text-faint">
              Loading recent alerts…
            </div>
          ) : alerts.length === 0 ? (
            <div className="px-4 py-10 text-center text-[12px] text-text-faint">
              No alerts in the recent log.
            </div>
          ) : (
            <ul>
              {alerts.map((alert, i) => (
                <AlertRow
                  key={alert.key}
                  alert={alert}
                  divider={i < alerts.length - 1}
                />
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function eventToDisplay(event: AlertEvent): DisplayAlert {
  const prev = event.previous_severity ?? "unknown";
  const title =
    event.current_severity === "critical"
      ? `RUL ${event.predicted_rul.toFixed(0)} dropped below ${event.threshold.toFixed(0)}`
      : `Severity escalated to ${event.current_severity}`;
  const detail = `${event.dataset_id} unit ${event.unit_id} · ${prev} → ${event.current_severity} · cycle ${event.cycle}`;
  return {
    key: `${event.dataset_id}-${event.unit_id}-${event.cycle}-${event.timestamp}`,
    dataset_id: event.dataset_id,
    unit_id: event.unit_id,
    severity: event.current_severity,
    previous_severity: event.previous_severity,
    title,
    detail,
    timestamp: event.timestamp,
    cycles_ago: null,
  };
}

function engineToDisplay(engine: FleetEngine): DisplayAlert {
  const title =
    engine.severity === "critical"
      ? "RUL below safety threshold"
      : "Degradation rate exceeds nominal";
  const cycles_ago = Math.max(
    1,
    Math.round(Math.abs(engine.degradation_rate) * 4),
  );
  return {
    key: `mock-${engine.engine_id}`,
    dataset_id: "FD001",
    unit_id: engine.engine_id,
    severity: engine.severity,
    previous_severity: null,
    title,
    detail: `RUL ${engine.predicted_rul.toFixed(0)} cycles · Δ ${engine.degradation_rate.toFixed(2)} / cycle`,
    timestamp: null,
    cycles_ago,
  };
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const diffSec = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.round(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.round(diffSec / 3600)}h ago`;
  return `${Math.round(diffSec / 86400)}d ago`;
}

function AlertRow({
  alert,
  divider,
}: {
  alert: DisplayAlert;
  divider: boolean;
}) {
  const timeLabel = alert.timestamp
    ? formatRelativeTime(alert.timestamp)
    : alert.cycles_ago != null
      ? `${alert.cycles_ago}c ago`
      : "—";

  return (
    <li
      className={cn(
        "flex items-center gap-4 px-4 py-3",
        divider && "border-b border-border/60",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-md border",
          alert.severity === "critical"
            ? "border-status-red/30 bg-status-red/10"
            : "border-status-amber/30 bg-status-amber/10",
        )}
      >
        <AlertTriangle
          className={cn(
            "h-4 w-4",
            alert.severity === "critical"
              ? "text-status-red"
              : "text-status-amber",
          )}
        />
      </div>

      <Link
        to={`/engine/${alert.unit_id}`}
        className="font-mono text-[14px] font-semibold text-text hover:text-violet-glow"
      >
        #{String(alert.unit_id).padStart(3, "0")}
      </Link>

      <div className="flex min-w-0 flex-1 flex-col leading-tight">
        <span className="truncate text-[13px] text-text">{alert.title}</span>
        <span className="truncate text-[11px] text-text-faint">{alert.detail}</span>
      </div>

      <SeverityBadge severity={alert.severity} />

      <div className="flex items-center gap-1 font-mono text-[11px] text-text-faint">
        <Clock className="h-3 w-3" />
        {timeLabel}
      </div>

      <Link
        to={`/engine/${alert.unit_id}`}
        className="flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2.5 py-1 text-[11px] text-text-dim hover:border-violet/40 hover:text-violet-glow"
      >
        Inspect
        <ArrowUpRight className="h-3 w-3" />
      </Link>
    </li>
  );
}
