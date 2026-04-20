// Engine status types
export type EngineStatus = 'healthy' | 'watch' | 'critical'

export interface EngineSensors {
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

export interface Engine {
  engine_id: number
  current_cycle: number
  predicted_rul: number
  status: EngineStatus
  sensors: EngineSensors
  last_updated: Date
  rul_history: { cycle: number; rul: number }[]
  sensor_history: { cycle: number; sensors: EngineSensors }[]
}

export interface AgentLog {
  id: string
  timestamp: Date
  agent_name: 'DataEngineerAgent' | 'MonitorAgent' | 'DiagnosticAgent' | 'MaintenanceAdvisorAgent'
  message: string
  severity: 'info' | 'warning' | 'critical'
  engine_id?: number
}

export interface Recommendation {
  id: string
  engine_id: number
  severity: 'critical' | 'warning' | 'watch'
  action: 'Ground Immediately' | 'Inspect Within 10 Cycles' | 'Schedule Maintenance' | 'Continue Monitoring'
  confidence: number
  contributing_factors: string[]
  created_at: Date
}

// Top RUL-correlated sensors from EDA, ordered by degradation impact
const degradationSensors = [
  { id: 's11', label: 'HPC static pressure' },
  { id: 's4',  label: 'LPT outlet temp' },
  { id: 's12', label: 'Fuel flow ratio' },
  { id: 's7',  label: 'HPC outlet pressure' },
  { id: 's15', label: 'Bypass ratio' },
  { id: 's21', label: 'LPT coolant bleed' },
  { id: 's9',  label: 'Physical core speed' },
]

// Deterministically pick sensors for an engine based on its ID
export function getEngineSensors(engineId: number, count: number = 2) {
  const offset = engineId % degradationSensors.length
  return Array.from({ length: count }, (_, i) =>
    degradationSensors[(offset + i) % degradationSensors.length]
  )
}

// Generate agent logs from real fleet data
export function generateAgentLogs(engines: Engine[]): AgentLog[] {
  if (engines.length === 0) return []

  const logs: AgentLog[] = []
  let logIndex = 0

  // Sort engines so critical/watch appear first (most interesting logs)
  const sorted = [...engines].sort((a, b) => {
    const order: Record<EngineStatus, number> = { critical: 0, watch: 1, healthy: 2 }
    return order[a.status] - order[b.status]
  })

  // Each engine gets a 4-agent pass through the pipeline
  const selected = sorted.slice(0, 25)
  for (const engine of selected) {
    const sensors = getEngineSensors(engine.engine_id, 2)
    const severityLabel = engine.status === 'critical' ? 'CRITICAL'
      : engine.status === 'watch' ? 'CAUTION' : 'NOMINAL'

    // DataEngineerAgent — always info
    logs.push({
      id: `log-${logIndex++}`,
      timestamp: new Date(Date.now() - logIndex * 120000),
      agent_name: 'DataEngineerAgent',
      message: `Ingested ${engine.current_cycle} cycles for Engine ${engine.engine_id}, data quality nominal`,
      severity: 'info',
      engine_id: engine.engine_id,
    })

    // MonitorAgent — severity matches engine status
    logs.push({
      id: `log-${logIndex++}`,
      timestamp: new Date(Date.now() - logIndex * 120000),
      agent_name: 'MonitorAgent',
      message: `Engine ${engine.engine_id} RUL predicted at ${engine.predicted_rul} cycles — ${severityLabel}`,
      severity: engine.status === 'critical' ? 'critical' : engine.status === 'watch' ? 'warning' : 'info',
      engine_id: engine.engine_id,
    })

    // DiagnosticAgent — only for non-healthy engines
    if (engine.status !== 'healthy') {
      logs.push({
        id: `log-${logIndex++}`,
        timestamp: new Date(Date.now() - logIndex * 120000),
        agent_name: 'DiagnosticAgent',
        message: `Fleet comparison for Engine ${engine.engine_id}: ${sensors[0].id} (${sensors[0].label}) and ${sensors[1].id} (${sensors[1].label}) showing degradation`,
        severity: engine.status === 'critical' ? 'critical' : 'warning',
        engine_id: engine.engine_id,
      })
    }

    // MaintenanceAdvisorAgent — only for non-healthy engines
    if (engine.status === 'critical') {
      logs.push({
        id: `log-${logIndex++}`,
        timestamp: new Date(Date.now() - logIndex * 120000),
        agent_name: 'MaintenanceAdvisorAgent',
        message: `Immediate inspection recommended for Engine ${engine.engine_id} — RUL at ${engine.predicted_rul} cycles`,
        severity: 'critical',
        engine_id: engine.engine_id,
      })
    } else if (engine.status === 'watch') {
      logs.push({
        id: `log-${logIndex++}`,
        timestamp: new Date(Date.now() - logIndex * 120000),
        agent_name: 'MaintenanceAdvisorAgent',
        message: `Schedule maintenance for Engine ${engine.engine_id} within next service window`,
        severity: 'warning',
        engine_id: engine.engine_id,
      })
    }
  }

  return logs.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
}

// Derive confidence from how far the engine's RUL is into the danger zone.
// Lower RUL = higher confidence that maintenance is needed.
function computeConfidence(rul: number, status: EngineStatus): number {
  if (status === 'critical') {
    // RUL 0-49: maps to 88-97% confidence (lower RUL = higher confidence)
    return Math.min(97, 97 - (rul / 50) * 9)
  }
  // Watch: RUL 50-99: maps to 72-88% confidence
  return Math.min(88, 88 - ((rul - 50) / 50) * 16)
}

// Generate recommendations from real fleet data
export function generateRecommendations(engines: Engine[]): Recommendation[] {
  const recommendations: Recommendation[] = []
  const now = Date.now()

  const criticalEngines = engines.filter(e => e.status === 'critical')
  const watchEngines = engines.filter(e => e.status === 'watch')

  criticalEngines.forEach((engine, i) => {
    const sensors = getEngineSensors(engine.engine_id, 2)
    const confidence = computeConfidence(engine.predicted_rul, engine.status)
    recommendations.push({
      id: `rec-${engine.engine_id}`,
      engine_id: engine.engine_id,
      severity: 'critical',
      action: engine.predicted_rul < 20 ? 'Ground Immediately' : 'Inspect Within 10 Cycles',
      confidence: Math.round(confidence * 10) / 10,
      contributing_factors: [
        `${sensors[0].id} (${sensors[0].label}) declining faster than fleet average`,
        `${sensors[1].id} (${sensors[1].label}) showing abnormal degradation pattern`,
        engine.predicted_rul < 30 ? 'Critical threshold breach imminent' : 'Accelerated degradation pattern detected',
      ],
      created_at: new Date(now - i * 300000),
    })
  })

  watchEngines.forEach((engine, i) => {
    const sensors = getEngineSensors(engine.engine_id, 2)
    const confidence = computeConfidence(engine.predicted_rul, engine.status)
    recommendations.push({
      id: `rec-${engine.engine_id}`,
      engine_id: engine.engine_id,
      severity: engine.predicted_rul < 35 ? 'warning' : 'watch',
      action: engine.predicted_rul < 35 ? 'Inspect Within 10 Cycles' : 'Schedule Maintenance',
      confidence: Math.round(confidence * 10) / 10,
      contributing_factors: [
        `${sensors[0].id} (${sensors[0].label}) showing early degradation signs`,
        `${sensors[1].id} (${sensors[1].label}) trending below fleet baseline`,
        engine.predicted_rul < 40 ? 'Degradation rate exceeding fleet average' : 'Minor deviation from nominal parameters',
      ],
      created_at: new Date(now - (criticalEngines.length + i) * 300000),
    })
  })

  return recommendations.sort((a, b) => {
    const severityOrder = { critical: 0, warning: 1, watch: 2 }
    return severityOrder[a.severity] - severityOrder[b.severity]
  })
}

// Fleet summary stats
export function getFleetSummary(engines: Engine[]) {
  const healthy = engines.filter(e => e.status === 'healthy').length
  const watch = engines.filter(e => e.status === 'watch').length
  const critical = engines.filter(e => e.status === 'critical').length
  const avgRul = Math.round(engines.reduce((sum, e) => sum + e.predicted_rul, 0) / (engines.length || 1))
  const activeAlerts = critical + Math.floor(watch / 2)

  return {
    total: engines.length,
    healthy,
    watch,
    critical,
    avgRul,
    activeAlerts,
  }
}
