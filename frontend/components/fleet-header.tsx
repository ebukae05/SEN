'use client'

import { cn } from '@/lib/utils'
import { Plane, CheckCircle, AlertTriangle, AlertCircle, Clock, Bell } from 'lucide-react'

interface FleetSummary {
  total: number
  healthy: number
  watch: number
  critical: number
  avgRul: number
  activeAlerts: number
}

interface FleetHeaderProps {
  summary: FleetSummary
}

export function FleetHeader({ summary }: FleetHeaderProps) {
  const stats = [
    {
      label: 'Total Engines',
      value: summary.total,
      icon: Plane,
      color: 'text-primary',
      glowClass: 'glow-navy',
    },
    {
      label: 'Healthy',
      value: summary.healthy,
      icon: CheckCircle,
      color: 'text-status-healthy',
      glowClass: '',
      bgClass: 'bg-status-healthy/10',
    },
    {
      label: 'Watch',
      value: summary.watch,
      icon: AlertTriangle,
      color: 'text-status-watch',
      glowClass: '',
      bgClass: 'bg-status-watch/10',
    },
    {
      label: 'Critical',
      value: summary.critical,
      icon: AlertCircle,
      color: 'text-status-critical',
      glowClass: summary.critical > 0 ? 'animate-pulse-critical' : '',
      bgClass: 'bg-status-critical/10',
    },
    {
      label: 'Avg Fleet RUL',
      value: `${summary.avgRul} cycles`,
      icon: Clock,
      color: 'text-primary',
      glowClass: '',
    },
    {
      label: 'Active Alerts',
      value: summary.activeAlerts,
      icon: Bell,
      color: summary.activeAlerts > 0 ? 'text-status-critical' : 'text-muted-foreground',
      glowClass: '',
    },
  ]

  return (
    <header className="bg-card/50 backdrop-blur-sm border-b border-border px-6 py-3">
      <div className="flex items-center gap-4 overflow-x-auto">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <div
              key={stat.label}
              className={cn(
                'flex items-center gap-3 px-4 py-2 rounded-lg bg-secondary/50 border border-border/50 min-w-fit',
                stat.glowClass
              )}
            >
              <div className={cn('p-1.5 rounded-md', stat.bgClass || 'bg-primary/10')}>
                <Icon className={cn('w-4 h-4', stat.color)} />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  {stat.label}
                </span>
                <span className={cn('text-lg font-semibold', stat.color)}>
                  {stat.value}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </header>
  )
}
