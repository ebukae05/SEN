"use client"

import { AnalyzeResponse, Severity } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Activity } from "lucide-react"

interface AgentActivityLogProps {
  analysisResults: AnalyzeResponse[]
  engineSeverities: Record<number, Severity>
}

interface ParsedStep {
  agent: string
  content: string
}

function parseAnalysisResult(result: string): ParsedStep[] {
  const steps: ParsedStep[] = []
  const agentMarkers = ["Monitor:", "Diagnostic:", "Advisor:"]
  
  // Try to split by agent markers
  let remaining = result
  let foundMarkers = false
  
  for (const marker of agentMarkers) {
    const parts = remaining.split(marker)
    if (parts.length > 1) {
      foundMarkers = true
      const agentName = marker.replace(":", "")
      
      // Get content until next marker or end
      let content = parts[1]
      for (const nextMarker of agentMarkers) {
        if (nextMarker !== marker && content.includes(nextMarker)) {
          content = content.split(nextMarker)[0]
        }
      }
      
      if (content.trim()) {
        steps.push({
          agent: agentName,
          content: content.trim(),
        })
      }
    }
  }
  
  // If no markers found, return raw content
  if (!foundMarkers || steps.length === 0) {
    return [{ agent: "Raw", content: result }]
  }
  
  return steps
}

function getAgentColor(agent: string): string {
  switch (agent.toLowerCase()) {
    case "monitor":
      return "text-blue-400"
    case "diagnostic":
      return "text-watch"
    case "advisor":
      return "text-healthy"
    default:
      return "text-muted-foreground"
  }
}

export function AgentActivityLog({ analysisResults, engineSeverities }: AgentActivityLogProps) {
  return (
    <Card className="h-full bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Activity className="h-4 w-4 text-primary" />
          Agent Activity Log
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-64">
          {analysisResults.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No analysis results yet. Run a deep analysis on an engine to see agent activity.
            </div>
          ) : (
            <div className="space-y-4">
              {analysisResults.map((result, index) => {
                const steps = parseAnalysisResult(result.result)
                const severity = engineSeverities[result.engine_id] || "healthy"
                
                return (
                  <div key={`${result.engine_id}-${index}`} className="space-y-2">
                    <div className="flex items-center gap-2 border-b border-border pb-2">
                      <span className="text-sm font-medium text-foreground">
                        Engine #{result.engine_id}
                      </span>
                      <Badge variant={severity} className="capitalize text-xs">
                        {severity}
                      </Badge>
                    </div>
                    {steps.map((step, stepIndex) => (
                      <div key={stepIndex} className="rounded-lg bg-secondary/30 p-3">
                        <div className={`mb-1 text-sm font-semibold ${getAgentColor(step.agent)}`}>
                          {step.agent}
                        </div>
                        <pre className="whitespace-pre-wrap font-mono text-xs text-muted-foreground">
                          {step.content}
                        </pre>
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
