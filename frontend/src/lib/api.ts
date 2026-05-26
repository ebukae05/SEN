import type { AnalyzeResponse, EngineStatus } from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE ?? "https://sen-production.up.railway.app";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listEngines: () => request<number[]>("/engines"),
  engineStatus: (id: number) => request<EngineStatus>(`/engine/${id}/status`),
  analyze: (engine_id: number) =>
    request<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify({ engine_id }),
    }),
};
