import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { FleetSummaryBar } from "../components/FleetSummaryBar";
import { FleetTable } from "../components/FleetTable";
import { makeFleetFromIds, makeMockFleet } from "../lib/mock";
import { useFleetStore } from "../lib/fleetStore";
import { useDataset } from "../lib/datasetContext";
import { CustomDatasetBanner } from "../components/CustomDatasetBanner";
import { api } from "../lib/api";
import type { FleetEngine } from "../lib/types";

function buildMockFor(datasetId: string, isCustom: boolean, engineCount?: number): FleetEngine[] {
  const count = isCustom ? Math.max(5, engineCount ?? 5) : 100;
  return makeMockFleet(count, datasetId);
}

export function Overview() {
  const { activeDataset } = useDataset();
  const datasetId = activeDataset?.dataset_id ?? "FD001";
  const isCustom = activeDataset?.source === "custom";
  const [engines, setEngines] = useState<FleetEngine[]>(() =>
    buildMockFor(datasetId, isCustom, activeDataset?.engine_count),
  );

  useEffect(() => {
    let cancelled = false;
    // Always render mock immediately so the table never flashes empty.
    setEngines(buildMockFor(datasetId, isCustom, activeDataset?.engine_count));
    // For custom datasets, replace with real engine IDs from the backend.
    if (!isCustom) return;
    api
      .listEngines(datasetId)
      .then((ids) => {
        if (cancelled || ids.length === 0) return;
        setEngines(makeFleetFromIds(ids, datasetId));
      })
      .catch(() => {
        // Mock already rendered above — nothing to do.
      });
    return () => {
      cancelled = true;
    };
  }, [datasetId, isCustom, activeDataset?.engine_count]);

  const scrollRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = useFleetStore.getState().scrollY;
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    let frame = 0;
    const onScroll = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        useFleetStore.getState().setScrollY(el.scrollTop);
      });
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      el.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <div
      ref={scrollRef}
      className="relative flex-1 overflow-y-auto px-8 pt-2 pb-16"
    >
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        {activeDataset?.source === "custom" ? (
          <CustomDatasetBanner dataset={activeDataset} />
        ) : (
          <Hero />
        )}
        <FleetSummaryBar engines={engines} />
        <FleetTable engines={engines} />
      </div>
    </div>
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
