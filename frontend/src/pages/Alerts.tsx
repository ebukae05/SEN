import { useMemo } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Bell, Clock } from "lucide-react";
import { SeverityBadge } from "../components/SeverityBadge";
import { Sparkline } from "../components/Sparkline";
import { makeMockFleet } from "../lib/mock";
import { cn } from "../lib/cn";
import type { FleetEngine } from "../lib/types";

export function Alerts() {
  const engines = useMemo(() => makeMockFleet(100), []);
  const alerts = useMemo(
    () =>
      engines
        .filter((e) => e.severity !== "healthy")
        .sort((a, b) => a.predicted_rul - b.predicted_rul),
    [engines],
  );

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
            Engines whose predicted RUL has crossed an operating threshold or
            whose degradation rate signals impending failure. Acknowledge to
            silence; resolve once maintenance is scheduled.
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
                sorted by urgency
              </span>
            </div>
            <button
              type="button"
              className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] text-text-dim hover:border-border-strong hover:text-text"
            >
              Acknowledge all
            </button>
          </div>
          <ul>
            {alerts.map((engine, i) => (
              <AlertRow
                key={engine.engine_id}
                engine={engine}
                divider={i < alerts.length - 1}
              />
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function AlertRow({
  engine,
  divider,
}: {
  engine: FleetEngine;
  divider: boolean;
}) {
  const color =
    engine.severity === "critical" ? "#EF4444" : "#F59E0B";
  const title =
    engine.severity === "critical"
      ? "RUL below safety threshold"
      : "Degradation rate exceeds nominal";

  const cyclesAgo = Math.max(1, Math.round(Math.abs(engine.degradation_rate) * 4));

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
          engine.severity === "critical"
            ? "border-status-red/30 bg-status-red/10"
            : "border-status-amber/30 bg-status-amber/10",
        )}
      >
        <AlertTriangle
          className={cn(
            "h-4 w-4",
            engine.severity === "critical"
              ? "text-status-red"
              : "text-status-amber",
          )}
        />
      </div>

      <Link
        to={`/engine/${engine.engine_id}`}
        className="font-mono text-[14px] font-semibold text-text hover:text-violet-glow"
      >
        #{String(engine.engine_id).padStart(3, "0")}
      </Link>

      <div className="flex min-w-0 flex-1 flex-col leading-tight">
        <span className="truncate text-[13px] text-text">{title}</span>
        <span className="text-[11px] text-text-faint">
          RUL {engine.predicted_rul.toFixed(0)} cycles · Δ{" "}
          {engine.degradation_rate.toFixed(2)} / cycle
        </span>
      </div>

      <Sparkline data={engine.trend} color={color} width={64} height={20} />

      <SeverityBadge severity={engine.severity} />

      <div className="flex items-center gap-1 font-mono text-[11px] text-text-faint">
        <Clock className="h-3 w-3" />
        {cyclesAgo}c ago
      </div>

      <Link
        to={`/engine/${engine.engine_id}`}
        className="flex items-center gap-1 rounded-md border border-border bg-surface-2 px-2.5 py-1 text-[11px] text-text-dim hover:border-violet/40 hover:text-violet-glow"
      >
        Inspect
        <ArrowUpRight className="h-3 w-3" />
      </Link>
    </li>
  );
}
