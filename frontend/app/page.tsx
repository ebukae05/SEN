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
import { fetchFleet, fetchSensors, ApiEngineSnapshot } from '@/lib/api'

type View = 'home' | 'fleet' | 'engine' | 'agents' | 'recommendations' | 'settings'

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
    // Sensor readings are fetched on-demand when an engine is selected.
    sensors: Object.fromEntries(
      ['s2','s3','s4','s7','s8','s9','s11','s12','s13','s14','s15','s17','s20','s21'].map(k => [k, 0])
    ) as unknown as EngineSensors,
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

  // Fetch real fleet data from the FastAPI backend on mount.
  useEffect(() => {
    fetchFleet()
      .then(snapshots => setEngines(snapshots.map(snapshotToEngine)))
      .catch(err => console.error('Fleet fetch failed — is the API running?', err))
      .finally(() => setLoading(false))
  }, [])

  const agentLogs = useMemo(() => generateAgentLogs(engines), [engines])
  const recommendations = useMemo(() => generateRecommendations(engines), [engines])
  const fleetSummary = useMemo(() => getFleetSummary(engines), [engines])

  const handleSelectEngine = async (engine: Engine) => {
    // Fetch real sensor history before navigating to the detail view.
    try {
      const readings = await fetchSensors(engine.engine_id)
      const sensor_history = readings.map(({ cycle, ...sensors }) => ({
        cycle,
        sensors: sensors as EngineSensors,
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
          return <EngineDetailView engine={selectedEngine} onBack={handleBackFromEngine} />
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
        {/* Fleet health header */}
        <FleetHeader summary={fleetSummary} />

        {/* Content area */}
        <main className="flex-1 overflow-auto">
          {renderView()}
        </main>
      </div>
    </div>
  )
}
