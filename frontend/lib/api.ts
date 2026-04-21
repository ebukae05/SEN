/**
 * api.ts — Typed fetch client for the SEN FastAPI backend.
 *
 * All functions read NEXT_PUBLIC_API_URL from the environment so the base URL
 * is never hardcoded.  Falls back to http://localhost:8000 for local dev.
 *
 * All data endpoints accept an optional `dataset` parameter (FD001–FD004).
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ── Response types (mirror FastAPI schemas) ───────────────────────────────────

export interface ApiEngineSnapshot {
  id: number
  name: string
  rul: number
  rulHistory: number[]
  healthPercent: number
  cycleCount: number
  status: 'healthy' | 'caution' | 'warning' | 'critical'
}

export interface ApiSensorReading {
  cycle: number
  sensors: Record<string, number>
}

export interface ApiEngineStatus {
  engine_id: number
  predicted_rul: number
  severity: string
  alert: boolean
}

export interface ApiDatasetInfo {
  dataset_id: string
  engines: number
  fault_modes: number
  operating_conditions: number
  n_features: number
  available: boolean
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Fetch metadata for all available CMAPSS datasets. */
export function fetchDatasets(): Promise<ApiDatasetInfo[]> {
  return get<ApiDatasetInfo[]>('/datasets')
}

/** Fetch health snapshot for all engines in a dataset. */
export function fetchFleet(dataset = 'FD001'): Promise<ApiEngineSnapshot[]> {
  return get<ApiEngineSnapshot[]>(`/fleet?dataset=${dataset}`)
}

/** Fetch the last N cycles of sensor readings for one engine (default 50). */
export function fetchSensors(engineId: number, lastN = 50, dataset = 'FD001'): Promise<ApiSensorReading[]> {
  return get<ApiSensorReading[]>(`/engine/${engineId}/sensors?last_n=${lastN}&dataset=${dataset}`)
}

/** Fetch CNN-LSTM RUL prediction + severity for one engine. */
export function fetchEngineStatus(engineId: number, dataset = 'FD001'): Promise<ApiEngineStatus> {
  return get<ApiEngineStatus>(`/engine/${engineId}/status?dataset=${dataset}`)
}

/** Run the full 4-agent pipeline for one engine. Takes 2-3 minutes. */
export async function runAnalysis(engineId: number, dataset = 'FD001'): Promise<string> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine_id: engineId, dataset }),
  })
  if (!res.ok) throw new Error(`POST /analyze → ${res.status}`)
  const data = await res.json()
  return data.result as string
}
