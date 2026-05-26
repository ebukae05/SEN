import type {
  ColumnRole,
  SensorMapping,
  SensorTypeTag,
} from "../../lib/types";
import { cn } from "../../lib/cn";

interface SensorMappingTableProps {
  mappings: SensorMapping[];
  onChange: (index: number, patch: Partial<SensorMapping>) => void;
}

const ROLES: ColumnRole[] = ["unit_id", "cycle", "sensor", "rul", "ignore"];

const TYPE_TAGS: SensorTypeTag[] = [
  "vibration",
  "temperature",
  "pressure",
  "speed",
  "current",
  "flow",
  "oil_quality",
  "acoustic",
  "humidity",
  "voltage",
  "custom",
];

const ROLE_TONE: Record<ColumnRole, string> = {
  unit_id: "border-violet/50 bg-violet/15 text-violet-glow",
  cycle: "border-status-green/40 bg-status-green/10 text-status-green",
  sensor: "border-border-strong bg-surface-2 text-text",
  rul: "border-status-amber/40 bg-status-amber/10 text-status-amber",
  ignore: "border-border bg-surface text-text-faint",
};

export function SensorMappingTable({ mappings, onChange }: SensorMappingTableProps) {
  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-surface">
      <table className="w-full text-[12px]">
        <thead className="border-b border-border bg-surface-2 text-[10px] uppercase tracking-wider text-text-faint">
          <tr>
            <th className="px-3 py-2.5 text-left font-medium">Column</th>
            <th className="px-3 py-2.5 text-left font-medium">Role</th>
            <th className="px-3 py-2.5 text-left font-medium">Display Name</th>
            <th className="px-3 py-2.5 text-left font-medium">Type</th>
            <th className="px-3 py-2.5 text-left font-medium">Unit</th>
            <th className="px-3 py-2.5 text-left font-medium">Warning</th>
            <th className="px-3 py-2.5 text-left font-medium">Critical</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((m, i) => {
            const disabled = m.role !== "sensor";
            return (
              <tr
                key={m.column_name}
                className="border-b border-border last:border-b-0 hover:bg-surface-hover"
              >
                <td className="px-3 py-2 font-mono text-[11.5px] text-text">
                  {m.column_name}
                </td>
                <td className="px-3 py-2">
                  <select
                    value={m.role}
                    onChange={(e) =>
                      onChange(i, { role: e.target.value as ColumnRole })
                    }
                    className={cn(
                      "h-7 rounded-md border px-2 font-mono text-[11px] focus:outline-none focus:ring-1 focus:ring-violet",
                      ROLE_TONE[m.role],
                    )}
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r} className="bg-surface text-text">
                        {r}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    value={m.display_name}
                    onChange={(e) => onChange(i, { display_name: e.target.value })}
                    placeholder={m.column_name}
                    disabled={disabled}
                    className="h-7 w-full rounded-md border border-border bg-bg/60 px-2 text-[12px] text-text placeholder:text-text-faint focus:border-violet focus:outline-none disabled:opacity-50"
                  />
                </td>
                <td className="px-3 py-2">
                  <select
                    value={m.type_tag}
                    onChange={(e) =>
                      onChange(i, { type_tag: e.target.value as SensorTypeTag })
                    }
                    disabled={disabled}
                    className="h-7 rounded-md border border-border bg-bg/60 px-2 font-mono text-[11px] text-text focus:border-violet focus:outline-none disabled:opacity-50"
                  >
                    {TYPE_TAGS.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    value={m.unit}
                    onChange={(e) => onChange(i, { unit: e.target.value })}
                    placeholder="mm/s"
                    disabled={disabled}
                    className="h-7 w-20 rounded-md border border-border bg-bg/60 px-2 font-mono text-[11px] text-text placeholder:text-text-faint focus:border-violet focus:outline-none disabled:opacity-50"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    inputMode="decimal"
                    value={m.warning_threshold ?? ""}
                    onChange={(e) =>
                      onChange(i, {
                        warning_threshold:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                    disabled={disabled}
                    className="h-7 w-20 rounded-md border border-border bg-bg/60 px-2 font-mono text-[11px] text-text focus:border-violet focus:outline-none disabled:opacity-50"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    inputMode="decimal"
                    value={m.critical_threshold ?? ""}
                    onChange={(e) =>
                      onChange(i, {
                        critical_threshold:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                    disabled={disabled}
                    className="h-7 w-20 rounded-md border border-border bg-bg/60 px-2 font-mono text-[11px] text-text focus:border-violet focus:outline-none disabled:opacity-50"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
