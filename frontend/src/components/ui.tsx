import { type ReactNode, useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] py-8 justify-center" role="status">
      <Loader2 className="animate-spin" size={16} />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center" role="alert">
      <AlertTriangle className="text-[var(--color-danger)]" size={28} />
      <p className="text-sm text-[var(--color-text-muted)] max-w-sm">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-gray-50"
        >
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 py-14 text-center">
      <p className="text-sm font-medium text-[var(--color-text)]">{title}</p>
      {hint && <p className="text-sm text-[var(--color-text-muted)] max-w-sm">{hint}</p>}
      {action}
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-md bg-gray-200/70 ${className}`} />;
}

const badgeColors: Record<string, string> = {
  neutral: "bg-gray-100 text-gray-700 border-gray-200",
  accent: "bg-[var(--color-accent-bg)] text-[var(--color-accent)] border-transparent",
  success: "bg-[var(--color-success-bg)] text-[var(--color-success)] border-transparent",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)] border-transparent",
  danger: "bg-[var(--color-danger-bg)] text-[var(--color-danger)] border-transparent",
};

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: keyof typeof badgeColors;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${badgeColors[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  ...rest
}: {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base = "inline-flex items-center justify-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const sizes = size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-2 text-sm";
  const variants: Record<string, string> = {
    primary: "bg-[var(--color-accent)] text-white hover:bg-[var(--color-accent-hover)]",
    secondary: "border border-[var(--color-border)] bg-white hover:bg-gray-50 text-[var(--color-text)]",
    ghost: "hover:bg-gray-100 text-[var(--color-text)]",
    danger: "bg-[var(--color-danger)] text-white hover:opacity-90",
  };
  return (
    <button className={`${base} ${sizes} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  danger,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl">
        <h2 className="text-sm font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-[var(--color-text-muted)]">{message}</p>
        <div className="mt-4 flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} size="sm" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

export function useConfirm() {
  const [state, setState] = useState<{
    open: boolean;
    title: string;
    message: string;
    danger?: boolean;
    resolve?: (v: boolean) => void;
  }>({ open: false, title: "", message: "" });

  const confirm = (title: string, message: string, danger?: boolean) =>
    new Promise<boolean>((resolve) => setState({ open: true, title, message, danger, resolve }));

  const node = (
    <ConfirmDialog
      open={state.open}
      title={state.title}
      message={state.message}
      danger={state.danger}
      onConfirm={() => {
        state.resolve?.(true);
        setState((s) => ({ ...s, open: false }));
      }}
      onCancel={() => {
        state.resolve?.(false);
        setState((s) => ({ ...s, open: false }));
      }}
    />
  );

  return { confirm, confirmDialog: node };
}
