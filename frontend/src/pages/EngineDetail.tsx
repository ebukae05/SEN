import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowUpRight, Bot, Brain, FileText, Sparkles, TrendingDown, TrendingUp, Wrench } from "lucide-react";
import { LineChart } from "../components/LineChart";
import { SeverityBadge } from "../components/SeverityBadge";
import { SensorDetailModal } from "../components/SensorDetailModal";
import { Sparkline } from "../components/Sparkline";
import { buildSensorDefsFromMap, makeMockEngineDetail, makeMockFleet } from "../lib/mock";
import { useDataset } from "../lib/datasetContext";
import { cn } from "../lib/cn";
import type { EngineDetail as Engine, SensorTrend } from "../lib/types";

const ASSET_LABEL: Record<string, string> = {
  turbofan_engine: "Turbofan",
  centrifugal_compressor: "Centrifugal Compressor",
  gas_turbine: "Gas Turbine",
  steam_turbine: "Steam Turbine",
  electric_motor: "Electric Motor",
  pump: "Pump",
  gearbox: "Gearbox",
  wind_turbine_drivetrain: "Wind Turbine Drivetrain",
  conveyor_drive: "Conveyor Drive",
  crusher: "Crusher",
  generator: "Generator",
  custom: "Custom Asset",
};

export function EngineDetail() {
  const { id } = useParams<{ id: string }>();
  const engineId = Number(id);
  const { activeDataset } = useDataset();
  const isCustom = activeDataset?.source === "custom";
  const sensorMap = activeDataset?.sensor_display_names;

  const detail = useMemo(() => {
    const fleet = makeMockFleet(100);
    const engine = fleet.find((e) => e.engine_id === engineId) ?? fleet[0];
    const overrideDefs =
      isCustom && sensorMap && Object.keys(sensorMap).length > 0
        ? buildSensorDefsFromMap(sensorMap)
        : undefined;
    return makeMockEngineDetail(engine, overrideDefs);
  }, [engineId, isCustom, sensorMap]);

  const subtitle = isCustom && activeDataset
    ? `${activeDataset.asset_id} · ${ASSET_LABEL[activeDataset.asset_type] ?? activeDataset.asset_type}`
    : "FD001 · Turbofan";

  const [activeSensor, setActiveSensor] = useState<SensorTrend | null>(null);

  const sevAccent =
    detail.severity === "critical"
      ? "text-status-red"
      : detail.severity === "warning"
        ? "text-status-amber"
        : "text-status-green";
  const curveColor =
    detail.severity === "critical"
      ? "#EF4444"
      : detail.severity === "warning"
        ? "#F59E0B"
        : "#C084FC";

  return (
    <div className="relative flex-1 overflow-y-auto px-8 pt-6 pb-16">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-[12px] text-text-faint hover:text-text-dim"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to fleet
        </Link>

        <Header detail={detail} sevAccent={sevAccent} subtitle={subtitle} />

        <DegradationCard detail={detail} curveColor={curveColor} />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <DiagnosisCard detail={detail} />
          <RecommendationCard detail={detail} />
        </div>

        <SensorGrid sensors={detail.sensors} onOpen={setActiveSensor} />
      </div>
      <SensorDetailModal
        sensor={activeSensor}
        cycles={detail.last_cycle}
        onClose={() => setActiveSensor(null)}
      />
    </div>
  );
}

function Header({
  detail,
  sevAccent,
  subtitle,
}: {
  detail: Engine;
  sevAccent: string;
  subtitle: string;
}) {
  return (
    <div className="lift relative overflow-hidden rounded-2xl border border-border bg-surface/70 p-6 backdrop-blur-sm">
      <div className="pointer-events-none absolute -top-32 -right-32 h-80 w-80 rounded-full"
        style={{
          background: `radial-gradient(circle, ${detail.severity === "critical" ? "rgba(239,68,68,0.25)" : detail.severity === "warning" ? "rgba(245,158,11,0.22)" : "rgba(168,85,247,0.22)"} 0%, transparent 70%)`,
        }}
      />

      <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] tracking-[0.35em] text-violet-glow uppercase">
              Engine Detail
            </span>
            <SeverityBadge severity={detail.severity} />
          </div>
          <div className="flex items-baseline gap-3">
            <h1 className="font-mono text-[44px] leading-none font-semibold tracking-tight text-text">
              #{String(detail.engine_id).padStart(3, "0")}
            </h1>
            <span className="text-[13px] text-text-faint">{subtitle}</span>
          </div>
        </div>

        <div className="flex items-center gap-6">
          <BigStat
            label="Predicted RUL"
            value={detail.predicted_rul.toFixed(0)}
            suffix="cycles"
            accent={sevAccent}
            glow
          />
          <Divider />
          <BigStat
            label="Δ / cycle"
            value={detail.degradation_rate.toFixed(2)}
            accent={
              detail.degradation_rate < 0 ? "text-status-red" : "text-status-green"
            }
            icon={detail.degradation_rate < 0 ? TrendingDown : TrendingUp}
          />
          <Divider />
          <BigStat
            label="Last Cycle"
            value={detail.last_cycle.toString()}
          />
          <Divider />
          <BigStat
            label="Threshold"
            value={detail.threshold.toString()}
            suffix="cycles"
          />
        </div>
      </div>
    </div>
  );
}

function Divider() {
  return <div className="hidden h-12 w-px bg-border lg:block" />;
}

