import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, FileText } from "lucide-react";
import { cn } from "../../lib/cn";

interface DropzoneProps {
  onFile: (file: File) => void;
  busy?: boolean;
  selected?: { name: string; size: number } | null;
}

const ACCEPTED = ".csv,.json,.xlsx";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function Dropzone({ onFile, busy, selected }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const pickFile = useCallback(() => inputRef.current?.click(), []);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files?.[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={pickFile}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && pickFile()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={cn(
        "group relative flex w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border border-dashed bg-surface/40 px-6 py-12 transition-colors",
        dragOver
          ? "border-violet bg-violet/5"
          : "border-border hover:border-border-strong hover:bg-surface-hover",
        busy && "pointer-events-none opacity-60",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
          e.currentTarget.value = "";
        }}
      />
      {busy ? (
        <Loader2 className="h-7 w-7 animate-spin text-violet-glow" />
      ) : selected ? (
        <FileText className="h-7 w-7 text-violet-glow" />
      ) : (
        <FileUp className="h-7 w-7 text-text-dim group-hover:text-text" />
      )}
      <div className="text-center">
        {selected ? (
          <>
            <p className="text-[13px] font-medium text-text">{selected.name}</p>
            <p className="font-mono text-[11px] text-text-faint">
              {formatBytes(selected.size)} · click to replace
            </p>
          </>
        ) : (
          <>
            <p className="text-[13px] font-medium text-text">
              Drop a sensor dataset, or click to browse
            </p>
            <p className="font-mono text-[11px] text-text-faint">
              CSV · JSON · XLSX · max 50 MB
            </p>
          </>
        )}
      </div>
    </div>
  );
}
