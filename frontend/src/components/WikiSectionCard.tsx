import { useEffect, useState } from "react";
import { ChevronDown, ChevronRight, Clock, Pencil, Plus, Trash2, X } from "lucide-react";
import type { WikiFact, WikiRevision, WikiSection, WikiSectionType } from "../types";
import { wikiApi } from "../api/client";
import { useToast } from "../contexts/ToastContext";
import { openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";
import { Badge, Button, Spinner } from "./ui";

function confidenceBadge(confidence?: number | null) {
  if (confidence == null) return null;
  const pct = Math.round(confidence * 100);
  const tone = confidence >= 0.7 ? "success" : confidence >= 0.4 ? "warning" : "danger";
  return (
    <Badge tone={tone} className="ml-1.5">
      {pct}% confidence
    </Badge>
  );
}

function timeAgo(iso?: string | null) {
  if (!iso) return "";
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function FactRow({ fact }: { fact: WikiFact }) {
  const unreviewed = fact.status === "unreviewed";
  return (
    <li
      className={`py-2 px-3 -mx-3 rounded-md ${unreviewed ? "bg-[var(--color-warning-bg)]/60 border-l-2 border-[var(--color-warning)]" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm leading-snug">{fact.text}</p>
        <div className="shrink-0 flex items-center">{confidenceBadge(fact.confidence)}</div>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
        {unreviewed && <Badge tone="warning">Unreviewed AI draft</Badge>}
        {fact.last_updated && (
          <span className="inline-flex items-center gap-1">
            <Clock size={11} /> {timeAgo(fact.last_updated)}
          </span>
        )}
        {(fact.sources || []).map((s, i) => (
          <button
            key={i}
            onClick={() => openDocumentInNewTab(s.document_id)}
            className="underline decoration-dotted hover:text-[var(--color-accent)]"
            title="Open source document"
          >
            {s.document_name || "source"}
            {s.page ? ` p.${s.page}` : ""}
          </button>
        ))}
      </div>
    </li>
  );
}

export function WikiSectionCard({
  patientId,
  sectionType,
  title,
  section,
  canEdit,
  onChanged,
}: {
  patientId: string;
  sectionType: WikiSectionType;
  title: string;
  section: WikiSection | undefined;
  canEdit: boolean;
  onChanged: () => void;
}) {
  const { toast } = useToast();
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<WikiFact[]>([]);
  const [saving, setSaving] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  const facts = section?.content || [];
  const hasUnreviewed = facts.some((f) => f.status === "unreviewed");

  function startEdit() {
    setDraft(facts.map((f) => ({ ...f })));
    setEditing(true);
  }

  async function save() {
    setSaving(true);
    try {
      await wikiApi.edit(
        patientId,
        sectionType,
        draft.filter((f) => f.text.trim().length > 0),
      );
      toast("success", `${title} updated`);
      setEditing(false);
      onChanged();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="bg-white border border-[var(--color-border)] rounded-lg">
      <div className="flex items-center gap-2 px-4 py-3">
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex items-center gap-2 flex-1 text-left"
          aria-expanded={expanded}
        >
          {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <h2 className="text-sm font-semibold">{title}</h2>
          {hasUnreviewed && <Badge tone="warning">Needs review</Badge>}
          <span className="text-xs text-[var(--color-text-muted)]">{facts.length}</span>
        </button>
        {section && (
          <button
            onClick={() => setShowHistory(true)}
            className="text-xs text-[var(--color-text-muted)] hover:text-[var(--color-accent)]"
          >
            v{section.version} history
          </button>
        )}
        {canEdit && !editing && (
          <Button variant="ghost" size="sm" onClick={startEdit}>
            <Pencil size={13} /> Edit
          </Button>
        )}
      </div>

      {expanded && !editing && (
        <div className="px-4 pb-4">
          {facts.length === 0 ? (
            <p className="text-sm text-[var(--color-text-muted)] py-2">Nothing recorded yet.</p>
          ) : (
            <ul className="divide-y divide-[var(--color-border)]/70">
              {facts.map((f) => (
                <FactRow key={f.id} fact={f} />
              ))}
            </ul>
          )}
        </div>
      )}

      {expanded && editing && (
        <div className="px-4 pb-4 space-y-2">
          {draft.map((f, idx) => (
            <div key={f.id} className="flex items-start gap-2">
              <textarea
                value={f.text}
                onChange={(e) =>
                  setDraft((d) => d.map((x, i) => (i === idx ? { ...x, text: e.target.value } : x)))
                }
                rows={2}
                className="flex-1 rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-sm resize-y"
              />
              <button
                onClick={() => setDraft((d) => d.filter((_, i) => i !== idx))}
                className="mt-1.5 text-[var(--color-text-muted)] hover:text-[var(--color-danger)]"
                aria-label="Remove statement"
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          <button
            onClick={() =>
              setDraft((d) => [
                ...d,
                { id: crypto.randomUUID(), text: "", status: "reviewed", last_updated: new Date().toISOString() },
              ])
            }
            className="text-sm text-[var(--color-accent)] inline-flex items-center gap-1"
          >
            <Plus size={14} /> Add statement
          </button>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" size="sm" onClick={() => setEditing(false)} disabled={saving}>
              <X size={13} /> Cancel
            </Button>
            <Button size="sm" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        </div>
      )}

      {showHistory && (
        <HistoryModal
          patientId={patientId}
          sectionType={sectionType}
          title={title}
          onClose={() => setShowHistory(false)}
        />
      )}
    </section>
  );
}

function HistoryModal({
  patientId,
  sectionType,
  title,
  onClose,
}: {
  patientId: string;
  sectionType: WikiSectionType;
  title: string;
  onClose: () => void;
}) {
  const [revisions, setRevisions] = useState<WikiRevision[] | null>(null);

  useEffect(() => {
    wikiApi.revisions(patientId, sectionType).then(setRevisions);
  }, [patientId, sectionType]);

  const sourceLabel: Record<string, string> = {
    ai_extraction: "AI extraction",
    curator_edit: "Curator edit",
    physician_edit: "Physician edit",
    system_seed: "Seed data",
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg max-h-[80vh] overflow-y-auto rounded-lg bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">{title} — revision history</h2>
          <button onClick={onClose} aria-label="Close" className="text-[var(--color-text-muted)] hover:text-[var(--color-text)]">
            <X size={16} />
          </button>
        </div>
        {revisions === null ? (
          <Spinner />
        ) : revisions.length === 0 ? (
          <p className="text-sm text-[var(--color-text-muted)]">No history yet.</p>
        ) : (
          <ul className="space-y-3">
            {revisions.map((r) => (
              <li key={r.id} className="border-l-2 border-[var(--color-border)] pl-3">
                <div className="text-sm font-medium">
                  v{r.version} · {sourceLabel[r.change_source] || r.change_source}
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">
                  {new Date(r.created_at).toLocaleString()}
                  {r.note ? ` — "${r.note}"` : ""}
                </div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">{r.content.length} statement(s)</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
