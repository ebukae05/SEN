"use client"

import { useState } from "react"
import { EngineStatus, analyzeEngine, AnalyzeResponse } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle,
  DialogDescription 
} from "@/components/ui/dialog"
import { AlertCircle, Gauge, Loader2, Play, X, TrendingUp } from "lucide-react"
import { toast } from "sonner"

interface EngineDetailViewProps {
  engine: EngineStatus | null
  open: boolean
  onClose: () => void
  onAnalysisComplete: (result: AnalyzeResponse) => void
}

export function EngineDetailView({ engine, open, onClose, onAnalysisComplete }: EngineDetailViewProps) {
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<string | null>(null)

  if (!engine) return null

  const handleRunAnalysis = async () => {
    setIsAnalyzing(true)
    setAnalysisResult(null)
    
    try {
      const result = await analyzeEngine(engine.engine_id)
      setAnalysisResult(result.result)
      onAnalysisComplete(result)
      toast.success(`Analysis complete for Engine #${engine.engine_id}`)
    } catch (error) {
      toast.error(`Failed to analyze engine: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsAnalyzing(false)
    }
  }

  const rulPercentage = Math.min(100, Math.max(0, (engine.predicted_rul / 200) * 100))
  const thresholdPercentage = (engine.threshold / 200) * 100

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="text-xl">
              Engine #{engine.engine_id}
            </DialogTitle>
            <Badge variant={engine.severity} className="capitalize">
              {engine.severity}
            </Badge>
          </div>
          <DialogDescription>
            Detailed view and analysis for this engine unit
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 overflow-y-auto flex-1">
          {/* RUL Display */}
          <Card className="bg-secondary/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Remaining Useful Life</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-5xl font-bold text-foreground">
                      {Math.round(engine.predicted_rul)}
                    </span>
                    <span className="text-xl text-muted-foreground">cycles</span>
                  </div>
                </div>
                <Gauge className="h-12 w-12 text-primary" />
              </div>

              {/* RUL Progress Bar */}
              <div className="mt-4">
                <div className="relative h-4 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      engine.severity === "critical"
                        ? "bg-critical"
                        : engine.severity === "watch"
                        ? "bg-watch"
                        : "bg-healthy"
                    }`}
                    style={{ width: `${rulPercentage}%` }}
                  />
                  {/* Threshold marker */}
                  <div
                    className="absolute top-0 h-full w-0.5 bg-foreground/50"
                    style={{ left: `${thresholdPercentage}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-xs text-muted-foreground">
                  <span>0</span>
                  <span className="flex items-center gap-1">
                    <span className="inline-block h-2 w-2 bg-foreground/50 rounded-full" />
                    Threshold: {engine.threshold}
                  </span>
                  <span>200</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Alert Status */}
          {engine.alert && (
            <div className="flex items-center gap-2 rounded-lg bg-critical/10 p-3 text-critical">
              <AlertCircle className="h-5 w-5" />
              <span className="font-medium">Alert Active: RUL below threshold ({engine.threshold} cycles)</span>
            </div>
          )}

          {/* Run Analysis Button */}
          <Button
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="w-full gap-2"
            size="lg"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running Deep Analysis (30-60s)...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run Deep Analysis
              </>
            )}
          </Button>

          {/* Analysis Result */}
          {analysisResult && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Analysis Result</CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea className="h-48">
                  <pre className="whitespace-pre-wrap font-mono text-sm text-muted-foreground">
                    {analysisResult}
                  </pre>
                </ScrollArea>
              </CardContent>
            </Card>
          )}

          {/* Sensor Trends Placeholder */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <TrendingUp className="h-4 w-4" />
                Sensor Trends
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex h-32 items-center justify-center rounded-lg border border-dashed border-border bg-muted/20">
                <p className="text-sm text-muted-foreground">
                  {/* TODO: Sensor history endpoint coming soon */}
                  Sensor history endpoint coming soon
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      </DialogContent>
    </Dialog>
  )
}
