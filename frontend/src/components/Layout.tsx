import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function Layout() {
  const { pathname } = useLocation();
  const isDetail = pathname.startsWith("/engine/");
  const isAgents = pathname === "/agents";
  const engineId = isDetail ? pathname.split("/")[2] : undefined;

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-text">
      <Sidebar />
      <main className="relative flex flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0">
          <div className="glow-violet absolute inset-x-0 top-0 h-[680px]" />
          <div className="bg-grid absolute inset-x-0 top-0 h-[680px]" />
        </div>
        <Header
          crumbs={
            isDetail
              ? [
                  { label: "Fleet", to: "/" },
                  { label: `Engine #${String(engineId).padStart(3, "0")}` },
                ]
              : isAgents
                ? [{ label: "Agents" }, { label: "Activity" }]
                : [{ label: "Fleet" }, { label: "Overview" }]
          }
        />
        <Outlet />
      </main>
    </div>
  );
}
