import RULChart from './RULChart'
import Chatbot from './Chatbot'
import { statusConfig } from '../data/mockEngines'

export default function DetailView({ engine, onBack }) {
  const cfg = statusConfig[engine.status]

  return (
    <div className="flex flex-col h-full">
      {/* Top bar */}
      <div className="flex items-center gap-4 px-8 py-4 border-b border-border shrink-0">
        <button
          onClick={onBack}
          className="text-muted hover:text-white text-sm transition-colors flex items-center gap-1.5"
        >
          ← Fleet
        </button>
        <div className="w-px h-4 bg-border" />
        <h2 className="text-white font-semibold text-sm font-mono">{engine.name}</h2>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
          style={{ color: cfg.color, backgroundColor: cfg.bg }}
        >
          {cfg.label}
        </span>
      </div>

      {/* Split panels */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT: Charts + stats */}
        <div className="flex-1 flex flex-col overflow-y-auto px-8 py-6 border-r border-border">
          {/* RUL header */}
          <div className="flex items-baseline gap-3 mb-6">
            <span
              className="text-5xl font-bold font-mono"
              style={{ color: cfg.color }}
            >
              {engine.rul}
            </span>
            <div>
              <p className="text-white text-sm font-medium">cycles remaining</p>
              <p className="text-muted text-xs">Remaining Useful Life</p>
            </div>
          </div>

          {/* Chart */}
          <div
            className="rounded-xl border border-border p-4 mb-6"
            style={{ backgroundColor: '#111118', height: '220px' }}
          >
            <p className="text-muted text-[10px] uppercase tracking-widest mb-3">
              RUL Trend
            </p>
            <div style={{ height: '170px' }}>
              <RULChart engine={engine} />
            </div>
          </div>

          {/* Key stats */}
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Health"
              value={`${engine.healthPercent}%`}
              color={engine.healthPercent > 60 ? '#22c55e' : engine.healthPercent > 30 ? '#eab308' : '#ef4444'}
            />
            <StatCard label="Cycle Count" value={engine.cycleCount} />
            <StatCard label="Alert Threshold" value="50 cycles" color="#eab308" />
          </div>

          {/* Sensor note */}
          <div className="mt-4 rounded-lg border border-border px-4 py-3" style={{ backgroundColor: '#0f0f18' }}>
            <p className="text-muted text-[11px] leading-relaxed">
              Data sourced from NASA CMAPSS FD001 · 14 sensor channels monitored ·
              CNN-LSTM model (RMSE 13.22 cycles)
            </p>
          </div>
        </div>

        {/* RIGHT: Chatbot */}
        <div className="w-80 shrink-0 flex flex-col" style={{ backgroundColor: '#0d0d14' }}>
          <Chatbot engine={engine} />
        </div>

      </div>
    </div>
  )
}

function StatCard({ label, value, color }) {
  return (
    <div
      className="rounded-lg border border-border px-4 py-3"
      style={{ backgroundColor: '#0f0f18' }}
    >
      <p className="text-muted text-[10px] uppercase tracking-widest mb-1">{label}</p>
      <p
        className="text-lg font-bold font-mono"
        style={{ color: color || '#e2e8f0' }}
      >
        {value}
      </p>
    </div>
  )
}
