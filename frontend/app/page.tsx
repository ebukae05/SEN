'use client'

import { useState, useMemo, useEffect } from 'react'
import { ParticleBackground } from '@/components/particle-background'
import { SenSidebar } from '@/components/sen-sidebar'
import { FleetHeader } from '@/components/fleet-header'
import { HomeView } from '@/components/views/home-view'
import { FleetView } from '@/components/views/fleet-view'
import { EngineDetailView } from '@/components/views/engine-detail-view'
import { AgentsView } from '@/components/views/agents-view'
import { RecommendationsView } from '@/components/views/recommendations-view'
import { SettingsView } from '@/components/views/settings-view'
import {
  generateAgentLogs,
  generateRecommendations,
  getFleetSummary,
  Engine,
  EngineSensors,
} from '@/lib/engine-utils'
import { fetchFleet, fetchSensors, ApiEngineSnapshot, fetchDatasets, ApiDatasetInfo } from '@/lib/api'

type View = 'home' | 'fleet' | 'engine' | 'agents' | 'recommendations' | 'settings'
type DatasetId = 'FD001' | 'FD002' | 'FD003' | 'FD004'

/** Map API status values to the three-tier EngineStatus used by the UI. */
function toEngineStatus(apiStatus: ApiEngineSnapshot['status']): Engine['status'] {
  if (apiStatus === 'critical') return 'critical'
  if (apiStatus === 'warning' || apiStatus === 'caution') return 'watch'
  return 'healthy'
}

/** Convert an ApiEngineSnapshot into the Engine shape the views expect. */
function snapshotToEngine(snap: ApiEngineSnapshot): Engine {
  return {
    engine_id: snap.id,
    current_cycle: snap.cycleCount,
    predicted_rul: snap.rul,
    status: toEngineStatus(snap.status),
    sensors: {} as EngineSensors,
    last_updated: new Date(),
    rul_history: snap.rulHistory.map((rul, i) => ({
      cycle: snap.cycleCount - (snap.rulHistory.length - 1 - i),
      rul,
    })),
    sensor_history: [],
  }
}

export default function SENDashboard() {
  const [currentView, setCurrentView] = useState<View>('home')
  const [selectedEngine, setSelectedEngine] = useState<Engine | null>(null)
  const [engines, setEngines] = useState<Engine[]>([])
  const [loading, setLoading] = useState(true)
  const [dataset, setDataset] = useState<DatasetId>('FD001')
  const [datasets, setDatasets] = useState<ApiDatasetInfo[]>([])

  // Fetch available datasets on mount.
  useEffect(() => {
    fetchDatasets()
      .then(setDatasets)
      .catch(err => console.error('Datasets fetch failed', err))
  }, [])

  // Fetch fleet data whenever the selected dataset changes.
  useEffect(() => {
    setLoading(true)
    setSelectedEngine(null)
    fetchFleet(dataset)
      .then(snapshots => setEngines(snapshots.map(snapshotToEngine)))
      .catch(err => console.error('Fleet fetch failed — is the API running?', err))
      .finally(() => setLoading(false))
  }, [dataset])

  const agentLogs = useMemo(() => generateAgentLogs(engines), [engines])
  const recommendations = useMemo(() => generateRecommendations(engines), [engines])
  const fleetSummary = useMemo(() => getFleetSummary(engines), [engines])

  const handleSelectEngine = async (engine: Engine) => {
    // Fetch real sensor history before navigating to the detail view.
    try {
      const readings = await fetchSensors(engine.engine_id, 50, dataset)
      const sensor_history = readings.map((r) => ({
        cycle: r.cycle,
        sensors: r.sensors as EngineSensors,
      }))
      const latest = sensor_history[sensor_history.length - 1]
      setSelectedEngine({
        ...engine,
        sensors: latest ? latest.sensors : engine.sensors,
        sensor_history,
      })
    } catch {
      // API unavailable — fall back to the engine without sensor history.
      setSelectedEngine(engine)
    }
    setCurrentView('engine')
  }

  const handleBackFromEngine = () => {
    setSelectedEngine(null)
    setCurrentView('fleet')
  }

  const handleViewChange = (view: View) => {
    if (view !== 'engine') {
      setSelectedEngine(null)
    }
    setCurrentView(view)
  }

  const renderView = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-full text-muted-foreground">
          Loading fleet data…
        </div>
      )
    }

    switch (currentView) {
      case 'home':
        return <HomeView />
      case 'fleet':
        return <FleetView engines={engines} onSelectEngine={handleSelectEngine} />
      case 'engine':
        if (selectedEngine) {
          return <EngineDetailView engine={selectedEngine} onBack={handleBackFromEngine} dataset={dataset} />
        }
        return <FleetView engines={engines} onSelectEngine={handleSelectEngine} />
      case 'agents':
        return <AgentsView logs={agentLogs} />
      case 'recommendations':
        return (
          <RecommendationsView
            recommendations={recommendations}
            engines={engines}
            onSelectEngine={handleSelectEngine}
          />
        )
      case 'settings':
        return <SettingsView />
      default:
        return <HomeView />
    }
  }

  return (
    <div className="flex h-screen bg-background circuit-bg overflow-hidden">
      {/* Particle background */}
      <ParticleBackground />

      {/* Sidebar */}
      <SenSidebar currentView={currentView} onViewChange={handleViewChange} />

      {/* Main content area */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* Dataset selector + Fleet health header */}
        <div className="flex items-center gap-4 px-6 pt-4 pb-0">
          <label className="text-sm text-muted-foreground font-medium">Dataset:</label>
          <select
            value={dataset}
            onChange={(e) => setDataset(e.target.value as DatasetId)}
            className="bg-secondary text-foreground text-sm rounded-md border border-border px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
          >
            {datasets.length > 0 ? datasets.map((d) => (
              <option key={d.dataset_id} value={d.dataset_id} disabled={!d.available}>
                {d.dataset_id} — {d.engines} engines, {d.fault_modes} fault mode(s), {d.operating_conditions} op cond(s)
              </option>
            )) : (
              <>
                <option value="FD001">FD001</option>
                <option value="FD002">FD002</option>
                <option value="FD003">FD003</option>
                <option value="FD004">FD004</option>
              </>
            )}
          </select>
        </div>
        <FleetHeader summary={fleetSummary} />

        {/* Content area */}
        <main className="flex-1 overflow-auto">
          {renderView()}
        </main>
      </div>
    </div>
  )
}
