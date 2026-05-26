import { Activity, AlertTriangle, CheckCircle2, Plane } from "lucide-react";
import type { FleetEngine } from "../lib/types";
import { cn } from "../lib/cn";

interface Props {
  engines: FleetEngine[];
}

export function FleetSummaryBar({ engines }: Props) {
  const total = engines.length;
  const critical = engines.filter((e) => e.severity === "critical").length;
  const warning = engines.filter((e) => e.severity === "warning").length;
  const healthy = engines.filter((e) => e.severity === "healthy").length;
  const avgRul =
    engines.reduce((sum, e) => sum + e.predicted_rul, 0) / (total || 1);

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
      <Stat icon={Plane} label="Fleet Size" value={total.toString()} accent="violet" />
      <Stat icon={CheckCircle2} label="Healthy" value={healthy.toString()} accent="green" />
      <Stat icon={AlertTriangle} label="Warning" value={warning.toString()} accent="amber" />
      <Stat icon={AlertTriangle} label="Critical" value={critical.toString()} accent="red" />
      <Stat icon={Activity} label="Avg RUL" value={avgRul.toFixed(1)} suffix="cycles" accent="violet" />
    </div>
  );
}

const accentMap = {
  violet: { text: "text-violet-glow", bar: "from-violet-glow/70 via-violet/40 to-transparent", glow: "rgba(168,85,247,0.18)" },
  green: { text: "text-status-green", bar: "from-status-green/70 via-status-green/30 to-transparent", glow: "rgba(34,197,94,0.18)" },
  amber: { text: "text-status-amber", bar: "from-status-amber/70 via-status-amber/30 to-transparent", glow: "rgba(245,158,11,0.18)" },
  red: { text: "text-status-red", bar: "from-status-red/80 via-status-red/30 to-transparent", glow: "rgba(239,68,68,0.22)" },
} as const;

function Stat({
  icon: Icon,
  label,
  value,
  suffix,
  accent,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  suffix?: string;
  accent: keyof typeof accentMap;
}) {
  const a = accentMap[accent];
  return (
    <div className="group lift relative overflow-hidden rounded-xl border border-border bg-surface/70 px-4 py-4 backdrop-blur-sm transition-colors hover:border-border-strong">
      <div
        className={cn(
          "pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r",
          a.bar,
        )}
      />
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
          {label}
        </span>
        <Icon className={cn("h-3.5 w-3.5 transition-transform group-hover:scale-110", a.text)} />
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span
          className="font-mono text-[32px] leading-none font-semibold tracking-tight text-text"
          style={{ textShadow: `0 0 24px ${a.glow}` }}
        >
          {value}
        </span>
        {suffix && (
          <span className="text-[11px] text-text-faint">{suffix}</span>
        )}
      </div>
    </div>
  );
}
