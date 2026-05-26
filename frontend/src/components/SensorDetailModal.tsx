import { ArrowDownRight, ArrowUpRight, BookOpen, Info } from "lucide-react";
import { Modal } from "./Modal";
import { SensorChart } from "./SensorChart";
import type { SensorTrend } from "../lib/types";
import { cn } from "../lib/cn";

interface Props {
  sensor: SensorTrend | null;
  cycles: number;
  onClose: () => void;
}

export function SensorDetailModal({ sensor, cycles, onClose }: Props) {
  return (
    <Modal open={!!sensor} onClose={onClose}>
      {sensor && <Content sensor={sensor} cycles={cycles} />}
    </Modal>
  );
}

function Content({ sensor, cycles }: { sensor: SensorTrend; cycles: number }) {
  const trending = sensor.delta_pct > 0;
  const alarming = Math.abs(sensor.delta_pct) > 8;
  const slopePerCycle = sensor.regression.slope;
  const slopePer100 = slopePerCycle * 100;

  return (
    <div>
      <div className="relative overflow-hidden border-b border-border px-6 pt-6 pb-5">
        <div className="pointer-events-none absolute -top-20 -right-20 h-60 w-60 rounded-full bg-[radial-gradient(circle,rgba(168,85,247,0.25),transparent_70%)]" />
        <div className="relative flex items-start justify-between gap-6">
          <div className="flex flex-col">
            <span className="font-mono text-[10px] tracking-[0.35em] text-violet-glow uppercase">
              Sensor Detail
            </span>
            <div className="mt-1 flex items-baseline gap-3">
              <span className="font-mono text-[14px] text-text-faint">
                {sensor.name}
              </span>
              <h2 className="text-[22px] font-semibold tracking-tight text-text">
                {sensor.label}
              </h2>
            </div>
            <span className="mt-1 font-mono text-[11px] text-text-faint">
              {cycles} cycles observed · normalized 0–1
            </span>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
              Δ Drift
            </span>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 font-mono text-[28px] leading-none font-semibold",
                alarming ? "text-status-amber" : "text-text",
              )}
              style={{
                textShadow: alarming
                  ? "0 0 24px rgba(245,158,11,0.4)"
                  : "0 0 24px rgba(168,85,247,0.25)",
              }}
            >
              {trending ? (
                <ArrowUpRight className="h-5 w-5" />
              ) : (
                <ArrowDownRight className="h-5 w-5" />
              )}
              {sensor.delta_pct > 0 ? "+" : ""}
              {sensor.delta_pct.toFixed(2)}%
            </span>
            <span className="font-mono text-[10px] text-text-faint">
              baseline avg {sensor.baseline.toFixed(3)}
            </span>
          </div>
        </div>
      </div>

      <div className="px-6 py-5">
        <SensorChart
          raw={sensor.values}
          regression={sensor.regression}
          fleet={sensor.fleet_avg}
          height={300}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 border-t border-border px-6 py-5 md:grid-cols-3">
        <Stat
          label="Slope"
          value={`${slopePerCycle >= 0 ? "+" : ""}${slopePer100.toFixed(3)}`}
          suffix="per 100 cycles"
        />
        <Stat
          label="vs Fleet"
          value={`${(
            ((sensor.values[sensor.values.length - 1] -
              sensor.fleet_avg[sensor.fleet_avg.length - 1]) /
              Math.abs(sensor.fleet_avg[sensor.fleet_avg.length - 1] || 1)) *
            100
          ).toFixed(1)}%`}
          suffix="above fleet avg"
        />
        <Stat
          label="Status"
          value={alarming ? "Drifting" : "Nominal"}
          suffix={alarming ? "outside fleet band" : "within fleet band"}
          accent={alarming ? "text-status-amber" : "text-status-green"}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 border-t border-border px-6 py-5 md:grid-cols-2">
        <ExplainCard
          icon={BookOpen}
          tag="What it measures"
          body={sensor.description}
        />
        <ExplainCard
          icon={Info}
          tag="Why the drift matters"
          body={sensor.why_it_matters}
          violet
        />
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  suffix,
  accent,
}: {
  label: string;
  value: string;
  suffix?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-2/60 px-3.5 py-3">
      <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
        {label}
      </span>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span
          className={cn(
            "font-mono text-[18px] font-semibold tracking-tight",
            accent ?? "text-text",
          )}
        >
          {value}
        </span>
      </div>
      {suffix && (
        <span className="mt-0.5 block text-[11px] text-text-faint">{suffix}</span>
      )}
    </div>
  );
}

function ExplainCard({
  icon: Icon,
  tag,
  body,
  violet,
}: {
  icon: React.ComponentType<{ className?: string }>;
  tag: string;
  body: string;
  violet?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3.5",
        violet
          ? "border-violet/25 bg-gradient-to-br from-violet/10 to-transparent"
          : "border-border bg-surface-2/60",
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className={cn("h-3.5 w-3.5", violet ? "text-violet-glow" : "text-text-faint")} />
        <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
          {tag}
        </span>
      </div>
      <p className="mt-2 text-[13px] leading-relaxed text-text">{body}</p>
    </div>
  );
}