function BigStat({
  label,
  value,
  suffix,
  accent,
  glow,
  icon: Icon,
}: {
  label: string;
  value: string;
  suffix?: string;
  accent?: string;
  glow?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
}) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
        {label}
      </span>
      <div className="mt-1.5 flex items-baseline gap-1.5">
        <span
          className={cn(
            "font-mono text-[28px] leading-none font-semibold tracking-tight",
            accent ?? "text-text",
          )}
          style={glow ? { textShadow: "0 0 24px rgba(239,68,68,0.35)" } : undefined}
        >
          {value}
        </span>
        {suffix && <span className="text-[11px] text-text-faint">{suffix}</span>}
        {Icon && <Icon className="h-3.5 w-3.5 text-text-faint" />}
      </div>
    </div>
  );
}

function DegradationCard({ detail, curveColor }: { detail: Engine; curveColor: string }) {
  return (
    <div className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 backdrop-blur-sm">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-[radial-gradient(ellipse_600px_120px_at_20%_0%,rgba(168,85,247,0.22),transparent_70%)]" />
      <div className="relative flex items-center justify-between border-b border-border px-5 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-6 w-6 items-center justify-center rounded-md border border-violet/30 bg-violet/10 shadow-[0_0_12px_rgba(168,85,247,0.35)]">
            <Sparkles className="h-3 w-3 text-violet-glow" />
          </div>
          <span className="text-[13px] font-semibold text-text">RUL Degradation Curve</span>
          <span className="font-mono text-[11px] text-text-faint">
            {detail.last_cycle} cycles observed
          </span>
        </div>
        <span className="font-mono text-[10px] text-text-faint">
          CNN-LSTM · 30-cycle window
        </span>
      </div>
      <div className="relative px-2 py-3">
        <LineChart
          data={detail.rul_history}
          height={260}
          color={curveColor}
          threshold={detail.threshold}
          yLabel="RUL (cycles)"
        />
      </div>
    </div>
  );
}

function DiagnosisCard({ detail }: { detail: Engine }) {
  return (
    <div className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 p-5 backdrop-blur-sm lg:col-span-2">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-border bg-surface-2">
          <Brain className="h-3.5 w-3.5 text-violet-glow" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold text-text">Diagnostic Agent</span>
          <span className="font-mono text-[10px] text-text-faint">Root-cause analysis · Gemini 2.5 Flash</span>
        </div>
      </div>
      <p className="mt-4 text-[14px] leading-relaxed text-text">{detail.diagnosis}</p>
      <div className="mt-5">
        <span className="text-[10px] font-medium tracking-wider text-text-faint uppercase">
          Top contributing sensors
        </span>
        <div className="mt-2 flex flex-wrap gap-2">
          {detail.top_contributors.map((c) => (
            <span
              key={c}
              className="rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-[11px] text-text-dim"
            >
              {c}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

function RecommendationCard({ detail }: { detail: Engine }) {
  return (
    <div className="lift relative flex flex-col overflow-hidden rounded-xl border border-violet/25 bg-gradient-to-br from-violet/10 to-transparent p-5 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-md border border-violet/30 bg-violet/10">
          <Wrench className="h-3.5 w-3.5 text-violet-glow" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold text-text">Maintenance Advisor</span>
          <span className="font-mono text-[10px] text-text-faint">Action plan</span>
        </div>
      </div>
      <p className="mt-4 flex-1 text-[14px] leading-relaxed text-text">{detail.recommendation}</p>
      <div className="mt-5 flex items-center gap-2">
        <button
          type="button"
          className="flex flex-1 items-center justify-center gap-1.5 rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-3 py-2 text-[12px] font-medium text-white shadow-[0_0_20px_rgba(168,85,247,0.2)] hover:from-violet/35 hover:to-violet/15"
        >
          <FileText className="h-3.5 w-3.5" />
          Generate PDF Report
        </button>
        <button
          type="button"
          className="flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-3 py-2 text-[12px] text-text-dim hover:text-text"
        >
          <Bot className="h-3.5 w-3.5" />
          Re-run
        </button>
      </div>
    </div>
  );
}

function SensorGrid({
  sensors,
  onOpen,
}: {
  sensors: SensorTrend[];
  onOpen: (s: SensorTrend) => void;
}) {
  return (
    <div className="lift rounded-xl border border-border bg-surface/70 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border px-5 py-3">
        <div className="flex items-center gap-2.5">
          <span className="text-[13px] font-semibold text-text">Sensor Trends</span>
          <span className="font-mono text-[11px] text-text-faint">{sensors.length} active sensors</span>
        </div>
        <span className="font-mono text-[10px] text-text-faint">Click any sensor for full detail</span>
      </div>
      <div className="grid grid-cols-1 gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
        {sensors.map((s) => (
          <SensorCard key={s.name} sensor={s} onOpen={() => onOpen(s)} />
        ))}
      </div>
    </div>
  );
}

function SensorCard({
  sensor,
  onOpen,
}: {
  sensor: SensorTrend;
  onOpen: () => void;
}) {
  const trending = sensor.delta_pct > 0;
  const alarming = Math.abs(sensor.delta_pct) > 8;
  const color = alarming ? "#F59E0B" : "#C084FC";
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group bg-surface px-4 py-4 text-left transition-colors hover:bg-surface-hover focus:bg-surface-hover focus:outline-none"
    >
      <div className="flex items-start justify-between">
        <div className="flex flex-col">
          <span className="font-mono text-[11px] text-text-faint">{sensor.name}</span>
          <span className="mt-0.5 text-[13px] font-medium text-text group-hover:text-violet-glow">
            {sensor.label}
          </span>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1 font-mono text-[11px]",
            alarming ? "text-status-amber" : "text-text-dim",
          )}
        >
          {trending ? <ArrowUpRight className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
          {sensor.delta_pct > 0 ? "+" : ""}
          {sensor.delta_pct.toFixed(1)}%
        </span>
      </div>
      <div className="mt-3">
        <Sparkline data={sensor.values} width={260} height={44} color={color} />
      </div>
    </button>
  );
}
