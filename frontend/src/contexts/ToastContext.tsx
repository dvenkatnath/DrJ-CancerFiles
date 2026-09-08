import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

export type ToastKind = "success" | "error" | "info";
interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  toast: (kind: ToastKind, message: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((kind: ToastKind, message: string) => {
    const id = nextId++;
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000);
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2" aria-live="polite" aria-atomic="false">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={
              "rounded-lg border px-4 py-3 text-sm shadow-md min-w-[260px] max-w-sm " +
              (t.kind === "success"
                ? "bg-[var(--color-success-bg)] border-[var(--color-success)] text-[var(--color-success)]"
                : t.kind === "error"
                  ? "bg-[var(--color-danger-bg)] border-[var(--color-danger)] text-[var(--color-danger)]"
                  : "bg-[var(--color-accent-bg)] border-[var(--color-accent)] text-[var(--color-accent)]")
            }
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
