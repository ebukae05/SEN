import {
  Activity,
  AlertTriangle,
  FileText,
  Gauge,
  LayoutGrid,
  LineChart,
  Plane,
  Settings,
  Sparkles,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../lib/cn";

interface NavItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  badge?: string;
  to?: string;
}

function NavItem({ icon: Icon, label, active, badge, to }: NavItemProps) {
  const inner = (
    <>
      {active && (
        <span className="absolute top-1.5 bottom-1.5 -left-2 w-[2px] rounded-r bg-violet-glow shadow-[0_0_8px_rgba(192,132,252,0.7)]" />
      )}
      <Icon
        className={cn(
          "h-4 w-4 shrink-0 transition-colors",
          active && "text-violet-glow",
        )}
      />
      <span className="flex-1 text-left">{label}</span>
      {badge && (
        <span className="rounded bg-status-red/15 px-1.5 py-0.5 font-mono text-[10px] font-medium text-status-red">
          {badge}
        </span>
      )}
    </>
  );
  const classes = cn(
    "group relative flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] font-medium transition-colors",
    active
      ? "bg-surface-hover text-text"
      : "text-text-dim hover:bg-surface-2 hover:text-text",
  );
  return to ? (
    <Link to={to} className={classes}>
      {inner}
    </Link>
  ) : (
    <button type="button" className={classes}>
      {inner}
    </button>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-2.5 pt-5 pb-1.5 text-[11px] font-medium tracking-wider text-text-faint uppercase">
      {children}
    </div>
  );
}

export function Sidebar() {
  const { pathname } = useLocation();
  return (
    <aside className="flex h-full w-60 shrink-0 flex-col border-r border-border bg-bg">
      <Link to="/" className="flex items-center gap-2.5 px-4 py-4">
        <div className="relative flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-violet to-violet-glow shadow-[0_0_12px_rgba(168,85,247,0.5)]">
          <Sparkles className="h-3.5 w-3.5 text-white" />
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[13px] font-semibold text-text">SEN</span>
          <span className="font-mono text-[10px] text-text-faint">v1.0.0</span>
        </div>
      </Link>

      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        <NavItem to="/" icon={LayoutGrid} label="Overview" active={pathname === "/"} />
        <NavItem icon={Plane} label="Fleet" />
        <NavItem icon={AlertTriangle} label="Alerts" badge="7" />
        <NavItem to="/agents" icon={Activity} label="Agents" active={pathname === "/agents"} />

        <SectionLabel>Analysis</SectionLabel>
        <NavItem icon={LineChart} label="Trends" />
        <NavItem icon={Gauge} label="Diagnostics" />
        <NavItem icon={FileText} label="Reports" />

        <SectionLabel>Pinned Engines</SectionLabel>
        <PinnedEngine id={3} severity="critical" rul={8} />
        <PinnedEngine id={17} severity="critical" rul={12} />
        <PinnedEngine id={42} severity="warning" rul={24} />
        <PinnedEngine id={88} severity="warning" rul={29} />
      </nav>

      <div className="border-t border-border px-2 py-3">
        <NavItem icon={Settings} label="Settings" />
      </div>
    </aside>
  );
}

function PinnedEngine({
  id,
  severity,
  rul,
}: {
  id: number;
  severity: "critical" | "warning" | "healthy";
  rul: number;
}) {
  const dot =
    severity === "critical"
      ? "bg-status-red"
      : severity === "warning"
        ? "bg-status-amber"
        : "bg-status-green";
  return (
    <Link
      to={`/engine/${id}`}
      className="group flex w-full items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] text-text-dim transition-colors hover:bg-surface-2 hover:text-text"
    >
      <span
        className={cn(
          "h-1.5 w-1.5 shrink-0 rounded-full",
          dot,
          severity === "critical" && "shadow-[0_0_8px_rgba(239,68,68,0.6)]",
        )}
      />
      <span className="flex-1 text-left">Engine {id}</span>
      <span className="font-mono text-[11px] text-text-faint">{rul}c</span>
    </Link>
  );
}
