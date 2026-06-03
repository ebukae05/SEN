import type {
  AgentEvent,
  AgentName,
  DatasetMeta,
  EngineDetail,
  FleetEngine,
  ProcessResult,
  Recommendation,
  SensorTrend,
  Severity,
  UploadPreview,
} from "./types";

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

function seedFromString(s: string): number {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return hash || 7;
}

function buildEngineFromRand(engineId: number, rand: () => number, threshold: number): FleetEngine {
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

  return {
    engine_id: engineId,
    predicted_rul: rul,
    severity: severityFromRul(rul, threshold),
    alert: rul < threshold,
    threshold,
    trend,
    degradation_rate: -(0.3 + rand() * 1.5),
    last_cycle: 120 + Math.round(rand() * 80),
  };
}

export function makeMockFleet(count = 100, seed: number | string = 7): FleetEngine[] {
  const seedNum = typeof seed === "string" ? seedFromString(seed) : seed;
  const rand = seededRandom(seedNum);
  const threshold = 30;
  const engines: FleetEngine[] = [];
  for (let i = 1; i <= count; i++) {
    engines.push(buildEngineFromRand(i, rand, threshold));
  }
  return engines.sort((a, b) => a.predicted_rul - b.predicted_rul);
}

export function makeFleetFromIds(ids: number[], seed: number | string = 7): FleetEngine[] {
  const seedNum = typeof seed === "string" ? seedFromString(seed) : seed;
  const rand = seededRandom(seedNum);
  const threshold = 30;
  const engines = ids.map((id) => buildEngineFromRand(id, rand, threshold));
  return engines.sort((a, b) => a.predicted_rul - b.predicted_rul);
}

