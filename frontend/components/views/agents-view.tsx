'use client'

import { cn } from '@/lib/utils'
import { AgentLog } from '@/lib/engine-utils'
import { Bot, Database, Activity, Stethoscope, Wrench } from 'lucide-react'

interface AgentsViewProps {
  logs: AgentLog[]
}

const agentConfig = {
  DataEngineerAgent: {
    icon: Database,
    color: 'text-status-healthy',
    bgColor: 'bg-status-healthy/10',
    borderColor: 'border-status-healthy/30',
  },
  MonitorAgent: {
    icon: Activity,
    color: 'text-primary',
    bgColor: 'bg-primary/10',
    borderColor: 'border-primary/30',
  },
  DiagnosticAgent: {
    icon: Stethoscope,
    color: 'text-accent',
    bgColor: 'bg-accent/10',
    borderColor: 'border-accent/30',
  },
  MaintenanceAdvisorAgent: {
    icon: Wrench,
    color: 'text-status-watch',
    bgColor: 'bg-status-watch/10',
    borderColor: 'border-status-watch/30',
  },
}

const severityConfig = {
  info: {
    label: 'Info',
    color: 'text-muted-foreground',
    bgColor: 'bg-secondary/50',
  },
  warning: {
    label: 'Warning',
    color: 'text-status-watch',
    bgColor: 'bg-status-watch/10',
  },
  critical: {
    label: 'Critical',
    color: 'text-status-critical',
    bgColor: 'bg-status-critical/10',
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

export function AgentsView({ logs }: AgentsViewProps) {
  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Bot className="w-6 h-6 text-primary" />
          <h2 className="text-2xl font-bold text-foreground">Agent Activity Log</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          Real-time activity from the multi-agent AI pipeline
        </p>
      </div>

      {/* Agent Legend */}
      <div className="flex flex-wrap gap-4 mb-6 p-4 rounded-lg bg-card border border-border">
        {Object.entries(agentConfig).map(([name, config]) => {
          const Icon = config.icon
          return (
            <div key={name} className="flex items-center gap-2">
              <div className={cn('p-1.5 rounded', config.bgColor)}>
                <Icon className={cn('w-4 h-4', config.color)} />
              </div>
              <span className="text-xs text-muted-foreground">{name}</span>
            </div>
          )
        })}
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-6 top-0 bottom-0 w-px bg-gradient-to-b from-primary via-accent to-transparent" />

        <div className="space-y-4">
          {logs.map((log, index) => {
            const agent = agentConfig[log.agent_name]
            const severity = severityConfig[log.severity]
            const Icon = agent.icon

            return (
              <div
                key={log.id}
                className={cn(
                  'relative pl-14 animate-slide-in',
                  index === 0 && 'animate-pulse-glow'
                )}
                style={{ animationDelay: `${index * 50}ms` }}
              >
                {/* Timeline dot */}
                <div className={cn(
                  'absolute left-4 w-5 h-5 rounded-full border-2 bg-background flex items-center justify-center',
                  agent.borderColor
                )}>
                  <div className={cn('w-2 h-2 rounded-full', agent.bgColor.replace('/10', ''))} />
                </div>

                {/* Log entry card */}
                <div className={cn(
                  'p-4 rounded-xl bg-card border transition-all duration-300 hover:border-primary/50',
                  log.severity === 'critical' ? 'border-status-critical/30 animate-pulse-critical' :
                  log.severity === 'warning' ? 'border-status-watch/30' :
                  'border-border'
                )}>
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="flex items-center gap-2">
                      <div className={cn('p-1.5 rounded', agent.bgColor)}>
                        <Icon className={cn('w-4 h-4', agent.color)} />
                      </div>
                      <span className={cn('text-sm font-medium', agent.color)}>
                        {log.agent_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        severity.bgColor,
                        severity.color
                      )}>
                        {severity.label}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {formatTime(log.timestamp)}
                      </span>
                    </div>
                  </div>
                  
                  <p className="text-sm text-foreground leading-relaxed">
                    {log.message}
                  </p>
                  
                  {log.engine_id && (
                    <div className="mt-2 flex items-center gap-1">
                      <span className="text-xs text-muted-foreground">Engine:</span>
                      <span className="text-xs font-medium text-primary">#{log.engine_id}</span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
