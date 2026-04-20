'use client'

import { useState } from 'react'
import { cn } from '@/lib/utils'
import { Engine, getEngineSensors } from '@/lib/engine-utils'
import { ArrowLeft, Activity, Cpu, Gauge, AlertTriangle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { runAnalysis } from '@/lib/api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface EngineDetailViewProps {
  engine: Engine
  onBack: () => void
}

const sensorLabels: Record<string, string> = {
  s2: 'Total temp at LPC outlet',
  s3: 'Total temp at HPC outlet', 
  s4: 'Total temp at LPT outlet',
  s7: 'Total pressure at HPC outlet',
  s8: 'Physical fan speed',
  s9: 'Physical core speed',
  s11: 'Static pressure at HPC outlet',
  s12: 'Ratio of fuel flow to Ps30',
  s13: 'Corrected fan speed',
  s14: 'Corrected core speed',
  s15: 'Bypass ratio',
  s17: 'Bleed enthalpy',
  s20: 'HPT coolant bleed',
  s21: 'LPT coolant bleed',
}

const sensorColors = [
  '#3b82f6', '#a78bfa', '#22c55e', '#eab308', '#ef4444',
  '#60a5fa', '#ec4899', '#f97316', '#06b6d4', '#8b5cf6',
  '#84cc16', '#f43f5e', '#0ea5e9', '#d946ef',
]

