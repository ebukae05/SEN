import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Activity, Brain, Filter, Wrench } from "lucide-react";
import { makeMockEvents, makeMockFleet } from "../lib/mock";
import { cn } from "../lib/cn";
import type { AgentEvent, AgentName } from "../lib/types";
import { SeverityBadge } from "../components/SeverityBadge";

const agentMeta: Record<
  AgentName,
  {
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    ring: string;
    role: string;
  }
> = {
  Monitor: {
    icon: Activity,
    color: "text-violet-glow",
    ring: "border-violet/35 bg-violet/10 shadow-[0_0_12px_rgba(168,85,247,0.35)]",
    role: "Real-Time Engine Health",
  },
  Diagnostic: {
    icon: Brain,
    color: "text-status-amber",
    ring: "border-status-amber/35 bg-status-amber/10 shadow-[0_0_12px_rgba(245,158,11,0.3)]",
    role: "Root-Cause Analysis",
  },
  Advisor: {
    icon: Wrench,
    color: "text-status-green",
    ring: "border-status-green/35 bg-status-green/10 shadow-[0_0_12px_rgba(34,197,94,0.3)]",
    role: "Maintenance Planning",
  },
};

export function Agents() {
  const events = useMemo(() => makeMockEvents(makeMockFleet(100), 36), []);
  const [agentFilter, setAgentFilter] = useState<AgentName | "All">("All");

  const filtered = useMemo(
    () =>
      agentFilter === "All"
        ? events
        : events.filter((e) => e.agent === agentFilter),
    [events, agentFilter],
  );

  const counts = useMemo(() => {
    return {
      All: events.length,
      Monitor: events.filter((e) => e.agent === "Monitor").length,
      Diagnostic: events.filter((e) => e.agent === "Diagnostic").length,
      Advisor: events.filter((e) => e.agent === "Advisor").length,
    };
  }, [events]);

  return (
    <div className="relative flex-1 overflow-y-auto px-8 pt-6 pb-16">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <Hero />
        <AgentRoster events={events} />
        <FilterBar
          counts={counts}
          active={agentFilter}
          onChange={setAgentFilter}
        />
        <Feed events={filtered} />
      </div>
    </div>
  );
}

function Hero() {
  return (
    <div className="relative flex flex-col items-start gap-3 pt-2">
      <span className="font-mono text-[11px] tracking-[0.35em] text-violet-glow uppercase">
        Agent Activity
      </span>
      <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-text">
        Live feed from the three-agent pipeline
      </h1>
      <p className="max-w-2xl text-[13px] text-text-dim">
        Every detection, diagnosis, and recommendation produced by the Monitor,
        Diagnostic, and Maintenance Advisor agents — color-coded by severity.
      </p>
    </div>
  );
}