export interface SensorDef {
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

const DRIFT_CYCLE = [0.85, 0.92, 0.78, -0.65, -0.55, 0.7, 0.6, -0.4, 0.5, -0.3];

export function buildSensorDefsFromMap(
  displayNames: Record<string, string>,
): SensorDef[] {
  return Object.entries(displayNames).map(([col, label], i) => ({
    name: col,
    label: label || col,
    drift: DRIFT_CYCLE[i % DRIFT_CYCLE.length],
    description: `${label || col} (${col}) — sensor channel ingested from the uploaded dataset.`,
    why_it_matters: `Sustained drift in ${label || col} away from the baseline window typically precedes mechanical degradation. Track against fleet average for context.`,
  }));
}

export function makeMockEngineDetail(
  engine: FleetEngine,
  overrideSensorDefs?: SensorDef[],
): EngineDetail {
  const defs = overrideSensorDefs && overrideSensorDefs.length > 0 ? overrideSensorDefs : SENSOR_DEFS;
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

  const sensors: SensorTrend[] = defs.map((def) => {
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

  const top_contributors =
    overrideSensorDefs && overrideSensorDefs.length > 0
      ? overrideSensorDefs.slice(0, 3).map((d) => `${d.label} (${d.name})`)
      : ["HPC Outlet Temp (s3)", "LPC Outlet Temp (s2)", "HPC Outlet Pressure (s7)"];

  return {
    ...engine,
    rul_history,
    sensors,
    diagnosis: sevText[engine.severity],
    recommendation: recText[engine.severity],
    top_contributors,
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

const RECOMMENDATIONS: Record<
  Severity,
  Array<{ tag: string; text: string }>
> = {
  critical: [
    {
      tag: "Ground + inspect HPC",
      text: "Ground engine before next cycle. Inspect HPC stages 3-7 for blade erosion and thermal-barrier coating breakdown. Estimated repair: 48-72 hours.",
    },
    {
      tag: "Ground + replace bearings",
      text: "Pull engine from service immediately. Fan-bearing vibration signature consistent with impending failure. Replace #1 and #2 bearings, re-balance fan rotor.",
    },
    {
      tag: "Emergency teardown",
      text: "Critical RUL projection. Schedule emergency teardown at next available bay. Capture borescope footage of HPC and HPT stages prior to disassembly.",
    },
  ],
  warning: [
    {
      tag: "Borescope at next MX",
      text: "Schedule HPC borescope inspection at next maintenance window. Continue daily sensor monitoring; flag any sensor delta above +12%.",
    },
    {
      tag: "Tighten monitoring",
      text: "Move to enhanced monitoring cadence — sample sensor data every cycle instead of every 10. Re-evaluate after 20 cycles.",
    },
    {
      tag: "Plan inspection window",
      text: "Add to maintenance queue for next 30-cycle window. Coordinate with line ops for minimum-disruption ground time.",
    },
  ],
  healthy: [
    {
      tag: "Standard cadence",
      text: "Operating within nominal parameters. Continue standard inspection cadence (every 200 cycles). No action required.",
    },
  ],
};

function cyclesUntil(rul: number, rate: number, floor: number): number {
  const r = Math.abs(rate);
  if (r === 0) return 9999;
  return Math.max(0, Math.round((rul - floor) / r));
}

export function makeMockRecommendations(fleet: FleetEngine[]): Recommendation[] {
  const rand = seededRandom(31);
  return fleet.map((e) => {
    const pool = RECOMMENDATIONS[e.severity];
    const pick = pool[Math.floor(rand() * pool.length)];
    return {
      engine_id: e.engine_id,
      severity: e.severity,
      predicted_rul: e.predicted_rul,
      degradation_rate: e.degradation_rate,
      threshold: e.threshold,
      dataset: "FD001",
      recommendation: pick.text,
      action_tag: pick.tag,
      cycles_to_threshold: cyclesUntil(e.predicted_rul, e.degradation_rate, e.threshold),
      cycles_to_failure: cyclesUntil(e.predicted_rul, e.degradation_rate, 0),
    };
  });
}

// ─── Upload wizard mocks (Stage 3) ──────────────────────────────────────────

export const mockUploadPreview: UploadPreview = {
  upload_id: "demo-upload-0001",
  filename: "compressor-fleet-sample.csv",
  format: "csv",
  row_count: 1240,
  columns: [
    "unit_id",
    "cycle",
    "vib_de_x",
    "vib_de_y",
    "vib_nde_x",
    "bearing_temp",
    "oil_pressure",
    "shaft_rpm",
    "motor_current",
    "rul",
  ],
  sample_rows: [
    {
      unit_id: 1,
      cycle: 1,
      vib_de_x: 2.1,
      vib_de_y: 1.9,
      vib_nde_x: 1.7,
      bearing_temp: 68.4,
      oil_pressure: 142,
      shaft_rpm: 1798,
      motor_current: 41.2,
      rul: 198,
    },
    {
      unit_id: 1,
      cycle: 2,
      vib_de_x: 2.2,
      vib_de_y: 1.9,
      vib_nde_x: 1.7,
      bearing_temp: 68.7,
      oil_pressure: 142,
      shaft_rpm: 1797,
      motor_current: 41.3,
      rul: 197,
    },
  ],
  quality: {
    is_valid: true,
    rows_loaded: 1240,
    engines_loaded: 5,
    missing_values: 3,
    out_of_range_values: 0,
    missing_required_columns: [],
    errors: [],
    warnings: ["3 missing sensor readings"],
  },
  suggestions: {
    unit_id: "unit_id",
    cycle: "cycle",
    vib_de_x: "sensor",
    vib_de_y: "sensor",
    vib_nde_x: "sensor",
    bearing_temp: "sensor",
    oil_pressure: "sensor",
    shaft_rpm: "sensor",
    motor_current: "sensor",
    rul: "rul",
  },
};

export const mockDatasets: DatasetMeta[] = [
  {
    dataset_id: "FD001",
    asset_id: "FD001",
    asset_type: "turbofan_engine",
    industry: "aerospace",
    tenant_id: "default",
    source: "cmapss",
    status: "ready",
    created_at: "",
    sensor_count: 14,
    engine_count: 100,
    row_count: 20631,
    has_rul: true,
    label: "FD001",
  },
  {
    dataset_id: "FD002",
    asset_id: "FD002",
    asset_type: "turbofan_engine",
    industry: "aerospace",
    tenant_id: "default",
    source: "cmapss",
    status: "ready",
    created_at: "",
    sensor_count: 14,
    engine_count: 260,
    row_count: 53759,
    has_rul: true,
    label: "FD002",
  },
  {
    dataset_id: "FD003",
    asset_id: "FD003",
    asset_type: "turbofan_engine",
    industry: "aerospace",
    tenant_id: "default",
    source: "cmapss",
    status: "ready",
    created_at: "",
    sensor_count: 14,
    engine_count: 100,
    row_count: 24720,
    has_rul: true,
    label: "FD003",
  },
  {
    dataset_id: "FD004",
    asset_id: "FD004",
    asset_type: "turbofan_engine",
    industry: "aerospace",
    tenant_id: "default",
    source: "cmapss",
    status: "ready",
    created_at: "",
    sensor_count: 14,
    engine_count: 249,
    row_count: 61249,
    has_rul: true,
    label: "FD004",
  },
];

export const mockProcessResult: ProcessResult = {
  dataset_id: "compressor-demo-a1b2",
  status: "ready",
  meta: {
    dataset_id: "compressor-demo-a1b2",
    asset_id: "compressor-fleet-sample",
    asset_type: "centrifugal_compressor",
    industry: "oil_gas",
    tenant_id: "default",
    source: "custom",
    status: "ready",
    created_at: new Date().toISOString(),
    sensor_count: 7,
    engine_count: 5,
    row_count: 1240,
    has_rul: true,
    sensor_display_names: {
      vib_de_x: "Drive-End Vibration X",
      vib_de_y: "Drive-End Vibration Y",
      vib_nde_x: "Non-Drive-End Vibration X",
      bearing_temp: "Bearing Temperature",
      oil_pressure: "Oil Pressure",
      shaft_rpm: "Shaft RPM",
      motor_current: "Motor Current",
    },
    label: "compressor-fleet-sample",
  },
  errors: [],
  warnings: [],
};

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
