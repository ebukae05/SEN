import EngineCard from './EngineCard'

export default function EngineGrid({ engines, onSelect }) {
  const critical = engines.filter(e => e.status === 'critical').length
  const warning  = engines.filter(e => e.status === 'warning').length

  return (
    <div className="p-8">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-white text-xl font-semibold mb-1">Fleet Overview</h1>
        <p className="text-muted text-sm">
          {engines.length} engines monitored
          {critical > 0 && (
            <span className="ml-3 text-red-400">· {critical} critical</span>
          )}
          {warning > 0 && (
            <span className="ml-3 text-yellow-400">· {warning} warning</span>
          )}
        </p>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {engines.map(engine => (
          <EngineCard key={engine.id} engine={engine} onSelect={onSelect} />
        ))}
      </div>
    </div>
  )
}
