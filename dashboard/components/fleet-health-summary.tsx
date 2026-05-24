"use client"

import { EngineStatus } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Activity, AlertTriangle, CheckCircle, Gauge, Server } from "lucide-react"

interface FleetHealthSummaryProps {
  statuses: EngineStatus[]
  isLoading: boolean
}

export function FleetHealthSummary({ statuses, isLoading }: FleetHealthSummaryProps) {
  const totalEngines = statuses.length
  const healthyCount = statuses.filter(s => s.severity === "healthy").length
  const watchCount = statuses.filter(s => s.severity === "watch").length
  const criticalCount = statuses.filter(s => s.severity === "critical").length
  const alertCount = statuses.filter(s => s.alert).length
  const avgRul = totalEngines > 0 
    ? Math.round(statuses.reduce((acc, s) => acc + s.predicted_rul, 0) / totalEngines)
    : 0

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="bg-card">
            <CardHeader className="pb-2">
              <Skeleton className="h-4 w-24" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-8 w-16" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const metrics = [
    {
      label: "Total Engines",
      value: totalEngines,
      icon: Server,
      color: "text-foreground",
    },
    {
      label: "Healthy",
      value: healthyCount,
      icon: CheckCircle,
      color: "text-healthy",
    },
    {
      label: "Watch",
      value: watchCount,
      icon: Activity,
      color: "text-watch",
    },
    {
      label: "Critical",
      value: criticalCount,
      icon: AlertTriangle,
      color: "text-critical",
    },
    {
      label: "Avg RUL",
      value: `${avgRul} cycles`,
      icon: Gauge,
      color: "text-primary",
    },
    {
      label: "Active Alerts",
      value: alertCount,
      icon: AlertTriangle,
      color: alertCount > 0 ? "text-critical" : "text-muted-foreground",
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
      {metrics.map((metric) => (
        <Card key={metric.label} className="bg-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {metric.label}
            </CardTitle>
            <metric.icon className={`h-4 w-4 ${metric.color}`} />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${metric.color}`}>
              {metric.value}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
