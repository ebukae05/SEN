import type { AssetType, Industry } from "../../lib/types";

interface AssetMetadataFormProps {
  assetId: string;
  industry: Industry;
  assetType: AssetType;
  onChange: (patch: {
    assetId?: string;
    industry?: Industry;
    assetType?: AssetType;
  }) => void;
}

const INDUSTRIES: Array<{ value: Industry; label: string }> = [
  { value: "oil_gas", label: "Oil & Gas" },
  { value: "power_generation", label: "Power Generation" },
  { value: "heavy_industry", label: "Heavy Industry" },
  { value: "mining", label: "Mining" },
  { value: "aerospace", label: "Aerospace & Defense" },
  { value: "marine", label: "Marine" },
  { value: "wind_energy", label: "Wind Energy" },
  { value: "automotive_manufacturing", label: "Automotive Mfg" },
  { value: "chemical", label: "Chemical" },
  { value: "general_manufacturing", label: "General Mfg" },
];

const ASSET_TYPES: Array<{ value: AssetType; label: string }> = [
  { value: "turbofan_engine", label: "Turbofan Engine" },
  { value: "centrifugal_compressor", label: "Centrifugal Compressor" },
  { value: "gas_turbine", label: "Gas Turbine" },
  { value: "steam_turbine", label: "Steam Turbine" },
  { value: "electric_motor", label: "Electric Motor" },
  { value: "pump", label: "Pump" },
  { value: "gearbox", label: "Gearbox" },
  { value: "wind_turbine_drivetrain", label: "Wind Turbine Drivetrain" },
  { value: "conveyor_drive", label: "Conveyor Drive" },
  { value: "crusher", label: "Crusher" },
  { value: "generator", label: "Generator" },
  { value: "custom", label: "Custom" },
];

export function AssetMetadataForm({
  assetId,
  industry,
  assetType,
  onChange,
}: AssetMetadataFormProps) {
  return (
    <section className="grid gap-3 rounded-lg border border-border bg-surface px-4 py-4 md:grid-cols-3">
      <Field label="Asset ID / Name">
        <input
          value={assetId}
          onChange={(e) => onChange({ assetId: e.target.value })}
          placeholder="compressor-unit-7"
          className="h-8 w-full rounded-md border border-border bg-bg/60 px-2.5 font-mono text-[12px] text-text placeholder:text-text-faint focus:border-violet focus:outline-none"
        />
      </Field>
      <Field label="Industry">
        <select
          value={industry}
          onChange={(e) => onChange({ industry: e.target.value as Industry })}
          className="h-8 w-full rounded-md border border-border bg-bg/60 px-2 text-[12px] text-text focus:border-violet focus:outline-none"
        >
          {INDUSTRIES.map((i) => (
            <option key={i.value} value={i.value}>
              {i.label}
            </option>
          ))}
        </select>
      </Field>
      <Field label="Asset Type">
        <select
          value={assetType}
          onChange={(e) => onChange({ assetType: e.target.value as AssetType })}
          className="h-8 w-full rounded-md border border-border bg-bg/60 px-2 text-[12px] text-text focus:border-violet focus:outline-none"
        >
          {ASSET_TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </Field>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[10px] uppercase tracking-wider text-text-faint">{label}</span>
      {children}
    </label>
  );
}
