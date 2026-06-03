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

export interface Recommendation {
  engine_id: number;
  severity: Severity;
  predicted_rul: number;
  degradation_rate: number;
  threshold: number;
  dataset: string;
  recommendation: string;
  action_tag: string;
  cycles_to_threshold: number;
  cycles_to_failure: number;
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

// ─── Ingestion (Stage 3) ────────────────────────────────────────────────────

export type SensorTypeTag =
  | "vibration"
  | "temperature"
  | "pressure"
  | "speed"
  | "current"
  | "flow"
  | "oil_quality"
  | "acoustic"
  | "humidity"
  | "voltage"
  | "custom";

export type ColumnRole = "unit_id" | "cycle" | "sensor" | "rul" | "ignore";

export type Industry =
  | "oil_gas"
  | "power_generation"
  | "heavy_industry"
  | "mining"
  | "aerospace"
  | "marine"
  | "wind_energy"
  | "automotive_manufacturing"
  | "chemical"
  | "general_manufacturing";

export type AssetType =
  | "turbofan_engine"
  | "centrifugal_compressor"
  | "gas_turbine"
  | "steam_turbine"
  | "electric_motor"
  | "pump"
  | "gearbox"
  | "wind_turbine_drivetrain"
  | "conveyor_drive"
  | "crusher"
  | "generator"
  | "custom";

export interface SensorMapping {
  column_name: string;
  role: ColumnRole;
  display_name: string;
  type_tag: SensorTypeTag;
  unit: string;
  warning_threshold: number | null;
  critical_threshold: number | null;
}

export interface SensorSchemaPayload {
  upload_id: string;
  asset_id: string;
  asset_type: AssetType;
  industry: Industry;
  cycle_column: string;
  unit_id_column: string;
  rul_column: string | null;
  mappings: SensorMapping[];
  tenant_id?: string;
}

export interface DataQualityReport {
  is_valid: boolean;
  rows_loaded: number;
  engines_loaded: number;
  missing_values: number;
  out_of_range_values: number;
  missing_required_columns: string[];
  errors: string[];
  warnings: string[];
}

export interface UploadPreview {
  upload_id: string;
  filename: string;
  format: string;
  row_count: number;
  columns: string[];
  sample_rows: Array<Record<string, unknown>>;
  quality: DataQualityReport;
  suggestions: Record<string, ColumnRole>;
}

export type TrainingPhase =
  | "pending"
  | "ready"
  | "training"
  | "trained"
  | "training_failed"
  | "failed";

export interface DatasetMeta {
  dataset_id: string;
  asset_id: string;
  asset_type: string;
  industry: string;
  tenant_id: string;
  source: "cmapss" | "custom";
  status: string;
  created_at: string;
  sensor_count: number;
  engine_count: number;
  row_count: number;
  has_rul: boolean;
  sensor_display_names?: Record<string, string>;
  label: string;
  error?: string | null;
  training_rmse?: number | null;
  trained_at?: string | null;
  n_features_trained?: number | null;
  training_error?: string | null;
}

export interface TrainingStatus {
  dataset_id: string;
  status: TrainingPhase | string;
  training_rmse: number | null;
  trained_at: string | null;
  n_features_trained: number | null;
  training_error: string | null;
}

export interface TrainingTriggerResponse {
  dataset_id: string;
  status: string;
  message: string;
}

export interface ProcessResult {
  dataset_id: string;
  status: "ready" | "failed" | string;
  meta: DatasetMeta;
  errors: string[];
  warnings: string[];
}

// ─── Alerts (Stage 3) ───────────────────────────────────────────────────────

export interface AlertEvent {
  dataset_id: string;
  unit_id: number;
  cycle: number;
  previous_severity: Severity | null;
  current_severity: Severity;
  predicted_rul: number;
  threshold: number;
  timestamp: string;
}
