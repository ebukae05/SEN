import { useMemo } from "react";
import { Sidebar } from "./components/Sidebar";
import { FleetSummaryBar } from "./components/FleetSummaryBar";
import { FleetTable } from "./components/FleetTable";
import { makeMockFleet } from "./lib/mock";

function App() {
  const engines = useMemo(() => makeMockFleet(100), []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-text">
      <Sidebar />
      <main className="relative flex flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="glow-violet absolute inset-x-0 top-0 h-[680px]" />
          <div className="bg-grid absolute inset-x-0 top-0 h-[680px]" />
        </div>
        <Header />
        <div className="relative flex-1 overflow-y-auto px-8 pt-2 pb-16">
          <div className="mx-auto flex max-w-7xl flex-col gap-8">
            <Hero />
            <FleetSummaryBar engines={engines} />
            <FleetTable engines={engines} />
          </div>
        </div>
      </main>
    </div>
  );
}

function Header() {
  return (
    <header className="relative z-10 flex h-14 items-center justify-between gap-6 border-b border-border bg-bg/60 px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <span className="text-[13px] text-text-dim">Fleet</span>
        <span className="text-text-faint">/</span>
        <span className="text-[13px] font-medium text-text">Overview</span>
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
        <span className="hidden font-mono text-[11px] text-text-faint lg:inline">
          FD001 · CNN-LSTM
        </span>
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

function Hero() {
  return (
    <div className="relative flex flex-col items-center pt-12 pb-2 text-center">
      <div className="mb-4 flex items-center gap-2">
        <span className="font-mono text-[11px] tracking-[0.35em] text-violet-glow uppercase">
          Sensor Engine Network
        </span>
      </div>
      <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-violet/25 bg-violet/10 px-3 py-1 backdrop-blur-sm">
        <span className="h-1.5 w-1.5 rounded-full bg-violet-glow shadow-[0_0_8px_rgba(192,132,252,0.8)]" />
        <span className="text-[11px] font-medium tracking-wide text-violet-glow">
          Three-agent diagnostic pipeline
        </span>
      </div>
      <h1 className="max-w-3xl bg-gradient-to-b from-white via-white to-white/60 bg-clip-text text-[52px] leading-[1.05] font-semibold tracking-tight text-transparent">
        Predictive maintenance
        <br />
        for rotating machinery
      </h1>
      <p className="mt-5 max-w-xl text-[14px] leading-relaxed text-text-dim">
        CNN-LSTM remaining useful life forecasts streamed through Monitor,
        Diagnostic, and Advisor agents. Sensor-agnostic. Real-time.
      </p>

      <div className="mt-10 grid w-full max-w-4xl grid-cols-1 gap-4 text-left md:grid-cols-2">
        <ProblemSolutionCard
          tag="The problem"
          tagColor="red"
          title="Unplanned failures cost millions"
          body="Turbofan engines and rotating machinery fail without warning. Reactive maintenance grounds aircraft, halts production lines, and turns routine cycles into emergency repairs — costing operators thousands per hour of downtime."
        />
        <ProblemSolutionCard
          tag="Our solution"
          tagColor="violet"
          title="Forecast, diagnose, recommend"
          body="SEN streams live sensor data through a CNN-LSTM to predict remaining useful life, then three coordinated agents diagnose root causes and generate maintenance plans before failure — turning downtime into scheduled action."
        />
      </div>
    </div>
  );
}

function ProblemSolutionCard({
  tag,
  tagColor,
  title,
  body,
}: {
  tag: string;
  tagColor: "red" | "violet";
  title: string;
  body: string;
}) {
  const tagStyles =
    tagColor === "red"
      ? "border-status-red/30 bg-status-red/10 text-status-red"
      : "border-violet/30 bg-violet/10 text-violet-glow";
  return (
    <div className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 px-5 py-5 backdrop-blur-sm">
      <span
        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wider uppercase ${tagStyles}`}
      >
        {tag}
      </span>
      <h3 className="mt-3 text-[16px] font-semibold tracking-tight text-text">
        {title}
      </h3>
      <p className="mt-2 text-[13px] leading-relaxed text-text-dim">{body}</p>
    </div>
  );
}

export default App;