function AgentRoster({ events }: { events: AgentEvent[] }) {
  const agents: AgentName[] = ["Monitor", "Diagnostic", "Advisor"];
  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
      {agents.map((a) => {
        const m = agentMeta[a];
        const Icon = m.icon;
        const agentEvents = events.filter((e) => e.agent === a);
        const last = agentEvents[0];
        return (
          <div
            key={a}
            className="lift relative overflow-hidden rounded-xl border border-border bg-surface/70 p-4 backdrop-blur-sm"
          >
            <div className="flex items-center gap-2.5">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-md border",
                  m.ring,
                )}
              >
                <Icon className={cn("h-4 w-4", m.color)} />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-[13px] font-semibold text-text">{a} Agent</span>
                <span className="font-mono text-[10px] text-text-faint">{m.role}</span>
              </div>
              <span className="ml-auto rounded-md border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-dim">
                {agentEvents.length} events
              </span>
            </div>
            {last && (
              <p className="mt-3 line-clamp-2 text-[12px] text-text-dim">
                Last: {last.title}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function FilterBar({
  counts,
  active,
  onChange,
}: {
  counts: Record<AgentName | "All", number>;
  active: AgentName | "All";
  onChange: (v: AgentName | "All") => void;
}) {
  const options: Array<AgentName | "All"> = ["All", "Monitor", "Diagnostic", "Advisor"];
  return (
    <div className="flex items-center justify-between border-b border-border pb-3">
      <div className="flex items-center gap-1">
        {options.map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            className={cn(
              "rounded-md px-2.5 py-1 text-[12px] font-medium transition-colors",
              active === opt
                ? "bg-surface-hover text-text"
                : "text-text-dim hover:bg-surface-2 hover:text-text",
            )}
          >
            {opt}
            <span className="ml-1.5 font-mono text-[10px] text-text-faint">
              {counts[opt]}
            </span>
          </button>
        ))}
      </div>
      <button
        type="button"
        className="flex items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 py-1 text-[12px] text-text-dim hover:text-text"
      >
        <Filter className="h-3.5 w-3.5" />
        Severity
      </button>
    </div>
  );
}

function Feed({ events }: { events: AgentEvent[] }) {
  const grouped = useMemo(() => {
    const groups: Record<string, AgentEvent[]> = {};
    for (const e of events) {
      const label = relativeGroup(e.ts);
      (groups[label] ??= []).push(e);
    }
    return Object.entries(groups);
  }, [events]);

  return (
    <div className="flex flex-col gap-8">
      {grouped.map(([label, list]) => (
        <section key={label}>
          <div className="mb-3 flex items-center gap-3">
            <span className="font-mono text-[10px] tracking-wider text-text-faint uppercase">
              {label}
            </span>
            <span className="h-px flex-1 bg-border" />
            <span className="font-mono text-[10px] text-text-faint">
              {list.length} events
            </span>
          </div>
          <ol className="relative ml-3 flex flex-col">
            <span className="absolute top-1 bottom-1 left-3 w-px bg-border" />
            {list.map((e) => (
              <EventItem key={e.id} event={e} />
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}

function EventItem({ event }: { event: AgentEvent }) {
  const m = agentMeta[event.agent];
  const Icon = m.icon;
  return (
    <li className="group relative flex gap-4 py-3 pl-10">
      <span
        className={cn(
          "absolute top-3.5 left-0 flex h-6 w-6 items-center justify-center rounded-full border bg-bg",
          m.ring,
        )}
      >
        <Icon className={cn("h-3 w-3", m.color)} />
      </span>
      <div className="flex flex-1 flex-col gap-2 rounded-lg border border-transparent px-3 py-2 transition-colors group-hover:border-border group-hover:bg-surface/50">
        <div className="flex flex-wrap items-center gap-2">
          <span className={cn("text-[12px] font-semibold", m.color)}>
            {event.agent} Agent
          </span>
          <span className="text-text-faint">·</span>
          <Link
            to={`/engine/${event.engine_id}`}
            className="font-mono text-[12px] text-text-dim hover:text-violet-glow"
          >
            Engine #{String(event.engine_id).padStart(3, "0")}
          </Link>
          <SeverityBadge severity={event.severity} />
          <span className="ml-auto font-mono text-[11px] text-text-faint">
            {formatTime(event.ts)}
          </span>
        </div>
        <p className="text-[13px] leading-snug text-text">{event.title}</p>
        <p className="text-[12px] leading-relaxed text-text-dim">{event.detail}</p>
        {event.meta.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {event.meta.map((m) => (
              <span
                key={m.k}
                className="rounded-md border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-dim"
              >
                <span className="text-text-faint">{m.k}:</span> {m.v}
              </span>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

function relativeGroup(ts: number): string {
  const diff = Date.now() - ts;
  const mins = diff / 60000;
  if (mins < 30) return "Last 30 minutes";
  if (mins < 120) return "Last 2 hours";
  if (mins < 360) return "Last 6 hours";
  return "Earlier today";
}

function formatTime(ts: number): string {
  const d = new Date(ts);
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}
