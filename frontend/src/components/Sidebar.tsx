import { NavLink, useParams } from "react-router-dom";
import {
  Users,
  BookOpen,
  FileText,
  MessageSquareText,
  ListChecks,
  Settings,
} from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { curationApi } from "../api/client";
import { usePolling } from "../hooks/usePolling";

function NavItem({
  to,
  icon,
  label,
  badge,
  disabled,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  badge?: number;
  disabled?: boolean;
}) {
  if (disabled) {
    return (
      <div
        className="flex items-center gap-2.5 rounded-md px-3 py-2 text-sm text-gray-300 cursor-not-allowed"
        title="Select a patient first"
      >
        {icon}
        <span>{label}</span>
      </div>
    );
  }
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors ${
          isActive
            ? "bg-[var(--color-accent-bg)] text-[var(--color-accent)] font-medium"
            : "text-[var(--color-text)] hover:bg-gray-100"
        }`
      }
    >
      {icon}
      <span className="flex-1">{label}</span>
      {typeof badge === "number" && badge > 0 && (
        <span className="rounded-full bg-[var(--color-warning-bg)] text-[var(--color-warning)] text-[11px] font-semibold px-1.5 py-0.5 min-w-[20px] text-center">
          {badge}
        </span>
      )}
    </NavLink>
  );
}

export function Sidebar() {
  const { user } = useAuth();
  const { patientId } = useParams();

  const queueCount = usePolling(
    () => curationApi.queue().then((items) => items.length),
    30000,
  );

  return (
    <aside className="w-60 shrink-0 border-r border-[var(--color-border)] bg-white flex flex-col">
      <div className="px-4 py-4 border-b border-[var(--color-border)]">
        <p className="text-sm font-semibold">Clinician Workstation</p>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Patient chart review</p>
      </div>
      <nav className="flex-1 p-2 space-y-0.5">
        <NavItem to="/patients" icon={<Users size={17} />} label="Patients" />
        <div className="my-2 border-t border-[var(--color-border)]" />
        <NavItem
          to={patientId ? `/patients/${patientId}/summary` : "#"}
          icon={<BookOpen size={17} />}
          label="Summary"
          disabled={!patientId}
        />
        <NavItem
          to={patientId ? `/patients/${patientId}/documents` : "#"}
          icon={<FileText size={17} />}
          label="Documents"
          disabled={!patientId}
        />
        <NavItem
          to={patientId ? `/patients/${patientId}/chat` : "#"}
          icon={<MessageSquareText size={17} />}
          label="Ask"
          disabled={!patientId}
        />
        <div className="my-2 border-t border-[var(--color-border)]" />
        <NavItem
          to="/curation-queue"
          icon={<ListChecks size={17} />}
          label="Curation Queue"
          badge={queueCount}
        />
        {user?.role === "admin" && (
          <NavItem to="/admin" icon={<Settings size={17} />} label="Admin / Settings" />
        )}
      </nav>
    </aside>
  );
}
