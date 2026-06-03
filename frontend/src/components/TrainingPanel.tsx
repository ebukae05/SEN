import { useCallback, useEffect, useRef, useState } from "react";
import { AlertCircle, Brain, CheckCircle2, Loader2, Play, RotateCcw } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/cn";
import type { DatasetMeta, TrainingPhase, TrainingStatus } from "../lib/types";

const POLL_INTERVAL_MS = 3000;

type Phase = TrainingPhase;

function phaseFrom(value: string | undefined | null): Phase {
  switch (value) {
    case "pending":
    case "ready":
    case "training":
    case "trained":
    case "training_failed":
    case "failed":
      return value;
    default:
      return "ready";
  }
}

const PHASE_BADGE: Record<Phase, { label: string; cls: string; dot: string }> = {
  pending: {
    label: "Pending",
    cls: "bg-text-faint/10 text-text-dim border-text-faint/25",
    dot: "bg-text-faint",
  },
  ready: {
    label: "Ready",
    cls: "bg-violet/10 text-violet-glow border-violet/30",
    dot: "bg-violet-glow",
  },
  training: {
    label: "Training",
    cls: "bg-status-amber/10 text-status-amber border-status-amber/25",
    dot: "bg-status-amber",
  },
  trained: {
    label: "Trained",
    cls: "bg-status-green/10 text-status-green border-status-green/25",
    dot: "bg-status-green",
  },
  training_failed: {
    label: "Training failed",
    cls: "bg-status-red/12 text-status-red border-status-red/30",
    dot: "bg-status-red",
  },
  failed: {
    label: "Failed",
    cls: "bg-status-red/12 text-status-red border-status-red/30",
    dot: "bg-status-red",
  },
};

export function TrainingPanel({
  dataset,
  onTrainingComplete,
}: {
  dataset: DatasetMeta;
  onTrainingComplete: () => void;
}) {
  const [phase, setPhase] = useState<Phase>(() => phaseFrom(dataset.status));
  const [rmse, setRmse] = useState<number | null>(dataset.training_rmse ?? null);
  const [nFeatures, setNFeatures] = useState<number | null>(
    dataset.n_features_trained ?? null,
  );
  const [error, setError] = useState<string | null>(dataset.training_error ?? null);
  const [submitting, setSubmitting] = useState(false);
  const pollRef = useRef<number | null>(null);

  const datasetId = dataset.dataset_id;

  // Sync local state when the parent passes in updated dataset meta.
  useEffect(() => {
    setPhase(phaseFrom(dataset.status));
    setRmse(dataset.training_rmse ?? null);
    setNFeatures(dataset.n_features_trained ?? null);
    setError(dataset.training_error ?? null);
  }, [dataset.status, dataset.training_rmse, dataset.n_features_trained, dataset.training_error]);

  const applyStatus = useCallback(
    (s: TrainingStatus) => {
      const next = phaseFrom(s.status);
      setPhase(next);
      setRmse(s.training_rmse);
      setNFeatures(s.n_features_trained);
      setError(s.training_error);
      return next;
    },
    [],
  );

  // Poll while training.
  useEffect(() => {
    if (phase !== "training") return;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await api.getTrainingStatus(datasetId);
        if (cancelled) return;
        const next = applyStatus(s);
        if (next === "trained" || next === "training_failed" || next === "failed") {
          if (pollRef.current !== null) {
            window.clearInterval(pollRef.current);
            pollRef.current = null;
          }
          onTrainingComplete();
        }
      } catch {
        // Transient errors — keep polling.
      }
    };
    // Kick off immediately so the user isn't waiting a full interval.
    tick();
    pollRef.current = window.setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      if (pollRef.current !== null) {
        window.clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [phase, datasetId, applyStatus, onTrainingComplete]);

  const canTrain =
    !submitting &&
    phase !== "training" &&
    (phase === "ready" || phase === "trained" || phase === "training_failed") &&
    dataset.has_rul;

  const handleTrain = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.triggerTraining(datasetId);
      setPhase(phaseFrom(res.status));
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start training";
      setError(msg);
      setPhase("training_failed");
    } finally {
      setSubmitting(false);
    }
  };

  const badge = PHASE_BADGE[phase];

  let buttonLabel = "Train Model";
  let ButtonIcon: typeof Play = Play;
  if (phase === "training") {
    buttonLabel = "Training…";
    ButtonIcon = Loader2;
  } else if (phase === "trained") {
    buttonLabel = "Retrain";
    ButtonIcon = RotateCcw;
  } else if (phase === "training_failed") {
    buttonLabel = "Retry";
    ButtonIcon = RotateCcw;
  }

  const hint = !dataset.has_rul
    ? "RUL labels required to fine-tune. Re-upload with a labeled RUL column."
    : phase === "pending"
      ? "Dataset is still ingesting. Wait for status to become Ready."
      : null;

  return (
    <div className="mt-4 rounded-md border border-border bg-bg/40 px-4 py-3.5">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet/10 text-violet-glow">
            <Brain className="h-3.5 w-3.5" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-medium text-text">Model fine-tuning</span>
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium",
                  badge.cls,
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    badge.dot,
                    phase === "training" && "animate-pulse",
                  )}
                />
                {badge.label}
              </span>
            </div>
            <div className="mt-0.5 flex items-center gap-3 font-mono text-[11px] text-text-faint">
              {phase === "trained" && rmse !== null && (
                <span className="flex items-center gap-1 text-status-green">
                  <CheckCircle2 className="h-3 w-3" />
                  RMSE: {rmse.toFixed(1)} cycles
                </span>
              )}
              {phase === "trained" && nFeatures !== null && (
                <span>n_features: {nFeatures}</span>
              )}
              {phase !== "trained" && phase !== "training" && (
                <span>Train a per-tenant CNN-LSTM on this dataset</span>
              )}
              {phase === "training" && (
                <span className="text-status-amber">
                  Fine-tuning on {dataset.row_count.toLocaleString()} rows · keep this
                  page open
                </span>
              )}
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={handleTrain}
          disabled={!canTrain}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-md border px-3 py-1.5 text-[11px] font-medium transition-colors",
            canTrain
              ? "border-violet/40 bg-violet/15 text-violet-glow hover:bg-violet/25"
              : "border-border bg-surface/60 text-text-faint",
          )}
        >
          <ButtonIcon
            className={cn("h-3.5 w-3.5", phase === "training" && "animate-spin")}
          />
          {buttonLabel}
        </button>
      </div>

      {phase === "training" && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-surface">
          <div className="h-full w-1/3 animate-[trainingBar_1.4s_ease-in-out_infinite] rounded-full bg-violet-glow/70" />
        </div>
      )}

      {phase === "training_failed" && error && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-status-red/25 bg-status-red/8 px-3 py-2 text-[11px] text-status-red">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span className="font-mono leading-relaxed">{error}</span>
        </div>
      )}

      {hint && phase !== "training" && phase !== "training_failed" && (
        <p className="mt-2 text-[11px] text-text-faint">{hint}</p>
      )}
    </div>
  );
}
