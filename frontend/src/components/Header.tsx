import { Link } from "react-router-dom";
import { Fragment } from "react";
import { DatasetSelector } from "./DatasetSelector";

interface Crumb {
  label: string;
  to?: string;
}

export function Header({ crumbs }: { crumbs: Crumb[] }) {
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
      <div className="flex items-center gap-3">
        <DatasetSelector />
        <button
          type="button"
          className="rounded-md border border-violet/40 bg-gradient-to-b from-violet/25 to-violet/10 px-3 py-1.5 text-[12px] font-medium text-white shadow-[0_0_24px_rgba(168,85,247,0.25),inset_0_1px_0_rgba(255,255,255,0.1)] hover:from-violet/35 hover:to-violet/15"
        >
          Run Pipeline
        </button>
      </div>
    </header>
  );
}