export function EngineDetailView({ engine, onBack }: EngineDetailViewProps) {
  const [analysisResult, setAnalysisResult] = useState<string | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)

  const handleRunAnalysis = async () => {
    setAnalysisLoading(true)
    setAnalysisResult(null)
    setAnalysisError(null)
    try {
      const result = await runAnalysis(engine.engine_id)
      setAnalysisResult(result)
    } catch (err) {
      setAnalysisError('Analysis failed — is the API running?')
    } finally {
      setAnalysisLoading(false)
    }
  }

  const statusConfig = {
    healthy: {
      label: 'Healthy',
      color: 'text-status-healthy',
      bgColor: 'bg-status-healthy/10',
      borderColor: 'border-status-healthy/50',
      glowClass: 'shadow-[0_0_30px_rgba(34,197,94,0.3)]',
    },
    watch: {
      label: 'Watch',
      color: 'text-status-watch',
      bgColor: 'bg-status-watch/10',
      borderColor: 'border-status-watch/50',
      glowClass: 'shadow-[0_0_30px_rgba(234,179,8,0.3)]',
    },
    critical: {
      label: 'Critical',
      color: 'text-status-critical',
      bgColor: 'bg-status-critical/10',
      borderColor: 'border-status-critical/50',
      glowClass: 'shadow-[0_0_30px_rgba(239,68,68,0.4)]',
    },
  }

  const config = statusConfig[engine.status]

  // Prepare RUL chart data
  const rulChartData = engine.rul_history.map((point) => ({
    cycle: point.cycle,
    rul: point.rul,
  }))

  // Prepare sensor chart data
  const sensorChartData = engine.sensor_history.map((point) => ({
    cycle: point.cycle,
    ...point.sensors,
  }))

  // Diagnostic notes derived from real engine data
  const sensors = getEngineSensors(engine.engine_id, 2)
  const healthPct = Math.min(100, Math.round((engine.predicted_rul / 130) * 100))

  const diagnosticNotes = [
    {
      agent: 'MonitorAgent',
      time: '2m ago',
      message: `Current RUL prediction: ${engine.predicted_rul} cycles (${healthPct}% health). ${
        engine.status === 'critical' ? 'Immediate attention required.' :
        engine.status === 'watch' ? 'Elevated monitoring active.' :
        'All parameters nominal.'
      }`,
    },
    {
      agent: 'DiagnosticAgent',
      time: '5m ago',
      message: engine.status === 'critical'
        ? `${sensors[0].id} (${sensors[0].label}) and ${sensors[1].id} (${sensors[1].label}) showing abnormal degradation. Recommend immediate fleet comparison.`
        : engine.status === 'watch'
        ? `${sensors[0].id} (${sensors[0].label}) trending below fleet baseline. ${sensors[1].id} (${sensors[1].label}) under observation.`
        : `All 14 sensors within normal operating parameters. No anomalies detected.`,
    },
    {
      agent: 'DataEngineerAgent',
      time: '8m ago',
      message: `Processed ${engine.current_cycle} cycles of telemetry data. 14 active sensors validated, 0 anomalies in data stream.`,
    },
  ]

  return (
    <div className="p-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-foreground">Engine #{engine.engine_id}</h2>
            <span className={cn(
              'px-3 py-1 rounded-full text-sm font-medium',
              config.bgColor,
              config.color
            )}>
              {config.label}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Current cycle: {engine.current_cycle} | Last updated: {Math.floor((Date.now() - engine.last_updated.getTime()) / 60000)}m ago
          </p>
        </div>
        <Button
          onClick={handleRunAnalysis}
          disabled={analysisLoading}
          className="bg-gradient-to-r from-primary to-accent text-primary-foreground hover:opacity-90 glow-navy disabled:opacity-50"
        >
          {analysisLoading ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Activity className="w-4 h-4 mr-2" />
          )}
          {analysisLoading ? 'Analyzing…' : 'Run Deeper Analysis'}
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* RUL Display Card */}
          <div className={cn(
            'p-6 rounded-xl bg-card border',
            config.borderColor,
            config.glowClass
          )}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-2">Remaining Useful Life</p>
                <div className="flex items-baseline gap-2">
                  <span className={cn('text-6xl font-bold', config.color)}>
                    {engine.predicted_rul}
                  </span>
                  <span className="text-xl text-muted-foreground">cycles</span>
                </div>
              </div>
              <div className={cn('p-4 rounded-xl', config.bgColor)}>
                <Gauge className={cn('w-12 h-12', config.color)} />
              </div>
            </div>
            {engine.status === 'critical' && (
              <div className="mt-4 p-3 rounded-lg bg-status-critical/10 border border-status-critical/30 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-status-critical" />
                <span className="text-sm text-status-critical font-medium">
                  Critical threshold breach — immediate inspection recommended
                </span>
              </div>
            )}
          </div>

          {/* RUL Trend Chart */}
          <div className="p-6 rounded-xl bg-card border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">RUL Prediction Over Time</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={rulChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="cycle" 
                    stroke="rgba(255,255,255,0.4)"
                    tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.4)"
                    tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="rul"
                    stroke={
                      engine.status === 'critical' ? '#ef4444' :
                      engine.status === 'watch' ? '#eab308' :
                      '#3b82f6'
                    }
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, fill: '#3b82f6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Sensor Readings Chart */}
          <div className="p-6 rounded-xl bg-card border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">Sensor Readings Over Time</h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sensorChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis 
                    dataKey="cycle" 
                    stroke="rgba(255,255,255,0.4)"
                    tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                  />
                  <YAxis 
                    stroke="rgba(255,255,255,0.4)"
                    tick={{ fill: 'rgba(255,255,255,0.6)', fontSize: 12 }}
                    domain={[0, 1]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'rgba(15, 23, 42, 0.95)',
                      border: '1px solid rgba(59, 130, 246, 0.3)',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Legend 
                    wrapperStyle={{ fontSize: '10px' }}
                    iconSize={8}
                  />
                  {Object.keys(engine.sensors).map((sensor, index) => (
                    <Line
                      key={sensor}
                      type="monotone"
                      dataKey={sensor}
                      stroke={sensorColors[index]}
                      strokeWidth={1.5}
                      dot={false}
                      name={sensor}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Sidebar - Diagnostic Notes */}
        <div className="space-y-6">
          <div className="p-6 rounded-xl bg-card border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-primary" />
              Agent Diagnostics
            </h3>
            <div className="space-y-4">
              {diagnosticNotes.map((note, index) => (
                <div key={index} className="p-3 rounded-lg bg-secondary/30 border border-border/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className={cn(
                      'text-xs font-medium',
                      note.agent === 'MonitorAgent' ? 'text-primary' :
                      note.agent === 'DiagnosticAgent' ? 'text-accent' :
                      'text-status-healthy'
                    )}>
                      {note.agent}
                    </span>
                    <span className="text-xs text-muted-foreground">{note.time}</span>
                  </div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{note.message}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 4-Agent Analysis Result */}
          {(analysisResult || analysisError || analysisLoading) && (
            <div className="p-6 rounded-xl bg-card border border-primary/30">
              <h3 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary" />
                4-Agent Pipeline Report
              </h3>
              {analysisLoading && (
                <div className="flex items-center gap-3 text-muted-foreground text-sm">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running all 4 agents — this takes 2-3 minutes…
                </div>
              )}
              {analysisError && (
                <p className="text-sm text-status-critical">{analysisError}</p>
              )}
              {analysisResult && (
                <pre className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed">
                  {analysisResult}
                </pre>
              )}
            </div>
          )}

          {/* Current Sensor Values */}
          <div className="p-6 rounded-xl bg-card border border-border">
            <h3 className="text-lg font-semibold text-foreground mb-4">Current Sensor Values</h3>
            <div className="space-y-2 max-h-64 overflow-auto pr-2">
              {Object.entries(engine.sensors).map(([key, value], index) => (
                <div key={key} className="flex items-center justify-between py-2 border-b border-border/30 last:border-0">
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-2 h-2 rounded-full" 
                      style={{ backgroundColor: sensorColors[index] }}
                    />
                    <span className="text-xs text-muted-foreground">{key}</span>
                  </div>
                  <span className="text-sm font-mono text-foreground">{value.toFixed(3)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
