"use client"

import { useState, useEffect, useCallback } from "react"
import useSWR from "swr"
import { toast } from "sonner"
import { 
  getEngines, 
  getEngineStatuses, 
  EngineStatus, 
  AnalyzeResponse,
  Severity 
} from "@/lib/api"
import { FleetHealthSummary } from "@/components/fleet-health-summary"
import { FleetOverviewGrid } from "@/components/fleet-overview-grid"
import { EngineDetailView } from "@/components/engine-detail-view"
import { AgentActivityLog } from "@/components/agent-activity-log"
import { RecommendationsPanel } from "@/components/recommendations-panel"
import { Activity, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"

const fetchFleetData = async (): Promise<EngineStatus[]> => {
  const engineIds = await getEngines()
  const statuses = await getEngineStatuses(engineIds, 10) // batch 10 at a time
  return statuses
}

export function Dashboard() {
  const { data: statuses, error, isLoading, mutate } = useSWR(
    "fleet-statuses",
    fetchFleetData,
    {
      refreshInterval: 60000, // refresh every 60 seconds
      revalidateOnFocus: true,
      onError: (err) => {
        toast.error(`Failed to fetch fleet data: ${err.message}`)
      },
    }
  )

  const [selectedEngine, setSelectedEngine] = useState<EngineStatus | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [analysisResults, setAnalysisResults] = useState<AnalyzeResponse[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)

  // Build a map of engine_id -> severity for the activity log
  const engineSeverities: Record<number, Severity> = {}
  if (statuses) {
    statuses.forEach((s) => {
      engineSeverities[s.engine_id] = s.severity
    })
  }

  const handleEngineSelect = useCallback((engine: EngineStatus) => {
    setSelectedEngine(engine)
    setDetailOpen(true)
  }, [])

  const handleDetailClose = useCallback(() => {
    setDetailOpen(false)
    setSelectedEngine(null)
  }, [])

  const handleAnalysisComplete = useCallback((result: AnalyzeResponse) => {
    setAnalysisResults((prev) => [result, ...prev].slice(0, 10)) // keep last 10
  }, [])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await mutate()
      toast.success("Fleet data refreshed")
    } catch {
      toast.error("Failed to refresh fleet data")
    } finally {
      setIsRefreshing(false)
    }
  }

  const latestAnalysis = analysisResults[0] || null
  const latestEngineSeverity = latestAnalysis 
    ? engineSeverities[latestAnalysis.engine_id] || null 
    : null

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
              <Activity className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">SEN</h1>
              <p className="text-xs text-muted-foreground">Sensor Engine Network</p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={handleRefresh}
            disabled={isRefreshing}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto space-y-6 p-4 md:p-6">
        {/* Fleet Health Summary Bar */}
        <section>
          <FleetHealthSummary 
            statuses={statuses || []} 
            isLoading={isLoading} 
          />
        </section>

        {/* Fleet Overview Grid */}
        <section>
          <FleetOverviewGrid
            statuses={statuses || []}
            isLoading={isLoading}
            onEngineSelect={handleEngineSelect}
          />
        </section>

        {/* Bottom Panels: Activity Log & Recommendations */}
        <section className="grid gap-6 lg:grid-cols-2">
          <AgentActivityLog 
            analysisResults={analysisResults}
            engineSeverities={engineSeverities}
          />
          <RecommendationsPanel 
            latestAnalysis={latestAnalysis}
            engineSeverity={latestEngineSeverity}
          />
        </section>
      </main>

      {/* Engine Detail Dialog */}
      <EngineDetailView
        engine={selectedEngine}
        open={detailOpen}
        onClose={handleDetailClose}
        onAnalysisComplete={handleAnalysisComplete}
      />
    </div>
  )
}
