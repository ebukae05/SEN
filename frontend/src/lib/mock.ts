import type { AgentEvent, AgentName, EngineDetail, FleetEngine, SensorTrend, Severity } from "./types";

function seededRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 2 ** 32;
    return state / 2 ** 32;
  };
}

function severityFromRul(rul: number, threshold: number): Severity {
  if (rul < threshold * 0.6) return "critical";
  if (rul < threshold * 1.3) return "warning";
  return "healthy";
}

export function makeMockFleet(count = 100): FleetEngine[] {
  const rand = seededRandom(7);
  const threshold = 30;
  const engines: FleetEngine[] = [];
  for (let i = 1; i <= count; i++) {
    const roll = rand();
    let rul: number;
    if (roll < 0.12) rul = Math.round(4 + rand() * 14);
    else if (roll < 0.32) rul = Math.round(20 + rand() * 18);
    else rul = Math.round(45 + rand() * 95);

    const points = 24;
    const startRul = rul + 18 + rand() * 12;
    const trend = Array.from({ length: points }, (_, k) => {
      const progress = k / (points - 1);
      const base = startRul - (startRul - rul) * progress;
      const noise = (rand() - 0.5) * 1.6;
      return Math.max(0, base + noise);
    });

    const degradation_rate = -(0.3 + rand() * 1.5);
    engines.push({
      engine_id: i,
      predicted_rul: rul,
      severity: severityFromRul(rul, threshold),
      alert: rul < threshold,
      threshold,
      trend,
      degradation_rate,
      last_cycle: 120 + Math.round(rand() * 80),
    });
  }
  return engines.sort((a, b) => a.predicted_rul - b.predicted_rul);
}

interface SensorDef {
  name: string;
  label: string;
  drift: number;
  description: string;
  why_it_matters: string;
}

const SENSOR_DEFS: SensorDef[] = [
  {
    name: "s2",
    label: "LPC Outlet Temp",
    drift: 0.85,
    description:
      "Temperature of air exiting the Low Pressure Compressor, measured before it enters the high-pressure stages.",
    why_it_matters:
      "Rising LPC outlet temperatures indicate the compressor is working harder to achieve the same pressure ratio — an early signal of fan or LPC blade fouling, tip-clearance loss, or upstream airflow restriction.",
  },
  {
    name: "s3",
    label: "HPC Outlet Temp",
    drift: 0.92,
    description:
      "Temperature of compressed air at the High Pressure Compressor exit, just before fuel injection in the combustor.",
    why_it_matters:
      "The single most reliable HPC degradation marker. Sustained upward drift signals blade erosion, seal wear, or thermal-barrier coating breakdown — the dominant failure mode in CMAPSS FD001.",
  },
  {
    name: "s4",
    label: "LPT Outlet Temp",
    drift: 0.78,
    description:
      "Temperature at the Low Pressure Turbine exit. The LPT extracts the residual energy from combustion gases to drive the fan.",
    why_it_matters:
      "Higher LPT outlet temps mean less energy was extracted upstream — typically a sign of HPC inefficiency or turbine blade wear. Sustained drift accelerates downstream thermal stress.",
  },
  {
    name: "s7",
    label: "HPC Outlet Pressure",
    drift: -0.65,
    description:
      "Static pressure at the High Pressure Compressor exit, the highest pressure point in the gas path.",
    why_it_matters:
      "Declining HPC pressure with constant fuel flow indicates the compressor is losing the ability to compress air efficiently — a direct measure of HPC stage degradation.",
  },
  {
    name: "s11",
    label: "Fan Speed",
    drift: -0.55,
    description:
      "Rotational speed of the front fan (N1), the largest rotating component and the primary source of bypass thrust.",
    why_it_matters:
      "Fan speed drops at constant throttle reveal blade-tip erosion, bearing drag, or increased shaft friction. In FD003/FD004 this is the dominant degradation signal.",
  },
  {
    name: "s12",
    label: "Core Speed",
    drift: 0.7,
    description:
      "Rotational speed of the engine core (N2) — the high-pressure compressor and turbine spool.",
    why_it_matters:
      "When core speed rises to maintain output, the control system is compensating for lost efficiency elsewhere in the gas path. A leading indicator that other sensors are about to drift.",
  },
];

