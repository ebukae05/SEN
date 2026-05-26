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
      { method: "DELETE" },
    );
    if (!res.ok) {
      throw new Error(`${res.status} ${res.statusText}`);
    }
  },
};
