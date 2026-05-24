"use client"

import { AnalyzeResponse, Severity } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { FileText, Download } from "lucide-react"

interface RecommendationsPanelProps {
  latestAnalysis: AnalyzeResponse | null
  engineSeverity: Severity | null
}

export function RecommendationsPanel({ latestAnalysis, engineSeverity }: RecommendationsPanelProps) {
  // TODO: PDF generation is server-side, not yet exposed
  const handleDownloadPdf = () => {
    // Placeholder - PDF endpoint not available yet
    alert("PDF generation endpoint coming soon")
  }

  return (
    <Card className="h-full bg-card">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <FileText className="h-4 w-4 text-primary" />
          Recommendations
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!latestAnalysis ? (
          <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            Run a deep analysis on an engine to see recommendations.
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">
                  Engine #{latestAnalysis.engine_id}
                </span>
                {engineSeverity && (
                  <Badge variant={engineSeverity} className="capitalize">
                    {engineSeverity}
                  </Badge>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="gap-2"
                onClick={handleDownloadPdf}
              >
                <Download className="h-4 w-4" />
                Download PDF
                {/* TODO: Link to /analyze response when PDF generation is server-side exposed */}
              </Button>
            </div>
            <ScrollArea className="h-40">
              <pre className="whitespace-pre-wrap font-mono text-sm text-muted-foreground">
                {latestAnalysis.result}
              </pre>
            </ScrollArea>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