function linregress(values: number[]): { slope: number; intercept: number } {
  const n = values.length;
  if (n < 2) return { slope: 0, intercept: values[0] ?? 0 };
  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumX2 = 0;
  for (let i = 0; i < n; i++) {
    sumX += i;
    sumY += values[i];
    sumXY += i * values[i];
    sumX2 += i * i;
  }
  const denom = n * sumX2 - sumX * sumX;
  const slope = denom === 0 ? 0 : (n * sumXY - sumX * sumY) / denom;
  const intercept = (sumY - slope * sumX) / n;
  return { slope, intercept };
}

function smooth(series: number[], window = 5): number[] {
  if (series.length < window) return series;
  const out: number[] = [];
  const half = Math.floor(window / 2);
  for (let i = 0; i < series.length; i++) {
    let sum = 0;
    let count = 0;
    for (let j = Math.max(0, i - half); j <= Math.min(series.length - 1, i + half); j++) {
      sum += series[j];
      count++;
    }
    out.push(sum / count);
  }
  return out;
}

export function makeMockEngineDetail(engine: FleetEngine): EngineDetail {
  const rand = seededRandom(engine.engine_id * 17 + 3);
  const cycles = engine.last_cycle;
  const startRul = 130;
  const rul_history = Array.from({ length: cycles }, (_, k) => {
    const t = k / (cycles - 1);
    const stable = startRul - 6 * t;
    const decline = startRul - (startRul - engine.predicted_rul) * Math.pow(t, 2.2);
    const blend = 1 / (1 + Math.exp(-12 * (t - 0.4)));
    const value = stable * (1 - blend) + decline * blend;
    return Math.max(0, value + (rand() - 0.5) * 1.2);
  });

  const severityScale =
    engine.severity === "critical" ? 1.0 : engine.severity === "warning" ? 0.55 : 0.25;

  const sensors: SensorTrend[] = SENSOR_DEFS.map((def) => {
    const raw = Array.from({ length: cycles }, (_, k) => {
      const t = k / (cycles - 1);
      const eased = Math.pow(t, 1.4);
      const noise = (rand() - 0.5) * 0.012;
      return 0.5 + def.drift * eased * 0.09 * severityScale + noise;
    });
    const values = smooth(raw, 7);
    const fleet_avg = Array.from({ length: cycles }, (_, k) => {
      const t = k / (cycles - 1);
      const eased = Math.pow(t, 1.4);
      return 0.5 + def.drift * eased * 0.025;
    });
    const baselineWindow = values.slice(0, Math.max(3, Math.floor(values.length * 0.08)));
    const finalWindow = values.slice(-Math.max(3, Math.floor(values.length * 0.08)));
    const baseline = baselineWindow.reduce((a, b) => a + b, 0) / baselineWindow.length;
    const finalAvg = finalWindow.reduce((a, b) => a + b, 0) / finalWindow.length;
    const delta_pct = ((finalAvg - baseline) / Math.abs(baseline || 1)) * 100;
    const regression = linregress(values);
    return {
      name: def.name,
      label: def.label,
      values,
      baseline,
      delta_pct,
      fleet_avg,
      regression,
      description: def.description,
      why_it_matters: def.why_it_matters,
    };
  });

  const sevText: Record<Severity, string> = {
    critical: "Severe HPC degradation detected. Multiple sensors trending outside fleet baseline. Immediate inspection required.",
    warning: "Early-stage HPC degradation. Sensor drift consistent with fleet-wide wear pattern. Schedule inspection within 20 cycles.",
    healthy: "Operating within nominal parameters. Sensor signatures match fleet baseline.",
  };
  const recText: Record<Severity, string> = {
    critical: "Ground engine before next cycle. Inspect HPC stages 3-7 for blade erosion. Estimated repair: 48-72 hours.",
    warning: "Continue monitoring with daily readings. Plan HPC borescope inspection at next scheduled maintenance window.",
    healthy: "No action required. Resume standard inspection cadence (every 200 cycles).",
  };

  return {
    ...engine,
    rul_history,
    sensors,
    diagnosis: sevText[engine.severity],
    recommendation: recText[engine.severity],
    top_contributors: ["HPC Outlet Temp (s3)", "LPC Outlet Temp (s2)", "HPC Outlet Pressure (s7)"],
  };
}

const EVENT_TEMPLATES: Record<
  AgentName,
  Array<{
    severity: Severity;
    title: (eid: number) => string;
    detail: (eid: number, rul: number) => string;
    meta: (rul: number) => Array<{ k: string; v: string }>;
  }>
