export const API_BASE_URL = "https://sen-production.up.railway.app"

export type Severity = "healthy" | "watch" | "critical"

export interface EngineStatus {
  engine_id: number
  predicted_rul: number
  severity: Severity
  alert: boolean
  threshold: number
}

export interface AnalyzeResponse {
  engine_id: number
  result: string
}

export interface HealthResponse {
  status: string
}

// Fetch all engine IDs
export async function getEngines(): Promise<number[]> {
  const response = await fetch(`${API_BASE_URL}/engines`)
  if (!response.ok) {
    throw new Error(`Failed to fetch engines: ${response.statusText}`)
  }
  return response.json()
}

// Fetch status for a single engine
export async function getEngineStatus(engineId: number): Promise<EngineStatus> {
  const response = await fetch(`${API_BASE_URL}/engine/${engineId}/status`)
  if (!response.ok) {
    throw new Error(`Failed to fetch engine ${engineId} status: ${response.statusText}`)
  }
  return response.json()
}

// Fetch statuses for multiple engines with batching
export async function getEngineStatuses(engineIds: number[], batchSize = 10): Promise<EngineStatus[]> {
  const results: EngineStatus[] = []
  
  for (let i = 0; i < engineIds.length; i += batchSize) {
    const batch = engineIds.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(id => getEngineStatus(id))
    )
    results.push(...batchResults)
  }
  
  return results
}

// Run deep analysis on an engine
export async function analyzeEngine(engineId: number): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ engine_id: engineId }),
  })
  if (!response.ok) {
    throw new Error(`Failed to analyze engine ${engineId}: ${response.statusText}`)
  }
  return response.json()
}

// Check API health
export async function checkHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error("API health check failed")
  }
  return response.json()
}
