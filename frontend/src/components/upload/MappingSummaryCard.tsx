import type { SensorMapping, SensorTypeTag } from "../../lib/types";

interface MappingSummaryCardProps {
  assetId: string;
  industry: string;
  assetType: string;
  engineCount: number | string;
  mappings: SensorMapping[];
  hasRul: boolean;
}

function sensorBreakdown(mappings: SensorMapping[]) {
  const breakdown: Partial<Record<SensorTypeTag, number>> = {};
  for (const m of mappings) {
    if (m.role !== "sensor") continue;
    breakdown[m.type_tag] = (breakdown[m.type_tag] ?? 0) + 1;
  }
  return Object.entries(breakdown).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0));
}

export function MappingSummaryCard({
  assetId,
  industry,
  assetType,
  engineCount,
  mappings,
  hasRul,
}: MappingSummaryCardProps) {
  const sensorCount = mappings.filter((m) => m.role === "sensor").length;
  const breakdown = sensorBreakdown(mappings);

  return (
    <section className="space-y-4 rounded-lg border border-border bg-surface px-5 py-5">
      <header className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-[14px] font-semibold text-text">{assetId}</h3>
          <p className="font-mono text-[11px] text-text-faint">
            {industry} · {assetType}
          </p>
        </div>
        <span className="rounded-full border border-violet/40 bg-violet/10 px-2.5 py-0.5 font-mono text-[10px] text-violet-glow">
          {hasRul ? "labeled" : "unsupervised"}
        </span>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Stat label="Engines" value={String(engineCount)} />
        <Stat label="Sensors" value={String(sensorCount)} />
        <Stat
          label="RUL Source"
          value={hasRul ? "User" : "Heuristic"}
        />
      </div>

      <div>
        <h4 className="mb-2 text-[10px] uppercase tracking-wider text-text-faint">
          Sensor breakdown
        </h4>
        <ul className="flex flex-wrap gap-1.5">
          {breakdown.map(([tag, count]) => (
            <li
              key={tag}
              className="rounded-md border border-border bg-bg/40 px-2 py-1 font-mono text-[11px] text-text-dim"
            >
              <span className="text-text">{tag}</span>
              <span className="ml-1.5 text-text-faint">×{count}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg/40 px-3 py-2.5">
      <span className="block text-[10px] uppercase tracking-wider text-text-faint">
        {label}
      </span>
      <span className="font-mono text-[14px] text-text">{value}</span>
    </div>
  );
}
