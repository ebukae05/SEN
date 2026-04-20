'use client'

import { cn } from '@/lib/utils'
import { Recommendation, Engine } from '@/lib/engine-utils'
import { AlertTriangle, AlertCircle, Eye, Wrench, CheckCircle, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface RecommendationsViewProps {
  recommendations: Recommendation[]
  engines: Engine[]
  onSelectEngine: (engine: Engine) => void
}

const severityConfig = {
  critical: {
    label: 'Critical',
    icon: AlertCircle,
    color: 'text-status-critical',
    bgColor: 'bg-status-critical/10',
    borderColor: 'border-status-critical/30',
    glowClass: 'animate-pulse-critical',
  },
  warning: {
    label: 'Warning',
    icon: AlertTriangle,
    color: 'text-status-watch',
    bgColor: 'bg-status-watch/10',
    borderColor: 'border-status-watch/30',
    glowClass: 'animate-pulse-watch',
  },
  watch: {
    label: 'Watch',
    icon: Eye,
    color: 'text-primary',
    bgColor: 'bg-primary/10',
    borderColor: 'border-primary/30',
    glowClass: '',
  },
}

const actionConfig = {
  'Ground Immediately': {
    icon: AlertCircle,
    color: 'text-status-critical',
  },
  'Inspect Within 10 Cycles': {
    icon: Wrench,
    color: 'text-status-watch',
  },
  'Schedule Maintenance': {
    icon: Wrench,
    color: 'text-primary',
  },
  'Continue Monitoring': {
    icon: CheckCircle,
    color: 'text-status-healthy',
  },
}

function formatTime(date: Date) {
  const now = Date.now()
  const diff = now - date.getTime()
  const minutes = Math.floor(diff / 60000)
  
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return date.toLocaleDateString()
}

export function RecommendationsView({ recommendations, engines, onSelectEngine }: RecommendationsViewProps) {
  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Wrench className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold text-foreground">Maintenance Recommendations</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          AI-generated maintenance recommendations for flagged engines
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {(['critical', 'warning', 'watch'] as const).map((severity) => {
          const config = severityConfig[severity]
          const count = recommendations.filter(r => r.severity === severity).length
          const Icon = config.icon
          
          return (
            <div
              key={severity}
              className={cn(
                'p-4 rounded-xl bg-card border',
                config.borderColor,
                count > 0 && severity === 'critical' && config.glowClass
              )}
            >
              <div className="flex items-center gap-3">
                <div className={cn('p-2 rounded-lg', config.bgColor)}>
                  <Icon className={cn('w-5 h-5', config.color)} />
                </div>
                <div>
                  <p className="text-2xl font-bold text-foreground">{count}</p>
                  <p className={cn('text-xs uppercase tracking-wide', config.color)}>
                    {config.label}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Recommendations list */}
      <div className="space-y-4">
        {recommendations.map((rec) => {
          const severity = severityConfig[rec.severity]
          const action = actionConfig[rec.action]
          const engine = engines.find(e => e.engine_id === rec.engine_id)
          const SeverityIcon = severity.icon
          const ActionIcon = action.icon

          return (
            <div
              key={rec.id}
              className={cn(
                'p-5 rounded-xl bg-card border transition-all duration-300',
                severity.borderColor,
                rec.severity === 'critical' && severity.glowClass
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  {/* Header */}
                  <div className="flex items-center gap-3 mb-3">
                    <div className={cn('p-2 rounded-lg', severity.bgColor)}>
                      <SeverityIcon className={cn('w-5 h-5', severity.color)} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-lg font-semibold text-foreground">
                          Engine #{rec.engine_id}
                        </span>
                        <span className={cn(
                          'px-2 py-0.5 rounded-full text-xs font-medium uppercase',
                          severity.bgColor,
                          severity.color
                        )}>
                          {severity.label}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Generated {formatTime(rec.created_at)}
                      </p>
                    </div>
                  </div>

                  {/* Action */}
                  <div className="flex items-center gap-2 mb-4 p-3 rounded-lg bg-secondary/30 border border-border/50">
                    <ActionIcon className={cn('w-5 h-5', action.color)} />
                    <span className={cn('font-medium', action.color)}>{rec.action}</span>
                    <span className="ml-auto text-sm text-muted-foreground">
                      Confidence: <span className="text-foreground font-medium">{rec.confidence.toFixed(1)}%</span>
                    </span>
                  </div>

                  {/* Contributing factors */}
                  <div>
                    <p className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
                      Contributing Factors
                    </p>
                    <ul className="space-y-1">
                      {rec.contributing_factors.map((factor, index) => (
                        <li key={index} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <span className={cn('mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0', severity.bgColor.replace('/10', ''))} />
                          {factor}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* View engine button */}
                {engine && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onSelectEngine(engine)}
                    className="flex-shrink-0 border-border hover:border-primary hover:text-primary"
                  >
                    View Details
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                )}
              </div>
            </div>
          )
        })}

        {recommendations.length === 0 && (
          <div className="text-center py-12">
            <CheckCircle className="w-12 h-12 text-status-healthy mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">All Clear</h3>
            <p className="text-sm text-muted-foreground">
              No maintenance recommendations at this time. All engines operating within normal parameters.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
