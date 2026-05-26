import { useEffect, useRef, useState } from "react";
import { ChevronDown, Check, Database } from "lucide-react";
import { useDataset } from "../lib/datasetContext";
import { cn } from "../lib/cn";

const INDUSTRY_LABEL: Record<string, string> = {
  oil_gas: "Oil & Gas",
  power_generation: "Power Gen",
  heavy_industry: "Heavy Industry",
  mining: "Mining",
  aerospace: "Aerospace",
  marine: "Marine",
  wind_energy: "Wind",
  automotive_manufacturing: "Automotive",
  chemical: "Chemical",
  general_manufacturing: "Mfg",
};

export function DatasetSelector() {
  const { datasets, activeDataset, activeDatasetId, setActiveDatasetId } = useDataset();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [open]);

  const cmapssDatasets = datasets.filter((d) => d.source === "cmapss");
  const customDatasets = datasets.filter((d) => d.source === "custom");

  const activeLabel = activeDataset?.label ?? activeDatasetId;
  const activeIndustry =
    activeDataset && activeDataset.source === "custom"
      ? INDUSTRY_LABEL[activeDataset.industry] ?? activeDataset.industry
      : "CNN-LSTM";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((p) => !p)}
        className="flex items-center gap-2 rounded-md border border-border bg-surface/80 px-2.5 py-1.5 text-[11px] text-text-dim hover:border-border-strong hover:bg-surface-hover hover:text-text"
      >
        <Database className="h-3.5 w-3.5" />
        <span className="font-mono text-text">{activeLabel}</span>
        <span className="text-text-faint">·</span>
        <span className="font-mono text-text-faint">{activeIndustry}</span>
        <ChevronDown className="h-3 w-3 text-text-faint" />
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-72 rounded-lg border border-border bg-surface shadow-[0_8px_32px_rgba(0,0,0,0.5)] backdrop-blur-md">
          <Section title="CMAPSS Datasets">
            {cmapssDatasets.map((d) => (
              <Item
                key={d.dataset_id}
                label={d.label}
                hint={`${d.sensor_count} sensors · ${d.engine_count} engines`}
                active={d.dataset_id === activeDatasetId}
                onClick={() => {
                  setActiveDatasetId(d.dataset_id);
                  setOpen(false);
                }}
              />
            ))}
          </Section>
          {customDatasets.length > 0 && (
            <Section title="Custom Datasets">
              {customDatasets.map((d) => (
                <Item
                  key={d.dataset_id}
                  label={d.label}
                  hint={
                    `${INDUSTRY_LABEL[d.industry] ?? d.industry} · ` +
                    `${d.sensor_count} sensors · ${d.engine_count} engines`
                  }
                  active={d.dataset_id === activeDatasetId}
                  onClick={() => {
                    setActiveDatasetId(d.dataset_id);
                    setOpen(false);
                  }}
                />
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-border last:border-b-0">
      <div className="px-3 pb-1 pt-3 text-[10px] uppercase tracking-wider text-text-faint">
        {title}
      </div>
      <ul className="pb-2">{children}</ul>
    </div>
  );
}

function Item({
  label,
  hint,
  active,
  onClick,
}: {
  label: string;
  hint: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={cn(
          "flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-[12px]",
          active ? "bg-violet/10 text-violet-glow" : "text-text-dim hover:bg-surface-hover hover:text-text",
        )}
      >
        <div className="flex flex-col">
          <span className="font-mono text-[12px]">{label}</span>
          <span className="font-mono text-[10px] text-text-faint">{hint}</span>
        </div>
        {active && <Check className="h-3.5 w-3.5" />}
      </button>
    </li>
  );
}
