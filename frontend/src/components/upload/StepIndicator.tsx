import { Check } from "lucide-react";
import { cn } from "../../lib/cn";

interface StepIndicatorProps {
  current: 1 | 2 | 3;
  labels?: [string, string, string];
}

const DEFAULT_LABELS: [string, string, string] = ["Upload", "Map Sensors", "Confirm"];

export function StepIndicator({ current, labels = DEFAULT_LABELS }: StepIndicatorProps) {
  return (
    <ol className="flex items-center gap-2">
      {labels.map((label, i) => {
        const step = (i + 1) as 1 | 2 | 3;
        const state = step < current ? "done" : step === current ? "active" : "upcoming";
        return (
          <li key={label} className="flex items-center gap-2">
            <div
              className={cn(
                "flex h-6 w-6 items-center justify-center rounded-full border font-mono text-[11px] transition-colors",
                state === "done" && "border-violet bg-violet/15 text-violet-glow",
                state === "active" &&
                  "border-violet bg-violet/20 text-violet-glow shadow-[0_0_12px_rgba(168,85,247,0.45)]",
                state === "upcoming" && "border-border bg-surface text-text-faint",
              )}
            >
              {state === "done" ? <Check className="h-3 w-3" /> : step}
            </div>
            <span
              className={cn(
                "text-[12px]",
                state === "active" ? "text-text" : "text-text-dim",
              )}
            >
              {label}
            </span>
            {i < labels.length - 1 && (
              <span className="mx-2 h-px w-12 bg-border" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
