import Sparkline from './Sparkline'
import { statusConfig } from '../data/mockEngines'

export default function EngineCard({ engine, onSelect }) {
  const cfg = statusConfig[engine.status]

  return (
    <button
      onClick={() => onSelect(engine)}
      className="w-full text-left rounded-xl border p-5 transition-all duration-200 hover:border-accent/40 hover:translate-y-[-1px] focus:outline-none focus:ring-1 focus:ring-accent/50"
      style={{
        backgroundColor: '#111118',
        borderColor: engine.status === 'critical' ? 'rgba(239,68,68,0.3)' : '#1e1e2e',
        boxShadow: engine.status === 'critical'
          ? '0 0 20px rgba(239,68,68,0.12)'
          : engine.status === 'warning'
          ? '0 0 12px rgba(234,179,8,0.08)'
          : 'none',
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <p className="text-[10px] text-muted uppercase tracking-widest mb-1">
            Turbofan Unit
          </p>
          <h3 className="text-white font-semibold text-sm font-mono">
            {engine.name}
          </h3>
        </div>
        <StatusBadge status={engine.status} cfg={cfg} />
      </div>

      {/* Sparkline + RUL */}
      <div className="flex items-end justify-between mb-4">
        <Sparkline data={engine.rulHistory} color={cfg.color} />
        <div className="text-right">
          <p
            className="text-2xl font-bold font-mono leading-none"
            style={{ color: cfg.color }}
          >
            {engine.rul}
          </p>
          <p className="text-[10px] text-muted mt-0.5">cycles left</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 pt-3 border-t border-border">
        <Stat label="Health" value={`${engine.healthPercent}%`} />
        <Stat label="Cycles" value={engine.cycleCount} />
        <div className="ml-auto flex items-center gap-1 text-muted text-[10px]">
          <span>Details</span>
          <span>›</span>
        </div>
      </div>
    </button>
  )
}

function StatusBadge({ status, cfg }) {
  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
      style={{ color: cfg.color, backgroundColor: cfg.bg }}
    >
      {cfg.label}
    </span>
  )
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-[10px] text-muted uppercase tracking-wider">{label}</p>
      <p className="text-xs text-white font-medium mt-0.5">{value}</p>
    </div>
  )
}
