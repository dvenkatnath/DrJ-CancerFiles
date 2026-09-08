import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Check, ExternalLink, Pencil, Search, Send, X } from "lucide-react";
import { curationApi, documentsApi } from "../api/client";
import type { Curation, DocumentChunk, DocumentItem, SectionDecisionValue, WikiFact, WikiSectionType } from "../types";
import { Badge, Button, ErrorState, Spinner, useConfirm } from "../components/ui";
import { openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";
import { useToast } from "../contexts/ToastContext";

const SECTION_TITLES: Record<WikiSectionType, string> = {
  at_a_glance: "At a Glance",
  problem_list: "Problem List",
  medications: "Medications",
  allergies: "Allergies",
  lab_highlights: "Lab Highlights",
  visit_timeline: "Visit Timeline",
  care_plan: "Care Plan",
  notes: "Notes",
};

function confidencePct(facts: WikiFact[]): number {
  const withConf = facts.filter((f) => f.confidence != null);
  if (withConf.length === 0) return 0;
  return Math.round((withConf.reduce((s, f) => s + (f.confidence || 0), 0) / withConf.length) * 100);
}

function highlight(text: string, query: string) {
  if (!query.trim()) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-yellow-200 rounded px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

export function CurationDetailPage() {
  const { curationId } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { confirm, confirmDialog } = useConfirm();

  const [curation, setCuration] = useState<Curation | null>(null);
  const [document, setDocument] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeSectionIdx, setActiveSectionIdx] = useState(0);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<string[]>([]);
  const [busySection, setBusySection] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(() => {
    if (!curationId) return;
    curationApi
      .get(curationId)
      .then((c) => {
        setCuration(c);
        setError(null);
        return Promise.all([documentsApi.get(c.document_id), documentsApi.chunks(c.document_id)]);
      })
      .then((res) => {
        if (!res) return;
        const [doc, ch] = res;
        setDocument(doc);
        setChunks(ch);
      })
      .catch((e) => setError(e.message || "Failed to load this curation item"));
  }, [curationId]);

  useEffect(load, [load]);

  const sectionKeys = useMemo(
    () => Object.keys(curation?.proposed_changes || {}) as WikiSectionType[],
    [curation],
  );

  const decisionFor = useCallback(
    (sectionType: string) => curation?.section_decisions.find((d) => d.section_type === sectionType),
    [curation],
  );

  const allDecided = sectionKeys.length > 0 && sectionKeys.every((s) => decisionFor(s) && decisionFor(s)!.decision !== "pending");

  async function decide(sectionType: WikiSectionType, decision: SectionDecisionValue, finalTexts?: string[]) {
    if (!curationId) return;
    setBusySection(sectionType);
    try {
      const proposal = curation!.proposed_changes[sectionType];
      let finalContent: WikiFact[] | null = null;
      if (decision === "edited" && finalTexts) {
        finalContent = proposal.additions.map((f, i) => ({ ...f, text: finalTexts[i] ?? f.text }));
      }
      const updated = await curationApi.decideSection(curationId, sectionType, {
        decision,
        final_content: finalContent,
      });
      setCuration(updated);
      setEditingSection(null);
      toast("success", `${SECTION_TITLES[sectionType]}: ${decision}`);
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to save decision");
    } finally {
      setBusySection(null);
    }
  }

  async function publish() {
    if (!curationId) return;
    const ok = await confirm(
      "Publish to wiki",
      "This commits every accepted/edited section into the patient's living wiki and marks the document Curated. Continue?",
    );
    if (!ok) return;
    setPublishing(true);
    try {
      await curationApi.publish(curationId);
      toast("success", "Published to wiki");
      navigate("/curation-queue");
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to publish");
    } finally {
      setPublishing(false);
    }
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!sectionKeys.length || editingSection) return;
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "j") setActiveSectionIdx((i) => Math.min(i + 1, sectionKeys.length - 1));
      if (e.key === "k") setActiveSectionIdx((i) => Math.max(i - 1, 0));
      const current = sectionKeys[activeSectionIdx];
      if (!current) return;
      if (e.key === "a" || e.key === "A") decide(current, "accepted");
      if (e.key === "r" || e.key === "R") decide(current, "rejected");
      if (e.key === "e" || e.key === "E") {
        setEditingSection(current);
        setEditDraft(curation!.proposed_changes[current].additions.map((f) => f.text));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionKeys, activeSectionIdx, editingSection, curation]);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!curation || !document) return <Spinner label="Loading curation item…" />;

  return (
    <div className="h-full flex">
      {confirmDialog}
      {/* Left: source document viewer */}
      <div className="w-1/2 border-r border-[var(--color-border)] flex flex-col min-w-0">
        <div className="border-b border-[var(--color-border)] p-3 flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)]" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search extracted text…"
              className="w-full rounded-md border border-[var(--color-border)] pl-8 pr-2 py-1.5 text-sm"
            />
          </div>
          <button
            onClick={() => openDocumentInNewTab(document.id)}
            className="text-xs text-[var(--color-accent)] hover:underline inline-flex items-center gap-1 shrink-0"
          >
            Open original <ExternalLink size={12} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          <p className="text-sm font-medium">{document.filename}</p>
          <p className="text-xs text-[var(--color-text-muted)]">
            {document.doc_type} · {document.doc_date || "date unresolved"}
          </p>
          {chunks === null ? (
            <Spinner />
          ) : (
            chunks.map((c) => (
              <div key={c.id} className="text-sm leading-relaxed border-l-2 border-[var(--color-border)] pl-3 py-1">
                {highlight(c.text, search)}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right: proposed wiki updates as diff cards */}
      <div className="w-1/2 flex flex-col min-w-0">
        <div className="border-b border-[var(--color-border)] p-3 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">Proposed wiki updates</p>
            <p className="text-xs text-[var(--color-text-muted)]">
              {sectionKeys.filter((s) => decisionFor(s) && decisionFor(s)!.decision !== "pending").length} of{" "}
              {sectionKeys.length} sections decided · A accept · E edit · R reject · J/K navigate
            </p>
          </div>
          <Button onClick={publish} disabled={!allDecided || publishing}>
            <Send size={14} /> Publish to Wiki
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {sectionKeys.map((sectionType, idx) => {
            const proposal = curation.proposed_changes[sectionType];
            const decision = decisionFor(sectionType);
            const isActive = idx === activeSectionIdx;
            const isEditing = editingSection === sectionType;
            return (
              <div
                key={sectionType}
                onClick={() => setActiveSectionIdx(idx)}
                className={`rounded-lg border p-3 ${isActive ? "border-[var(--color-accent)] ring-1 ring-[var(--color-accent)]" : "border-[var(--color-border)]"}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">{SECTION_TITLES[sectionType]}</h3>
                    <Badge tone={confidencePct(proposal.additions) >= 60 ? "success" : "warning"}>
                      {confidencePct(proposal.additions)}% avg confidence
                    </Badge>
                  </div>
                  {decision && decision.decision !== "pending" && (
                    <Badge tone={decision.decision === "rejected" ? "danger" : "success"}>{decision.decision}</Badge>
                  )}
                </div>

                {!isEditing ? (
                  <ul className="space-y-1.5">
                    {proposal.additions.map((f, i) => (
                      <li
                        key={f.id}
                        className={`text-sm rounded px-2 py-1 ${
                          decision?.decision === "rejected"
                            ? "line-through text-[var(--color-text-muted)] bg-gray-50"
                            : "bg-[var(--color-success-bg)] text-[var(--color-success)]"
                        }`}
                      >
                        {decision?.decision === "edited" && decision.final_content
                          ? decision.final_content[i]?.text
                          : f.text}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="space-y-2">
                    {editDraft.map((text, i) => (
                      <textarea
                        key={i}
                        value={text}
                        onChange={(e) => setEditDraft((d) => d.map((x, j) => (j === i ? e.target.value : x)))}
                        rows={2}
                        className="w-full rounded-md border border-[var(--color-border)] px-2 py-1.5 text-sm"
                      />
                    ))}
                  </div>
                )}

                <div className="flex justify-end gap-1.5 mt-2">
                  {isEditing ? (
                    <>
                      <Button variant="secondary" size="sm" onClick={() => setEditingSection(null)}>
                        <X size={12} /> Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => decide(sectionType, "edited", editDraft)}
                        disabled={busySection === sectionType}
                      >
                        <Check size={12} /> Save edit
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setEditingSection(sectionType);
                          setEditDraft(proposal.additions.map((f) => f.text));
                        }}
                        disabled={busySection === sectionType}
                      >
                        <Pencil size={12} /> Edit
                      </Button>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => decide(sectionType, "rejected")}
                        disabled={busySection === sectionType}
                      >
                        Reject
                      </Button>
                      <Button size="sm" onClick={() => decide(sectionType, "accepted")} disabled={busySection === sectionType}>
                        Accept
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
