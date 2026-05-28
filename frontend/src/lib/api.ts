import type {
  AnalyzeResponse,
  DatasetMeta,
  EngineStatus,
  ProcessResult,
  SensorSchemaPayload,
  UploadPreview,
} from "./types";

const API_BASE =
  import.meta.env.VITE_API_BASE ?? "https://sen-production.up.railway.app";

const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function authHeaders(extra?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {};
  if (API_KEY) headers["X-API-Key"] = API_KEY;
  if (extra) Object.assign(headers, extra as Record<string, string>);
  return headers;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: authHeaders({ "Content-Type": "application/json", ...(init?.headers as Record<string, string> | undefined) }),
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText} — ${path}`);
  }
  return res.json() as Promise<T>;
}

function withDataset(path: string, datasetId?: string): string {
  if (!datasetId) return path;
  const join = path.includes("?") ? "&" : "?";
  return `${path}${join}dataset=${encodeURIComponent(datasetId)}`;
}

export const api = {
  listEngines: (datasetId?: string) =>
    request<number[]>(withDataset("/engines", datasetId)),
  engineStatus: (id: number, datasetId?: string) =>
    request<EngineStatus>(withDataset(`/engine/${id}/status`, datasetId)),
  analyze: (engine_id: number, datasetId?: string) =>
    request<AnalyzeResponse>(withDataset("/analyze", datasetId), {
      method: "POST",
      body: JSON.stringify({ engine_id }),
    }),

  uploadFile: async (file: File): Promise<UploadPreview> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/ingest/upload`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {
        // fall through
      }
      throw new Error(`${res.status} — ${detail}`);
    }
    return res.json() as Promise<UploadPreview>;
  },

  submitSchema: (schema: SensorSchemaPayload) =>
    request<ProcessResult>("/ingest/schema", {
      method: "POST",
      body: JSON.stringify(schema),
    }),

  listDatasets: () => request<DatasetMeta[]>("/ingest/datasets"),

  deleteDataset: async (datasetId: string): Promise<void> => {
    const res = await fetch(
      `${API_BASE}/ingest/dataset/${encodeURIComponent(datasetId)}`,
      { method: "DELETE", headers: authHeaders() },
    );
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`);
    }
  },
};
