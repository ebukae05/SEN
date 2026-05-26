import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

interface ProcessingStatusProps {
  state: "running" | "success" | "error";
  message?: string;
  errors?: string[];
  datasetId?: string;
  onReset: () => void;
}

export function ProcessingStatus({
  state,
  message,
  errors = [],
  datasetId,
  onReset,
}: ProcessingStatusProps) {
  if (state === "running") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border bg-surface px-6 py-12">
        <Loader2 className="h-7 w-7 animate-spin text-violet-glow" />
        <p className="text-[13px] text-text">Processing dataset…</p>
        <p className="font-mono text-[11px] text-text-faint">
          CDH → normalize → label → persist
        </p>
      </div>
    );
  }

  if (state === "success") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-status-green/30 bg-status-green/5 px-6 py-10">
        <CheckCircle2 className="h-7 w-7 text-status-green" />
        <p className="text-[13px] font-medium text-text">Dataset ready</p>
        {message && (
          <p className="font-mono text-[11px] text-text-dim">{message}</p>
        )}
        <div className="mt-3 flex items-center gap-2">
          <Link
            to={`/fleet?dataset=${encodeURIComponent(datasetId ?? "")}`}
            className="rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-3 py-1.5 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-violet/35 hover:to-violet/15"
          >
            View in Fleet
          </Link>
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
          >
            Upload Another
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-status-red/30 bg-status-red/5 px-6 py-5">
      <div className="flex items-center gap-2.5">
        <AlertTriangle className="h-5 w-5 text-status-red" />
        <p className="text-[13px] font-medium text-text">Processing failed</p>
      </div>
      {message && <p className="text-[12px] text-text-dim">{message}</p>}
      {errors.length > 0 && (
        <ul className="space-y-1 text-[12px] text-status-red">
          {errors.map((e) => (
            <li key={e} className="flex gap-2">
              <span aria-hidden>•</span>
              <span>{e}</span>
            </li>
          ))}
        </ul>
      )}
      <button
        type="button"
        onClick={onReset}
        className="rounded-md border border-border bg-surface px-3 py-1.5 text-[12px] text-text-dim hover:bg-surface-hover hover:text-text"
      >
        Start Over
      </button>
    </div>
  );
}
