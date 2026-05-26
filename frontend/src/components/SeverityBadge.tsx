import { cn } from "../lib/cn";
import type { Severity } from "../lib/types";

const styles: Record<Severity, string> = {
  healthy: "bg-status-green/10 text-status-green border-status-green/25",
  warning: "bg-status-amber/10 text-status-amber border-status-amber/25",
  critical: "bg-status-red/12 text-status-red border-status-red/30",
};

const labels: Record<Severity, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        styles[severity],
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          severity === "healthy" && "bg-status-green",
          severity === "warning" && "bg-status-amber",
          severity === "critical" && "bg-status-red pulse-red",
        )}
      />
      {labels[severity]}
    </span>
  );
}
