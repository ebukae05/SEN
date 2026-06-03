import { Database, Trash2 } from "lucide-react";
import { useState } from "react";
import { api } from "../lib/api";
import { useDataset } from "../lib/datasetContext";
import type { DatasetMeta } from "../lib/types";
import { TrainingPanel } from "./TrainingPanel";

const INDUSTRY_LABEL: Record<string, string> = {
  oil_gas: "Oil & Gas",
  power_generation: "Power Generation",
  heavy_industry: "Heavy Industry",
  mining: "Mining",
  aerospace: "Aerospace & Defense",
  marine: "Marine",
  wind_energy: "Wind Energy",
  automotive_manufacturing: "Automotive Mfg",
  chemical: "Chemical",
  general_manufacturing: "General Mfg",
};

const ASSET_LABEL: Record<string, string> = {
  turbofan_engine: "Turbofan Engine",
  centrifugal_compressor: "Centrifugal Compressor",
  gas_turbine: "Gas Turbine",
  steam_turbine: "Steam Turbine",
  electric_motor: "Electric Motor",
  pump: "Pump",
  gearbox: "Gearbox",
  wind_turbine_drivetrain: "Wind Turbine Drivetrain",
  conveyor_drive: "Conveyor Drive",
  crusher: "Crusher",
  generator: "Generator",
  custom: "Custom",
};

export function CustomDatasetBanner({
  dataset,
  onTrainingComplete,
}: {
  dataset: DatasetMeta;
  onTrainingComplete?: () => void | Promise<void>;
}) {
  const { refresh, setActiveDatasetId } = useDataset();
  const [busy, setBusy] = useState(false);

  const handleTrainingComplete = async () => {
    await refresh();
    if (onTrainingComplete) await onTrainingComplete();
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete dataset "${dataset.asset_id}"?`)) return;
    setBusy(true);
    try {
      await api.deleteDataset(dataset.dataset_id);
      setActiveDatasetId("FD001");
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Delete failed";
      window.alert(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="lift relative overflow-hidden rounded-xl border border-violet/30 bg-gradient-to-br from-violet/10 via-surface/70 to-surface/70 px-6 py-5 backdrop-blur-sm">
      <div className="flex items-start justify-between gap-6">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-violet/15 text-violet-glow">
            <Database className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-[18px] font-semibold text-text">{dataset.asset_id}</h2>
            <p className="font-mono text-[11px] text-text-faint">
              {INDUSTRY_LABEL[dataset.industry] ?? dataset.industry} ·{" "}
              {ASSET_LABEL[dataset.asset_type] ?? dataset.asset_type} · custom dataset
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleDelete}
          disabled={busy}
          className="flex items-center gap-1.5 rounded-md border border-border bg-surface/80 px-2.5 py-1.5 text-[11px] text-text-dim hover:border-status-red/40 hover:text-status-red disabled:opacity-50"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </button>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Engines" value={String(dataset.engine_count)} />
        <Stat label="Sensors" value={String(dataset.sensor_count)} />
        <Stat label="Rows" value={dataset.row_count.toLocaleString()} />
        <Stat label="RUL" value={dataset.has_rul ? "Labeled" : "Heuristic"} />
      </div>
      <TrainingPanel dataset={dataset} onTrainingComplete={handleTrainingComplete} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg/40 px-3 py-2">
      <span className="block text-[10px] uppercase tracking-wider text-text-faint">
        {label}
      </span>
      <span className="font-mono text-[14px] text-text">{value}</span>
    </div>
  );
}
