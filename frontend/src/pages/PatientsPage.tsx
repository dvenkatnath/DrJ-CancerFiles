import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Search, UserRound } from "lucide-react";
import { patientsApi } from "../api/client";
import type { PatientListItem } from "../types";
import { Badge, Button, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

const statusTone: Record<string, "neutral" | "warning" | "success"> = {
  active: "success",
  pending_review: "warning",
  archived: "neutral",
};

export function PatientsPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { toast } = useToast();
  const [patients, setPatients] = useState<PatientListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  function load(q?: string) {
    setError(null);
    patientsApi
      .list(q)
      .then(setPatients)
      .catch((e) => setError(e.message || "Failed to load patients"));
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const id = setTimeout(() => load(query || undefined), 250);
    return () => clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold">Patients</h1>
          <p className="text-sm text-[var(--color-text-muted)]">Search by name or MRN</p>
        </div>
        {(user?.role === "admin" || user?.role === "curator") && (
          <Button onClick={() => setShowCreate(true)}>
            <Plus size={16} /> Add patient
          </Button>
        )}
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search patients…"
          className="w-full rounded-md border border-[var(--color-border)] bg-white pl-9 pr-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-accent)] outline-none"
        />
      </div>

      {error && <ErrorState message={error} onRetry={() => load(query || undefined)} />}

      {!error && patients === null && (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {!error && patients && patients.length === 0 && (
        <EmptyState
          title="No patients found"
          hint={query ? "Try a different search term." : "Add your first patient to get started."}
        />
      )}

      {!error && patients && patients.length > 0 && (
        <div className="bg-white border border-[var(--color-border)] rounded-lg divide-y divide-[var(--color-border)] overflow-hidden">
          {patients.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/patients/${p.id}/summary`)}
              className="w-full flex items-center gap-4 px-4 py-3.5 text-left hover:bg-gray-50 transition-colors"
            >
              <div className="h-9 w-9 rounded-full bg-[var(--color-accent-bg)] text-[var(--color-accent)] flex items-center justify-center shrink-0">
                <UserRound size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm truncate">{p.name}</span>
                  <Badge tone={statusTone[p.status] || "neutral"}>{p.status.replace("_", " ")}</Badge>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                  MRN {p.mrn} · {p.document_count} document{p.document_count === 1 ? "" : "s"} · updated{" "}
                  {timeAgo(p.updated_at)}
                </p>
              </div>
              {p.pending_review_count > 0 && (
                <Badge tone="warning">{p.pending_review_count} pending review</Badge>
              )}
            </button>
          ))}
        </div>
      )}

      {showCreate && (
        <CreatePatientModal
          onClose={() => setShowCreate(false)}
          onCreated={(p) => {
            setShowCreate(false);
            toast("success", `${p.name} added`);
            load(query || undefined);
            navigate(`/patients/${p.id}/summary`);
          }}
        />
      )}
    </div>
  );
}

function CreatePatientModal({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: (p: { id: string; name: string }) => void;
}) {
  const { toast } = useToast();
  const [mrn, setMrn] = useState("");
  const [name, setName] = useState("");
  const [dob, setDob] = useState("");
  const [sex, setSex] = useState("unknown");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const patient = await patientsApi.create({ mrn, name, date_of_birth: dob || null, sex });
      onCreated(patient);
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Failed to create patient");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl space-y-3">
        <h2 className="text-sm font-semibold">Add patient</h2>
        <div>
          <label className="block text-xs font-medium mb-1">MRN</label>
          <input
            required
            value={mrn}
            onChange={(e) => setMrn(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Full name</label>
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm"
          />
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium mb-1">Date of birth</label>
            <input
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium mb-1">Sex</label>
            <select
              value={sex}
              onChange={(e) => setSex(e.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm"
            >
              <option value="unknown">Unknown</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={submitting}>
            {submitting ? "Adding…" : "Add patient"}
          </Button>
        </div>
      </form>
    </div>
  );
}
