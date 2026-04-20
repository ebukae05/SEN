'use client'

import { cn } from '@/lib/utils'
import { Engine } from '@/lib/engine-utils'
import { Clock, TrendingDown } from 'lucide-react'

interface FleetViewProps {
  engines: Engine[]
  onSelectEngine: (engine: Engine) => void
}

function EngineCard({ engine, onClick }: { engine: Engine; onClick: () => void }) {
  const statusConfig = {
    healthy: {
      label: 'Healthy',
      color: 'text-status-healthy',
      bgColor: 'bg-status-healthy/10',
      borderColor: 'border-status-healthy/30',
      glowClass: 'hover:shadow-[0_0_20px_rgba(34,197,94,0.3)]',
      pulseClass: 'animate-pulse-healthy',
    },
    watch: {
      label: 'Watch',
      color: 'text-status-watch',
      bgColor: 'bg-status-watch/10',
      borderColor: 'border-status-watch/30',
      glowClass: 'hover:shadow-[0_0_20px_rgba(234,179,8,0.3)]',
      pulseClass: 'animate-pulse-watch',
    },
    critical: {
      label: 'Critical',
      color: 'text-status-critical',
      bgColor: 'bg-status-critical/10',
      borderColor: 'border-status-critical/30',
      glowClass: 'hover:shadow-[0_0_25px_rgba(239,68,68,0.4)]',
      pulseClass: 'animate-pulse-critical',
    },
  }

  const config = statusConfig[engine.status]
  const timeAgo = Math.floor((Date.now() - engine.last_updated.getTime()) / 60000)

  return (
    <button
      onClick={onClick}
      className={cn(
        'relative w-full p-5 rounded-xl bg-card border text-left transition-all duration-300 group',
        config.borderColor,
        config.glowClass,
        engine.status === 'critical' && config.pulseClass
      )}
    >
      {/* Glow border effect */}
      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
        <div className={cn(
          'absolute inset-[-1px] rounded-xl',
          engine.status === 'critical' ? 'bg-gradient-to-r from-status-critical/50 to-status-critical/20' :
          engine.status === 'watch' ? 'bg-gradient-to-r from-status-watch/50 to-status-watch/20' :
          'bg-gradient-to-r from-primary/50 to-accent/20'
        )} style={{ mask: 'linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0)', maskComposite: 'exclude', padding: '1px' }} />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Engine</span>
          <span className="text-lg font-bold text-foreground">#{engine.engine_id}</span>
        </div>
        <span className={cn(
          'px-2 py-0.5 rounded-full text-xs font-medium',
          config.bgColor,
          config.color
        )}>
          {config.label}
        </span>
      </div>

      {/* RUL Display */}
      <div className="mb-4">
        <div className="flex items-baseline gap-1">
          <span className={cn('text-4xl font-bold', config.color)}>
            {engine.predicted_rul}
          </span>
          <span className="text-sm text-muted-foreground">cycles</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Predicted RUL</p>
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1 text-muted-foreground">
          <TrendingDown className="w-3 h-3" />
          <span>Cycle {engine.current_cycle}</span>
        </div>
        <div className="flex items-center gap-1 text-muted-foreground">
          <Clock className="w-3 h-3" />
          <span>{timeAgo}m ago</span>
        </div>
      </div>

      {/* Mini sparkline (visual indicator) */}
      <div className="mt-3 h-8 flex items-end gap-0.5">
        {engine.rul_history.slice(-20).map((point, i) => {
          const maxRul = Math.max(...engine.rul_history.slice(-20).map(p => p.rul))
          const height = (point.rul / maxRul) * 100
          return (
            <div
              key={i}
              className={cn(
                'flex-1 rounded-t transition-all',
                engine.status === 'critical' ? 'bg-status-critical/50' :
                engine.status === 'watch' ? 'bg-status-watch/50' :
                'bg-primary/50'
              )}
              style={{ height: `${Math.max(height, 10)}%` }}
            />
          )
        })}
      </div>
    </button>
  )
}

export function FleetView({ engines, onSelectEngine }: FleetViewProps) {
  return (
    <div className="p-6 h-full overflow-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-foreground">Fleet Overview</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Monitoring {engines.length} engines — sorted by urgency
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
        {engines.map((engine) => (
          <EngineCard
            key={engine.engine_id}
            engine={engine}
            onClick={() => onSelectEngine(engine)}
          />
        ))}
      </div>
    </div>
  )
}
