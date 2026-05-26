import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { mockDatasets } from "./mock";
import type { DatasetMeta } from "./types";

const STORAGE_KEY = "sen.activeDataset";
const DEFAULT_DATASET = "FD001";

interface DatasetContextValue {
  datasets: DatasetMeta[];
  activeDatasetId: string;
  activeDataset: DatasetMeta | undefined;
  setActiveDatasetId: (id: string) => void;
  refresh: () => Promise<void>;
  loading: boolean;
}

const DatasetContext = createContext<DatasetContextValue | undefined>(undefined);

function readStored(): string {
  if (typeof window === "undefined") return DEFAULT_DATASET;
  return window.localStorage.getItem(STORAGE_KEY) || DEFAULT_DATASET;
}

export function DatasetProvider({ children }: { children: React.ReactNode }) {
  const [datasets, setDatasets] = useState<DatasetMeta[]>(mockDatasets);
  const [activeDatasetId, setActive] = useState<string>(readStored());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const fetched = await api.listDatasets();
      setDatasets(fetched.length > 0 ? fetched : mockDatasets);
    } catch {
      setDatasets(mockDatasets);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const setActiveDatasetId = useCallback((id: string) => {
    setActive(id);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, id);
    }
  }, []);

  const activeDataset = useMemo(
    () => datasets.find((d) => d.dataset_id === activeDatasetId),
    [datasets, activeDatasetId],
  );

  const value = useMemo<DatasetContextValue>(
    () => ({ datasets, activeDatasetId, activeDataset, setActiveDatasetId, refresh, loading }),
    [datasets, activeDatasetId, activeDataset, setActiveDatasetId, refresh, loading],
  );

  return <DatasetContext.Provider value={value}>{children}</DatasetContext.Provider>;
}

export function useDataset(): DatasetContextValue {
  const ctx = useContext(DatasetContext);
  if (!ctx) {
    throw new Error("useDataset must be used inside DatasetProvider");
  }
  return ctx;
}
