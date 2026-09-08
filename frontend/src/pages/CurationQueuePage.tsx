import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { curationApi } from "../api/client";
import type { CurationListItem, CurationPriority, CurationStatus } from "../types";
import { Badge, EmptyState, ErrorState, Skeleton } from "../components/ui";

const PRIORITY_TONE: Record<CurationPriority, "danger" | "warning" | "accent" | "neutral"> = {
  urgent: "danger",
  high: "warning",
  normal: "accent",
  low: "neutral",
};

const STATUS_TONE: Record<CurationStatus, "neutral" | "warning" | "success"> = {
  pending: "neutral",
  in_progress: "warning",
  published: "success",
  rejected: "neutral",
};

function timeAgo(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function CurationQueuePage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<CurationListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<CurationPriority | "">("");
  const [selected, setSelected] = useState(0);

  function load() {
    curationApi
      .queue(priorityFilter ? { priority: priorityFilter } : undefined)
      .then((r) => {
        setItems(r);
        setError(null);
      })
      .catch((e) => setError(e.message || "Failed to load the curation queue"));
  }

  useEffect(load, [priorityFilter]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!items || items.length === 0) return;
      if (e.key === "j") setSelected((s) => Math.min(s + 1, items.length - 1));
      if (e.key === "k") setSelected((s) => Math.max(s - 1, 0));
      if (e.key === "Enter") navigate(`/curation/${items[selected].id}`);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [items, selected, navigate]);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-semibold">Curation Queue</h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Documents awaiting review · use J/K to navigate, Enter to open
          </p>
        </div>
        <select
          value={priorityFilter}
          onChange={(e) => setPriorityFilter(e.target.value as CurationPriority | "")}
          className="rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-sm"
        >
          <option value="">All priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>
      </div>

      {error && <ErrorState message={error} onRetry={load} />}
      {!error && items === null && (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      )}
      {!error && items && items.length === 0 && (
        <EmptyState title="Nothing to review" hint="The curation queue is empty right now." />
      )}
      {!error && items && items.length > 0 && (
        <div className="bg-white border border-[var(--color-border)] rounded-lg divide-y divide-[var(--color-border)] overflow-hidden">
          {items.map((item, i) => (
            <button
              key={item.id}
              onClick={() => navigate(`/curation/${item.id}`)}
              onMouseEnter={() => setSelected(i)}
              className={`w-full flex items-center gap-4 px-4 py-3 text-left ${
                selected === i ? "bg-[var(--color-accent-bg)]" : "hover:bg-gray-50"
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{item.patient_name}</span>
                  <Badge tone={PRIORITY_TONE[item.priority]}>{item.priority}</Badge>
                  <Badge tone={STATUS_TONE[item.status]}>{item.status.replace("_", " ")}</Badge>
                </div>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5 truncate">
                  {item.document_filename} · {item.section_count} section{item.section_count === 1 ? "" : "s"}{" "}
                  proposed · {timeAgo(item.created_at)}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
