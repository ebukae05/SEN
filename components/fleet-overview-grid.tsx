"use client"

import { EngineStatus, Severity } from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ChevronDown, AlertCircle } from "lucide-react"
import { useState } from "react"

interface FleetOverviewGridProps {
  statuses: EngineStatus[]
  isLoading: boolean
  onEngineSelect: (engine: EngineStatus) => void
}

type SortOption = "urgency" | "engine_id"

const severityOrder: Record<Severity, number> = {
  critical: 0,
  watch: 1,
  healthy: 2,
}

export function FleetOverviewGrid({ statuses, isLoading, onEngineSelect }: FleetOverviewGridProps) {
  const [sortBy, setSortBy] = useState<SortOption>("urgency")

  const sortedStatuses = [...statuses].sort((a, b) => {
    if (sortBy === "urgency") {
      const severityDiff = severityOrder[a.severity] - severityOrder[b.severity]
      if (severityDiff !== 0) return severityDiff
      return a.predicted_rul - b.predicted_rul
    }
    return a.engine_id - b.engine_id
  })

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-foreground">Fleet Overview</h2>
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <Card key={i} className="bg-card">
              <CardContent className="p-4">
                <Skeleton className="mb-2 h-4 w-16" />
                <Skeleton className="mb-2 h-6 w-20" />
                <Skeleton className="h-5 w-14" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-foreground">Fleet Overview</h2>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="gap-2">
              Sort: {sortBy === "urgency" ? "Urgency" : "Engine ID"}
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setSortBy("urgency")}>
              By Urgency (Critical First)
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setSortBy("engine_id")}>
              By Engine ID
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
        {sortedStatuses.map((status) => (
          <EngineCard
            key={status.engine_id}
            status={status}
            onClick={() => onEngineSelect(status)}
          />
        ))}
      </div>
    </div>
  )
}

interface EngineCardProps {
  status: EngineStatus
  onClick: () => void
}

function EngineCard({ status, onClick }: EngineCardProps) {
  const borderColor = {
    healthy: "border-healthy/30 hover:border-healthy/60",
    watch: "border-watch/30 hover:border-watch/60",
    critical: "border-critical/30 hover:border-critical/60",
  }[status.severity]

  return (
    <Card
      className={`cursor-pointer bg-card transition-all ${borderColor} hover:shadow-lg`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-medium text-muted-foreground">
            Engine #{status.engine_id}
          </span>
          {status.alert && (
            <AlertCircle className="h-4 w-4 text-critical" />
          )}
        </div>
        <div className="mb-2 text-xl font-bold text-foreground">
          {Math.round(status.predicted_rul)} <span className="text-sm font-normal text-muted-foreground">cycles</span>
        </div>
        <Badge variant={status.severity} className="capitalize">
          {status.severity}
        </Badge>
      </CardContent>
    </Card>
  )
}
