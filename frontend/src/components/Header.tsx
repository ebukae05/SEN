import { Link, useNavigate } from "react-router-dom";
import { Fragment, useEffect, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { DatasetSelector } from "./DatasetSelector";
import { api } from "../lib/api";
import { useDataset } from "../lib/datasetContext";

interface Crumb {
  label: string;
  to?: string;
}

async function pickMostCriticalEngine(datasetId: string): Promise<number> {
  const ids = await api.listEngines(datasetId);
  if (ids.length === 0) throw new Error("No engines in active dataset");
  const statuses = await Promise.all(
    ids.map((id) =>
      api.engineStatus(id, datasetId).catch(() => null),
    ),
  );
  const valid = statuses.filter(
    (s): s is NonNullable<typeof s> => s !== null,
  );
  if (valid.length === 0) return ids[0];
  const alerts = valid.filter((s) => s.alert);
  const pool = alerts.length > 0 ? alerts : valid;
  pool.sort((a, b) => a.predicted_rul - b.predicted_rul);
  return pool[0].engine_id;
}

export function Header({ crumbs }: { crumbs: Crumb[] }) {
  const navigate = useNavigate();
  const { activeDatasetId } = useDataset();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!error) return;
    const t = window.setTimeout(() => setError(null), 6000);
    return () => window.clearTimeout(t);
  }, [error]);

  const handleRun = async () => {
    if (running) return;
    setError(null);
    setRunning(true);
    try {
      const engineId = await pickMostCriticalEngine(activeDatasetId);
      await api.analyze(engineId, activeDatasetId);
      navigate("/agents");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Pipeline run failed";
      setError(msg);
    } finally {
      setRunning(false);
    }
  };

  return (
    <header className="relative z-10 flex h-14 items-center justify-between gap-6 border-b border-border bg-bg/60 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        {crumbs.map((c, i) => (
          <Fragment key={i}>
            {i > 0 && <span className="text-text-faint">/</span>}
            {c.to ? (
              <Link to={c.to} className="text-[13px] text-text-dim hover:text-text">
                {c.label}
              </Link>
            ) : (
              <span
                className={
                  i === crumbs.length - 1
                    ? "text-[13px] font-medium text-text"
                    : "text-[13px] text-text-dim"
                }
              >
                {c.label}
              </span>
            )}
          </Fragment>
        ))}
        <span className="ml-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2/80 px-2 py-0.5 font-mono text-[10px] text-text-dim">
          <span className="h-1.5 w-1.5 rounded-full bg-status-green shadow-[0_0_6px_rgba(34,197,94,0.7)]" />
          LIVE
        </span>
      </div>
      <div className="hidden flex-1 justify-center md:flex">
        <button
          type="button"
          className="flex h-8 w-80 items-center gap-2 rounded-md border border-border bg-surface/60 px-2.5 text-[12px] text-text-faint backdrop-blur-sm hover:border-border-strong hover:text-text-dim"
        >
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></svg>
          <span className="flex-1 text-left">Search engines, alerts, reports…</span>
          <kbd className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-faint">⌘K</kbd>
        </button>
      </div>
      <div className="relative flex items-center gap-3">
        <DatasetSelector />
        <button
          type="button"
          onClick={handleRun}
          disabled={running}
          className="flex items-center gap-1.5 rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-3 py-1.5 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-violet/35 hover:to-violet/15 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {running ? "Running…" : "Run Pipeline"}
        </button>
        {error && (
          <div
            role="alert"
            className="absolute top-full right-0 z-50 mt-2 flex max-w-sm items-start gap-2 rounded-md border border-status-red/30 bg-surface/95 px-3 py-2 text-[11px] text-status-red shadow-lg backdrop-blur-sm"
          >
            <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            <span className="font-mono leading-relaxed">{error}</span>
          </div>
        )}
      </div>
    </header>
  );
}
