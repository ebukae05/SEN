import { useMemo } from "react";
import { LineChart, TrendingDown, TrendingUp } from "lucide-react";
import { Sparkline } from "../components/Sparkline";
import { makeMockFleet } from "../lib/mock";

export function Trends() {
  const engines = useMemo(() => makeMockFleet(100), []);

  const avgRul = engines.reduce((s, e) => s + e.predicted_rul, 0) / engines.length;
  const avgDegradation =
    engines.reduce((s, e) => s + e.degradation_rate, 0) / engines.length;
  const criticalShare =
    engines.filter((e) => e.severity === "critical").length / engines.length;

  const fleetTrend = useMemo(() => {
    const points = 24;
    return Array.from({ length: points }, (_, i) => {
      const sum = engines.reduce((acc, e) => acc + e.trend[i], 0);
      return sum / engines.length;
    });
  }, [engines]);

  return (
    <div className="relative flex-1 overflow-y-auto px-8 pt-6 pb-16">
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        <div className="flex flex-col items-start gap-3 pt-2">
          <span className="font-mono text-[11px] tracking-[0.35em] text-violet-glow uppercase">
            Fleet Trends
          </span>
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-text">
            Aggregate degradation and RUL evolution
          </h1>
          <p className="max-w-2xl text-[13px] text-text-dim">
            Long-horizon view of how the fleet is aging. Drill into per-cohort
            breakdowns, operating-condition correlations, and predicted failure
            density windows.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          <KpiCard
            label="Avg fleet RUL"
            value={avgRul.toFixed(0)}
            suffix="cycles"
            tone="violet"
            trend={fleetTrend}
          />
          <KpiCard
            label="Avg Δ / cycle"
            value={avgDegradation.toFixed(2)}
            suffix="rate"
            tone="red"
            icon={TrendingDown}
          />
          <KpiCard
            label="Critical share"
            value={(criticalShare * 100).toFixed(1)}
            suffix="%"
            tone="amber"
            icon={TrendingUp}
          />
        </div>

        <Placeholder />
      </div>
    </div>
  );
}

function KpiCard({
  label,
  value,
  suffix,
  tone,
  trend,
  icon: Icon,
}: {
  label: string;
  value: string;
  suffix: string;
  tone: "violet" | "red" | "amber";
  trend?: number[];
  icon?: React.ComponentType<{ className?: string }>;
}) {
  const toneColors = {
    violet: { color: "#C084FC", text: "text-violet-glow" },
    red: { color: "#EF4444", text: "text-status-red" },
    amber: { color: "#F59E0B", text: "text-status-amber" },
  } as const;
  const t = toneColors[tone];

  return (
    <div className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 p-4 backdrop-blur-sm">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium tracking-wider text-text-faint uppercase">
          {label}
        </span>
        {Icon && <Icon className={`h-3.5 w-3.5 ${t.text}`} />}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="font-mono text-[26px] font-semibold tracking-tight text-text">
          {value}
        </span>
        <span className="text-[11px] text-text-faint">{suffix}</span>
      </div>
      {trend && (
        <div className="mt-3">
          <Sparkline data={trend} color={t.color} width={240} height={36} />
        </div>
      )}
    </div>
  );
}

function Placeholder() {
  return (
    <div className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 p-8 backdrop-blur-sm">
      <div className="flex items-start gap-4">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-violet/30 bg-violet/10">
          <LineChart className="h-5 w-5 text-violet-glow" />
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-[16px] font-semibold tracking-tight text-text">
            Deeper trend analytics in development
          </h2>
          <p className="max-w-xl text-[13px] leading-relaxed text-text-dim">
            Upcoming: per-cohort RUL distributions, sensor-correlation
            heatmaps, operating-condition slices (FD001–FD004), and
            time-to-failure density windows. Wired into the Diagnostic agent
            stream once the backend exposes aggregate endpoints.
          </p>
          <ul className="mt-2 flex flex-col gap-1.5 text-[12px] text-text-dim">
            <PlaceholderItem>RUL distribution by operating condition</PlaceholderItem>
            <PlaceholderItem>Sensor-pair correlation matrix</PlaceholderItem>
            <PlaceholderItem>Rolling 30-cycle failure density</PlaceholderItem>
            <PlaceholderItem>Cohort decay curves vs nominal</PlaceholderItem>
          </ul>
        </div>
      </div>
    </div>
  );
}

function PlaceholderItem({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-center gap-2">
      <span className="h-1 w-1 rounded-full bg-violet-glow" />
      <span>{children}</span>
    </li>
  );
}
