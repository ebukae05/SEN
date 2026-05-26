import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface Props {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function Modal({ open, onClose, children }: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return createPortal(
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg/70 px-4 py-8 backdrop-blur-md"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="lift relative max-h-full w-full max-w-3xl overflow-hidden rounded-2xl border border-border-strong bg-surface/95 shadow-[0_30px_80px_-20px_rgba(0,0,0,0.8)]"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="absolute top-3 right-3 z-10 flex h-7 w-7 items-center justify-center rounded-md border border-border bg-surface-2 text-text-dim transition-colors hover:border-border-strong hover:text-text"
        >
          <X className="h-3.5 w-3.5" />
        </button>
        <div className="max-h-[85vh] overflow-y-auto">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
