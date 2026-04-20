import { useState } from 'react'
import { statusConfig } from '../data/mockEngines'

export default function Sidebar({ engines, selectedEngine, onSelect, onHome }) {
  const [search, setSearch] = useState('')

  const filtered = engines.filter(e =>
    e.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <aside className="w-64 shrink-0 border-r border-border flex flex-col bg-surface h-screen">

      {/* Brand */}
      <div
        className="px-5 py-4 border-b border-border cursor-pointer"
        onClick={onHome}
      >
        <div className="flex items-center gap-2.5 mb-1">
          <div
            className="w-2 h-2 rounded-full shrink-0"
            style={{ background: '#3b82f6', boxShadow: '0 0 8px #3b82f6' }}
          />
          <span className="text-white font-semibold tracking-wide text-sm">SEN</span>
        </div>
        <p className="text-muted text-[10px] leading-tight">Sensor Engine Network</p>
      </div>

      {/* Search */}
      <div className="px-3 py-3 border-b border-border">
        <input
          type="text"
          placeholder="Search engines…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full bg-bg border border-border rounded-lg px-3 py-1.5 text-xs text-white placeholder-muted focus:outline-none focus:border-accent/50 transition-colors"
        />
      </div>

      {/* Engine list */}
      <div className="flex-1 overflow-y-auto py-2">
        {filtered.map(engine => {
          const cfg      = statusConfig[engine.status] || statusConfig.healthy
          const isActive = selectedEngine?.id === engine.id
          return (
            <button
              key={engine.id}
              onClick={() => onSelect(engine)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                isActive
                  ? 'bg-accent/10 border-r-2 border-accent'
                  : 'hover:bg-white/5'
              }`}
            >
              <div
                className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{
                  background: cfg.color,
                  boxShadow: isActive ? `0 0 6px ${cfg.color}` : 'none',
                }}
              />
              <span className={`text-xs flex-1 ${isActive ? 'text-white font-medium' : 'text-muted'}`}>
                {engine.name}
              </span>
              <span
                className="text-[10px] font-mono font-medium shrink-0"
                style={{ color: cfg.color }}
              >
                {engine.rul}
              </span>
            </button>
          )
        })}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-border">
        <p className="text-[10px] text-muted/40">NASA CMAPSS FD001 · {engines.length} engines</p>
      </div>
    </aside>
  )
}
