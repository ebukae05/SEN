import { ChevronDown, Filter, Search, TrendingDown } from "lucide-react";
import { useMemo, useState } from "react";
import type { FleetEngine } from "../lib/types";
import { cn } from "../lib/cn";
import { Sparkline } from "./Sparkline";
import { SeverityBadge } from "./SeverityBadge";

interface Props {
  engines: FleetEngine[];
}

type SortKey = "rul" | "id" | "degradation";

export function FleetTable({ engines }: Props) {
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("rul");

  const rows = useMemo(() => {
    const filtered = query
      ? engines.filter((e) => String(e.engine_id).includes(query))
      : engines;
    const sorted = [...filtered].sort((a, b) => {
      if (sortKey === "id") return a.engine_id - b.engine_id;
      if (sortKey === "degradation")
        return a.degradation_rate - b.degradation_rate;
      return a.predicted_rul - b.predicted_rul;
    });
    return sorted;
  }, [engines, query, sortKey]);

  return (
    <div className="lift rounded-xl border border-border bg-surface/70 backdrop-blur-sm">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-semibold text-text">
            Fleet Overview
          </span>
          <span className="font-mono text-[11px] text-text-faint">
            {rows.length} engines
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-2.5 h-3.5 w-3.5 -translate-y-1/2 text-text-faint" />
            <input
              type="text"
              placeholder="Search engine id..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="h-8 w-52 rounded-md border border-border bg-surface-2 pr-3 pl-8 text-[12px] text-text placeholder:text-text-faint focus:border-violet/60 focus:ring-2 focus:ring-violet/20 focus:outline-none"
            />
          </div>
          <button
            type="button"
            className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] text-text-dim hover:text-text"
          >
            <Filter className="h-3.5 w-3.5" />
            Filter
          </button>
          <button
            type="button"
            onClick={() =>
              setSortKey((k) =>
                k === "rul" ? "id" : k === "id" ? "degradation" : "rul",
              )
            }
            className="flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] text-text-dim hover:text-text"
          >
            Sort: {sortKey === "rul" ? "RUL" : sortKey === "id" ? "ID" : "Δ/cycle"}
            <ChevronDown className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-[13px]">
          <thead>
            <tr className="border-b border-border text-left text-[11px] font-medium tracking-wider text-text-faint uppercase">
              <Th className="pl-4">Engine ID</Th>
              <Th>RUL</Th>
              <Th>Trend</Th>
              <Th>Status</Th>
              <Th>Δ / cycle</Th>
              <Th>Threshold</Th>
              <Th>Last Cycle</Th>
              <Th className="pr-4 text-right">Action</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((e) => (
              <FleetRow key={e.engine_id} engine={e} />
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t border-border px-4 py-2.5">
        <span className="font-mono text-[11px] text-text-faint">
          COUNT <span className="text-text-dim">{rows.length}</span>
        </span>
        <span className="font-mono text-[11px] text-text-faint">
          1—{Math.min(rows.length, 100)} of {rows.length} · PAGE{" "}
          <span className="text-text-dim">1 of 1</span>
        </span>
      </div>
    </div>
  );
}

function Th({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <th className={cn("px-3 py-2.5 font-medium", className)}>{children}</th>
  );
}

function FleetRow({ engine: e }: { engine: FleetEngine }) {
  const rulColor =
    e.severity === "critical"
      ? "text-status-red"
      : e.severity === "warning"
        ? "text-status-amber"
        : "text-text";
  const sparkColor =
    e.severity === "critical"
      ? "#EF4444"
      : e.severity === "warning"
        ? "#F59E0B"
        : "#C084FC";
  return (
    <tr className="group border-b border-border/40 transition-colors last:border-b-0 hover:bg-violet-soft">
      <td className="py-2.5 pl-4">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[13px] text-text">
            #{String(e.engine_id).padStart(3, "0")}
          </span>
        </div>
      </td>
      <td className="px-3">
        <div className="flex items-center gap-1.5">
          <span className={cn("font-mono text-[14px] font-medium", rulColor)}>
            {e.predicted_rul.toFixed(0)}
          </span>
          <span className="text-[11px] text-text-faint">cycles</span>
          <TrendingDown
            className={cn(
              "h-3 w-3",
              e.severity === "critical"
                ? "text-status-red"
                : e.severity === "warning"
                  ? "text-status-amber"
                  : "text-text-faint",
            )}
          />
        </div>
      </td>
      <td className="px-3">
        <Sparkline data={e.trend} color={sparkColor} />
      </td>
      <td className="px-3">
        <SeverityBadge severity={e.severity} />
      </td>
      <td className="px-3">
        <span className="font-mono text-[13px] text-text-dim">
          {e.degradation_rate.toFixed(2)}
        </span>
      </td>
      <td className="px-3">
        <span className="font-mono text-[12px] text-text-faint">
          {e.threshold}
        </span>
      </td>
      <td className="px-3">
        <span className="font-mono text-[12px] text-text-dim">
          {e.last_cycle}
        </span>
      </td>
      <td className="py-2.5 pr-4 text-right">
        <button
          type="button"
          className="rounded-md border border-border bg-surface-2 px-2.5 py-1 text-[11px] text-text-dim opacity-0 transition-opacity hover:border-violet/40 hover:text-violet-glow group-hover:opacity-100"
        >
          Analyze →
        </button>
      </td>
    </tr>
  );
}
