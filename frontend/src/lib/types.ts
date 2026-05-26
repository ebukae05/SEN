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
