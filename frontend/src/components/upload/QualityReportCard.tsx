import { AlertTriangle, CheckCircle2, Info } from "lucide-react";
import type { DataQualityReport, UploadPreview } from "../../lib/types";

interface QualityReportCardProps {
  preview: UploadPreview;
}

interface StatProps {
  label: string;
  value: string;
  tone?: "default" | "warn" | "bad";
}

function Stat({ label, value, tone = "default" }: StatProps) {
  const valueClass =
    tone === "bad"
      ? "text-status-red"
      : tone === "warn"
        ? "text-status-amber"
        : "text-text";
  return (
    <div className="flex flex-col gap-1 rounded-md border border-border bg-surface/60 px-3 py-2.5">
      <span className="text-[10px] uppercase tracking-wider text-text-faint">{label}</span>
      <span className={`font-mono text-[14px] font-medium ${valueClass}`}>{value}</span>
    </div>
  );
}

function reportTone(report: DataQualityReport): "ok" | "warn" | "bad" {
  if (!report.is_valid || report.errors.length > 0) return "bad";
  if (report.warnings.length > 0) return "warn";
  return "ok";
}

export function QualityReportCard({ preview }: QualityReportCardProps) {
  const tone = reportTone(preview.quality);
  const Icon = tone === "ok" ? CheckCircle2 : tone === "warn" ? Info : AlertTriangle;
  const headline =
    tone === "ok"
      ? "Data quality looks clean."
      : tone === "warn"
        ? "Data loaded with warnings."
        : "Data quality issues — fix before continuing.";
  const iconClass =
    tone === "ok"
      ? "text-status-green"
      : tone === "warn"
        ? "text-status-amber"
        : "text-status-red";

  return (
    <section className="space-y-3 rounded-lg border border-border bg-surface px-4 py-4">
      <header className="flex items-center gap-2.5">
        <Icon className={`h-4 w-4 ${iconClass}`} />
        <h3 className="text-[13px] font-medium text-text">{headline}</h3>
      </header>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat label="Rows loaded" value={preview.quality.rows_loaded.toLocaleString()} />
        <Stat
          label="Engines detected"
          value={
            preview.quality.engines_loaded > 0
              ? String(preview.quality.engines_loaded)
              : "—"
          }
        />
        <Stat
          label="Missing values"
          value={String(preview.quality.missing_values)}
          tone={preview.quality.missing_values > 0 ? "warn" : "default"}
        />
        <Stat
          label="Out-of-range"
          value={String(preview.quality.out_of_range_values)}
          tone={preview.quality.out_of_range_values > 0 ? "warn" : "default"}
        />
      </div>
      {preview.quality.errors.length > 0 && (
        <ul className="space-y-1 text-[12px] text-status-red">
          {preview.quality.errors.map((e) => (
            <li key={e} className="flex gap-2">
              <span aria-hidden>•</span>
              <span>{e}</span>
            </li>
          ))}
        </ul>
      )}
      {preview.quality.warnings.length > 0 && (
        <ul className="space-y-1 text-[12px] text-status-amber">
          {preview.quality.warnings.map((w) => (
            <li key={w} className="flex gap-2">
              <span aria-hidden>•</span>
              <span>{w}</span>
            </li>
          ))}
        </ul>
      )}
      <details className="rounded-md border border-border bg-bg/40">
        <summary className="cursor-pointer px-3 py-2 text-[12px] text-text-dim">
          Sample rows ({preview.sample_rows.length})
        </summary>
        <div className="overflow-x-auto px-3 pb-3">
          <table className="w-full font-mono text-[11px]">
            <thead className="text-text-faint">
              <tr>
                {preview.columns.map((c) => (
                  <th key={c} className="py-1 pr-3 text-left font-normal">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.sample_rows.map((row, i) => (
                <tr key={i} className="text-text-dim">
                  {preview.columns.map((c) => (
                    <td key={c} className="py-0.5 pr-3">
                      {row[c] === null || row[c] === undefined ? "—" : String(row[c])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
