import { Link, useParams } from "react-router-dom";
import { ChevronRight, LogOut, WifiOff } from "lucide-react";
import { useAuth } from "../contexts/AuthContext";
import { useActivePatientMaybe } from "./patientHooks";
import { healthApi } from "../api/client";
import { usePolling } from "../hooks/usePolling";
import { Badge } from "./ui";

const roleLabel: Record<string, string> = {
  physician: "Physician",
  curator: "Curator",
  admin: "Admin",
};

export function TopBar() {
  const { user, logout } = useAuth();
  const { patientId } = useParams();
  const patientCtx = useActivePatientMaybe();
  const health = usePolling(() => healthApi.get(), 20000);

  const degraded = health && (health.database.ok === false || health.llm.mode !== "live");

  return (
    <header className="h-14 shrink-0 border-b border-[var(--color-border)] bg-white flex items-center px-5 gap-3">
      <div className="flex items-center gap-1.5 text-sm text-[var(--color-text-muted)] min-w-0">
        <Link to="/patients" className="hover:text-[var(--color-text)]">
          Patients
        </Link>
        {patientId && patientCtx?.patient && (
          <>
            <ChevronRight size={14} />
            <span className="font-medium text-[var(--color-text)] truncate">
              {patientCtx.patient.name}{" "}
              <span className="text-[var(--color-text-muted)] font-normal">({patientCtx.patient.mrn})</span>
            </span>
          </>
        )}
      </div>

      <div className="flex-1" />

      {health && (
        <div title={`Database: ${health.database.ok ? "ok" : "down"} · LLM: ${health.llm.mode}`}>
          {degraded ? (
            <Badge tone="warning">
              <WifiOff size={12} />
              {health.database.ok === false ? "Database issue" : `LLM: ${health.llm.mode.replace("_", " ")}`}
            </Badge>
          ) : (
            <Badge tone="success">All systems live</Badge>
          )}
        </div>
      )}

      <div className="flex items-center gap-2 text-sm">
        <div className="text-right leading-tight">
          <div className="font-medium">{user?.full_name}</div>
          <div className="text-xs text-[var(--color-text-muted)]">{user && roleLabel[user.role]}</div>
        </div>
        <button
          onClick={() => logout()}
          className="ml-1 rounded-md p-2 text-[var(--color-text-muted)] hover:bg-gray-100 hover:text-[var(--color-text)]"
          aria-label="Log out"
          title="Log out"
        >
          <LogOut size={17} />
        </button>
      </div>
    </header>
  );
}
