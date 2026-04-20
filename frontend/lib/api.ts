/**
 * api.ts — Typed fetch client for the SEN FastAPI backend.
 *
 * All functions read NEXT_PUBLIC_API_URL from the environment so the base URL
 * is never hardcoded.  Falls back to http://localhost:8000 for local dev.
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
  s2: number
  s3: number
  s4: number
  s7: number
  s8: number
  s9: number
  s11: number
  s12: number
  s13: number
  s14: number
  s15: number
  s17: number
  s20: number
  s21: number
}

export interface ApiEngineStatus {
  engine_id: number
  predicted_rul: number
  severity: string
  alert: boolean
}

// ── Fetch helpers ─────────────────────────────────────────────────────────────

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`)
  return res.json() as Promise<T>
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Fetch health snapshot for all 100 engines. */
export function fetchFleet(): Promise<ApiEngineSnapshot[]> {
  return get<ApiEngineSnapshot[]>('/fleet')
}

/** Fetch the last N cycles of sensor readings for one engine (default 50). */
export function fetchSensors(engineId: number, lastN = 50): Promise<ApiSensorReading[]> {
  return get<ApiSensorReading[]>(`/engine/${engineId}/sensors?last_n=${lastN}`)
}

/** Fetch CNN-LSTM RUL prediction + severity for one engine. */
export function fetchEngineStatus(engineId: number): Promise<ApiEngineStatus> {
  return get<ApiEngineStatus>(`/engine/${engineId}/status`)
}

/** Run the full 4-agent pipeline for one engine. Takes 2-3 minutes. */
export async function runAnalysis(engineId: number): Promise<string> {
  const res = await fetch(`${BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine_id: engineId }),
  })
  if (!res.ok) throw new Error(`POST /analyze → ${res.status}`)
  const data = await res.json()
  return data.result as string
}
