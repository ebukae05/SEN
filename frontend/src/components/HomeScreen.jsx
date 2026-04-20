import { statusConfig } from '../data/mockEngines'

export default function HomeScreen({ engines, onSelect }) {
  const counts = engines.reduce((acc, e) => {
    acc[e.status] = (acc[e.status] || 0) + 1
    return acc
  }, {})

  const avgRul    = engines.length ? Math.round(engines.reduce((s, e) => s + e.rul, 0) / engines.length) : 0
  const critical  = engines.filter(e => e.status === 'critical')
  const warning   = engines.filter(e => e.status === 'warning')
  const alerts    = [...critical, ...warning].slice(0, 6)

  return (
    <div className="p-8 max-w-4xl">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-white text-2xl font-semibold mb-1">Fleet Overview</h1>
        <p className="text-muted text-sm">Real-time turbofan engine health monitoring · NASA CMAPSS FD001</p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-5 gap-3 mb-8">
        <StatCard label="Total Engines" value={engines.length} color="#3b82f6" />
        <StatCard label="Healthy"  value={counts.healthy  || 0} color="#22c55e" />
        <StatCard label="Caution"  value={counts.caution  || 0} color="#f97316" />
        <StatCard label="Warning"  value={counts.warning  || 0} color="#eab308" />
        <StatCard label="Critical" value={counts.critical || 0} color="#ef4444" />
      </div>

      {/* Fleet health bar */}
      <div className="rounded-xl border border-border p-5 mb-6" style={{ backgroundColor: '#111118' }}>
        <div className="flex items-center justify-between mb-3">
          <p className="text-white text-sm font-medium">Fleet Health Distribution</p>
          <p className="text-muted text-xs">Avg RUL: <span className="text-white font-mono">{avgRul} cycles</span></p>
        </div>
        <div className="flex h-3 rounded-full overflow-hidden gap-0.5">
          {[
            { key: 'healthy',  color: '#22c55e' },
            { key: 'caution',  color: '#f97316' },
            { key: 'warning',  color: '#eab308' },
            { key: 'critical', color: '#ef4444' },
          ].map(({ key, color }) => {
            const pct = ((counts[key] || 0) / engines.length) * 100
            return pct > 0 ? (
              <div
                key={key}
                style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.85 }}
                title={`${key}: ${counts[key] || 0}`}
              />
            ) : null
          })}
        </div>
        <div className="flex gap-4 mt-3">
          {[
            { key: 'healthy',  color: '#22c55e', label: 'Healthy'  },
            { key: 'caution',  color: '#f97316', label: 'Caution'  },
            { key: 'warning',  color: '#eab308', label: 'Warning'  },
            { key: 'critical', color: '#ef4444', label: 'Critical' },
          ].map(({ key, color, label }) => (
            <div key={key} className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
              <span className="text-muted text-xs">{label} ({counts[key] || 0})</span>
            </div>
          ))}
        </div>
      </div>

      {/* Alerts section */}
      {alerts.length > 0 && (
        <div className="rounded-xl border border-border p-5" style={{ backgroundColor: '#111118' }}>
          <p className="text-white text-sm font-medium mb-4">
            Engines Requiring Attention
            <span className="ml-2 text-xs text-muted font-normal">({alerts.length} flagged)</span>
          </p>
          <div className="space-y-2">
            {alerts.map(engine => {
              const cfg = statusConfig[engine.status]
              return (
                <button
                  key={engine.id}
                  onClick={() => onSelect(engine)}
                  className="w-full flex items-center gap-4 px-4 py-3 rounded-lg border transition-all hover:border-opacity-60 text-left"
                  style={{
                    backgroundColor: '#0f0f18',
                    borderColor: `${cfg.color}33`,
                    boxShadow: `0 0 12px ${cfg.color}10`,
                  }}
                >
                  <div
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ background: cfg.color, boxShadow: `0 0 6px ${cfg.color}` }}
                  />
                  <span className="text-white text-sm font-medium flex-1">{engine.name}</span>
                  <span
                    className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
                    style={{ color: cfg.color, backgroundColor: cfg.bg }}
                  >
                    {cfg.label}
                  </span>
                  <span className="text-muted text-xs font-mono">{engine.rul} cycles left</span>
                  <span className="text-muted text-xs">›</span>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div
      className="rounded-xl border p-4 text-center"
      style={{
        backgroundColor: '#111118',
        borderColor: `${color}22`,
        boxShadow: `0 0 16px ${color}10`,
      }}
    >
      <p className="text-2xl font-bold font-mono mb-1" style={{ color }}>{value}</p>
      <p className="text-muted text-[10px] uppercase tracking-wider">{label}</p>
    </div>
  )
}
