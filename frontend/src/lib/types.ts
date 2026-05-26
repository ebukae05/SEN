export type Severity = "healthy" | "warning" | "critical";

export interface EngineStatus {
  engine_id: number;
  predicted_rul: number;
  severity: Severity;
  alert: boolean;
  threshold: number;
}

export interface AnalyzeResponse {
  engine_id: number;
  result: string;
}

export interface FleetEngine extends EngineStatus {
  trend: number[];
  degradation_rate: number;
  last_cycle: number;
}

export interface SensorTrend {
  name: string;
  label: string;
  values: number[];
  baseline: number;
  delta_pct: number;
  fleet_avg: number[];
  regression: { slope: number; intercept: number };
  description: string;
  why_it_matters: string;
}

export interface EngineDetail extends FleetEngine {
  rul_history: number[];
  sensors: SensorTrend[];
  diagnosis: string;
  recommendation: string;
  top_contributors: string[];
}

export type AgentName = "Monitor" | "Diagnostic" | "Advisor";

export interface AgentEvent {
  id: string;
  agent: AgentName;
  engine_id: number;
  severity: Severity;
  title: string;
  detail: string;
  meta: Array<{ k: string; v: string }>;
  ts: number;
}
