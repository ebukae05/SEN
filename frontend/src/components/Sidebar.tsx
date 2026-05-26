import {
  Activity,
  AlertTriangle,
  FileText,
  Gauge,
  LineChart,
  Plane,
  Settings,
  Sparkles,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import { cn } from "../lib/cn";

// ─── Animation variants ───────────────────────────────────────────────────────

const sidebarVariants = {
  open: { width: "15rem" },
  closed: { width: "3.5rem" },
};

const transitionProps = {
  type: "tween" as const,
  ease: "easeOut" as const,
  duration: 0.2,
};

const labelVariants = {
  open: { opacity: 1, x: 0, display: "block" },
  closed: { opacity: 0, x: -8, transitionEnd: { display: "none" } },
};

// ─── NavItem ──────────────────────────────────────────────────────────────────

interface NavItemProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  active?: boolean;
  badge?: string;
  to?: string;
  isCollapsed: boolean;
}

function NavItem({ icon: Icon, label, active, badge, to, isCollapsed }: NavItemProps) {
  const inner = (
    <>
      {active && (
        <span className="absolute top-1.5 bottom-1.5 -left-2 w-[2px] rounded-r bg-violet-glow shadow-[0_0_8px_rgba(192,132,252,0.7)]" />
      )}
      <Icon
        className={cn(
          "h-4 w-4 shrink-0 transition-colors",
          active ? "text-violet-glow" : "",
        )}
      />
      <motion.span
        variants={labelVariants}
        animate={isCollapsed ? "closed" : "open"}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className="flex flex-1 items-center justify-between overflow-hidden whitespace-nowrap"
      >
        <span>{label}</span>
        {badge && (
          <span className="rounded bg-status-red/15 px-1.5 py-0.5 font-mono text-[10px] font-medium text-status-red">
            {badge}
          </span>
        )}
      </motion.span>
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

// ─── SectionLabel ─────────────────────────────────────────────────────────────

function SectionLabel({
  children,
  isCollapsed,
}: {
  children: React.ReactNode;
  isCollapsed: boolean;
}) {
  return (
    <motion.div
      variants={labelVariants}
      animate={isCollapsed ? "closed" : "open"}
      transition={{ duration: 0.15, ease: "easeOut" }}
      className="overflow-hidden whitespace-nowrap px-2.5 pt-5 pb-1.5 text-[11px] font-medium tracking-wider text-text-faint uppercase"
    >
      {children}
    </motion.div>
  );
}

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export function Sidebar() {
  const { pathname } = useLocation();
  const [isCollapsed, setIsCollapsed] = useState(true);

  return (
    <motion.aside
      className="relative flex h-full shrink-0 flex-col border-r border-border bg-bg overflow-hidden z-30"
      variants={sidebarVariants}
      initial="closed"
      animate={isCollapsed ? "closed" : "open"}
      transition={transitionProps}
      onMouseEnter={() => setIsCollapsed(false)}
      onMouseLeave={() => setIsCollapsed(true)}
    >
      {/* Logo */}
      <Link to="/fleet" className="flex items-center gap-2.5 px-[0.65rem] py-4 shrink-0">
        <div className="relative flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-violet to-violet-glow shadow-[0_0_12px_rgba(168,85,247,0.5)]">
          <Sparkles className="h-3.5 w-3.5 text-white" />
        </div>
        <motion.div
          variants={labelVariants}
          animate={isCollapsed ? "closed" : "open"}
          transition={{ duration: 0.15, ease: "easeOut" }}
          className="flex flex-col leading-tight overflow-hidden whitespace-nowrap"
        >
          <span className="text-[13px] font-semibold text-text">SEN</span>
          <span className="font-mono text-[10px] text-text-faint">v1.0.0</span>
        </motion.div>
      </Link>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden px-2 pb-4">
        <NavItem
          to="/fleet"
          icon={Plane}
          label="Fleet Overview"
          active={pathname === "/" || pathname === "/fleet"}
          isCollapsed={isCollapsed}
        />
        <NavItem
          icon={AlertTriangle}
          label="Alerts"
          badge="7"
          isCollapsed={isCollapsed}
        />
        <NavItem
          to="/agents"
          icon={Activity}
          label="Agents"
          active={pathname === "/agents"}
          isCollapsed={isCollapsed}
        />

        <SectionLabel isCollapsed={isCollapsed}>Analysis</SectionLabel>
        <NavItem icon={LineChart} label="Trends" isCollapsed={isCollapsed} />
        <NavItem icon={Gauge} label="Diagnostics" isCollapsed={isCollapsed} />
        <NavItem
          to="/recommendations"
          icon={FileText}
          label="Recommendations"
          active={pathname === "/recommendations"}
          isCollapsed={isCollapsed}
        />

        <SectionLabel isCollapsed={isCollapsed}>Pinned Engines</SectionLabel>
        <PinnedEngine id={3} severity="critical" rul={8} isCollapsed={isCollapsed} />
        <PinnedEngine id={17} severity="critical" rul={12} isCollapsed={isCollapsed} />
        <PinnedEngine id={42} severity="warning" rul={24} isCollapsed={isCollapsed} />
        <PinnedEngine id={88} severity="warning" rul={29} isCollapsed={isCollapsed} />
      </nav>

      {/* Bottom */}
      <div className="border-t border-border px-2 py-3 shrink-0">
        <NavItem icon={Settings} label="Settings" isCollapsed={isCollapsed} />
      </div>
    </motion.aside>
  );
}

// ─── PinnedEngine ─────────────────────────────────────────────────────────────

function PinnedEngine({
  id,
  severity,
  rul,
  isCollapsed,
}: {
  id: number;
  severity: "critical" | "warning" | "healthy";
  rul: number;
  isCollapsed: boolean;
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
      <motion.span
        variants={labelVariants}
        animate={isCollapsed ? "closed" : "open"}
        transition={{ duration: 0.15, ease: "easeOut" }}
        className="flex flex-1 items-center justify-between overflow-hidden whitespace-nowrap"
      >
        <span>Engine {id}</span>
        <span className="font-mono text-[11px] text-text-faint">{rul}c</span>
      </motion.span>
    </Link>
  );
}