> = {
  Monitor: [
    {
      severity: "critical",
      title: (eid) => `RUL forecast dropped below threshold on Engine #${pad(eid)}`,
      detail: () =>
        "Sliding-window CNN-LSTM prediction crossed the 30-cycle floor. Anomaly flag raised, escalating to Diagnostic Agent.",
      meta: (rul) => [
        { k: "Predicted RUL", v: `${rul} cycles` },
        { k: "Confidence", v: "94%" },
        { k: "Window", v: "30 cycles" },
      ],
    },
    {
      severity: "warning",
      title: (eid) => `Sensor drift detected on Engine #${pad(eid)}`,
      detail: () =>
        "HPC outlet temperature trending +6.4% above fleet baseline. Within warning band but accelerating.",
      meta: (rul) => [
        { k: "Predicted RUL", v: `${rul} cycles` },
        { k: "Drift", v: "+6.4%" },
        { k: "Rate", v: "0.18/cycle" },
      ],
    },
    {
      severity: "healthy",
      title: (eid) => `Engine #${pad(eid)} cleared post-cycle check`,
      detail: () => "All 14 active sensors within nominal range. No anomaly raised.",
      meta: (rul) => [
        { k: "Predicted RUL", v: `${rul} cycles` },
        { k: "Sensors OK", v: "14 / 14" },
      ],
    },
  ],
  Diagnostic: [
    {
      severity: "critical",
      title: (eid) => `Root cause identified for Engine #${pad(eid)}: HPC degradation`,
      detail: () =>
        "Compared to fleet average, this engine shows accelerated decay across s2, s3, and s7. Pattern matches stage-3-7 blade erosion signature.",
      meta: () => [
        { k: "Pattern", v: "HPC blade erosion" },
        { k: "Top sensor", v: "s3 (+9.1%)" },
        { k: "Fleet z-score", v: "+2.7σ" },
      ],
    },
    {
      severity: "warning",
      title: (eid) => `Engine #${pad(eid)} shows early-stage wear pattern`,
      detail: () =>
        "Sensor signature consistent with normal aging but ahead of fleet curve. Recommend trend re-check at next cycle.",
      meta: () => [
        { k: "Pattern", v: "Normal aging+" },
        { k: "Fleet z-score", v: "+1.4σ" },
      ],
    },
  ],
  Advisor: [
    {
      severity: "critical",
      title: (eid) => `Maintenance plan generated for Engine #${pad(eid)}`,
      detail: () =>
        "Ground engine before next cycle. Inspect HPC stages 3-7 for blade erosion. PDF report dispatched to ops queue.",
      meta: () => [
        { k: "Action", v: "Ground + inspect" },
        { k: "ETA repair", v: "48-72 h" },
        { k: "Report", v: "engine-XXX-report.pdf" },
      ],
    },
    {
      severity: "warning",
      title: (eid) => `Inspection scheduled for Engine #${pad(eid)}`,
      detail: () =>
        "Borescope inspection added to next maintenance window. Continue daily sensor monitoring in interim.",
      meta: () => [
        { k: "Action", v: "Schedule borescope" },
        { k: "Window", v: "next MX cycle" },
      ],
    },
  ],
};

function pad(n: number) {
  return String(n).padStart(3, "0");
}

export function makeMockEvents(fleet: FleetEngine[], count = 40): AgentEvent[] {
  const rand = seededRandom(99);
  const events: AgentEvent[] = [];
  const now = Date.now();
  const agents: AgentName[] = ["Monitor", "Diagnostic", "Advisor"];
  for (let i = 0; i < count; i++) {
    const engine = fleet[Math.floor(rand() * fleet.length)];
    const agent = agents[Math.floor(rand() * agents.length)];
    const templates = EVENT_TEMPLATES[agent].filter(
      (t) =>
        t.severity === engine.severity ||
        (engine.severity === "critical" && t.severity === "warning"),
    );
    const tpl = templates[Math.floor(rand() * templates.length)] ?? EVENT_TEMPLATES[agent][0];
    events.push({
      id: `evt-${i}`,
      agent,
      engine_id: engine.engine_id,
      severity: tpl.severity,
      title: tpl.title(engine.engine_id),
      detail: tpl.detail(engine.engine_id, engine.predicted_rul),
      meta: tpl.meta(engine.predicted_rul),
      ts: now - Math.floor(rand() * 1000 * 60 * 60 * 8),
    });
  }
  return events.sort((a, b) => b.ts - a.ts);
}
