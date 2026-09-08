import { useEffect, useState } from "react";
import { ExternalLink, Upload } from "lucide-react";
import { useActivePatient } from "../contexts/PatientContext";
import { documentsApi } from "../api/client";
import type { DocumentItem } from "../types";
import { Button, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { DocumentStatusBadge } from "../components/StatusBadge";
import { UploadModal } from "../components/UploadModal";
import { useDocumentBlobUrl, openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";
import { useToast } from "../contexts/ToastContext";

const ACTIVE_STATUSES = new Set(["uploaded", "extracting", "summarized"]);

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function PatientDocumentsPage() {
  const { patient } = useActivePatient();
  const { toast } = useToast();
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  function load() {
    if (!patient) return;
    documentsApi
      .list(patient.id)
      .then((docs) => {
        setDocuments(docs);
        setError(null);
      })
      .catch((e) => setError(e.message || "Failed to load documents"));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patient?.id]);

  // Poll while any document is still moving through the pipeline, so status
  // badges update live without a manual refresh.
  useEffect(() => {
    if (!documents?.some((d) => ACTIVE_STATUSES.has(d.status))) return;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [documents]);

  if (!patient) return null;
  const selected = documents?.find((d) => d.id === selectedId) || null;

  return (
    <div className="h-full flex">
      <div className="flex-1 min-w-0 p-6 overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-lg font-semibold">Documents</h1>
          <Button onClick={() => setShowUpload(true)}>
            <Upload size={15} /> Upload
          </Button>
        </div>

        {error && <ErrorState message={error} onRetry={load} />}
        {!error && documents === null && (
          <div className="space-y-2">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )}
        {!error && documents && documents.length === 0 && (
          <EmptyState
            title="No documents yet"
            hint="Upload labs, visit notes, discharge summaries, or imaging reports to get started."
            action={
              <Button onClick={() => setShowUpload(true)} className="mt-2">
                <Upload size={15} /> Upload documents
              </Button>
            }
          />
        )}
        {!error && documents && documents.length > 0 && (
          <div className="bg-white border border-[var(--color-border)] rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
                <tr>
                  <th className="text-left px-4 py-2 font-medium">Filename</th>
                  <th className="text-left px-4 py-2 font-medium">Type</th>
                  <th className="text-left px-4 py-2 font-medium">Date</th>
                  <th className="text-left px-4 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-border)]">
                {documents.map((d) => (
                  <tr
                    key={d.id}
                    onClick={() => setSelectedId(d.id)}
                    className={`cursor-pointer hover:bg-gray-50 ${selectedId === d.id ? "bg-[var(--color-accent-bg)]" : ""}`}
                  >
                    <td className="px-4 py-2.5 max-w-[260px] truncate">{d.filename}</td>
                    <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{d.doc_type || "—"}</td>
                    <td className="px-4 py-2.5 text-[var(--color-text-muted)]">
                      {d.doc_date || (d.doc_date_confidence === "unresolved" ? "needs review" : "—")}
                    </td>
                    <td className="px-4 py-2.5">
                      <DocumentStatusBadge status={d.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selected && (
        <DocumentPreviewPane
          key={selected.id}
          document={selected}
          onSaved={() => {
            load();
            toast("success", "Document details updated");
          }}
        />
      )}

      {showUpload && patient && (
        <UploadModal
          patientId={patient.id}
          onClose={() => setShowUpload(false)}
          onUploaded={() => {
            load();
          }}
        />
      )}
    </div>
  );
}

function DocumentPreviewPane({ document: doc, onSaved }: { document: DocumentItem; onSaved: () => void }) {
  const { url, mimeType, loading, error } = useDocumentBlobUrl(doc.id);
  const [docType, setDocType] = useState(doc.doc_type || "");
  const [docDate, setDocDate] = useState(doc.doc_date || "");
  const [saving, setSaving] = useState(false);
  const { toast } = useToast();

  async function saveConfirmation() {
    setSaving(true);
    try {
      await documentsApi.confirm(doc.id, { doc_type: docType || null, doc_date: docDate || null });
      onSaved();
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <aside className="w-[420px] shrink-0 border-l border-[var(--color-border)] bg-white overflow-y-auto p-5">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-semibold truncate">{doc.filename}</h2>
        <button
          onClick={() => openDocumentInNewTab(doc.id)}
          className="shrink-0 text-[var(--color-accent)] hover:underline text-xs inline-flex items-center gap-1"
        >
          Open <ExternalLink size={12} />
        </button>
      </div>

      <p className="text-xs text-[var(--color-text-muted)] mb-4">
        {formatBytes(doc.size_bytes)} · {doc.mime_type} · uploaded {new Date(doc.created_at).toLocaleString()}
        {doc.ocr_used && " · OCR used"}
      </p>

      {doc.status === "error" && doc.error_message && (
        <div className="mb-4 rounded-md bg-[var(--color-danger-bg)] text-[var(--color-danger)] text-xs px-3 py-2">
          {doc.error_message}
        </div>
      )}

      <div className="mb-4 rounded-md border border-[var(--color-border)] bg-gray-50 h-48 flex items-center justify-center overflow-hidden">
        {loading && <span className="text-xs text-[var(--color-text-muted)]">Loading preview…</span>}
        {error && <span className="text-xs text-[var(--color-danger)]">{error}</span>}
        {url && mimeType?.startsWith("image/") && <img src={url} alt={doc.filename} className="max-h-full max-w-full object-contain" />}
        {url && mimeType === "application/pdf" && <iframe title={doc.filename} src={url} className="w-full h-full" />}
        {url && mimeType?.startsWith("text/") && (
          <iframe title={doc.filename} src={url} className="w-full h-full bg-white" />
        )}
        {url && !mimeType?.startsWith("image/") && mimeType !== "application/pdf" && !mimeType?.startsWith("text/") && (
          <span className="text-xs text-[var(--color-text-muted)]">No inline preview for this file type.</span>
        )}
      </div>

      <div className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--color-text-muted)]">
          Confirm detected metadata
        </p>
        <div>
          <label className="block text-xs font-medium mb-1">Document type</label>
          <input
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-sm"
          />
          {!doc.doc_type_confirmed && (
            <p className="text-[11px] text-[var(--color-warning)] mt-1">Auto-detected, not yet confirmed</p>
          )}
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Document date</label>
          <input
            type="date"
            value={docDate}
            onChange={(e) => setDocDate(e.target.value)}
            className="w-full rounded-md border border-[var(--color-border)] px-2.5 py-1.5 text-sm"
          />
          {!doc.doc_date_confirmed && (
            <p className="text-[11px] text-[var(--color-warning)] mt-1">
              {doc.doc_date ? "Auto-detected, not yet confirmed" : "Could not be determined automatically"}
            </p>
          )}
        </div>
        <Button size="sm" onClick={saveConfirmation} disabled={saving} className="w-full">
          {saving ? "Saving…" : "Confirm"}
        </Button>
      </div>
    </aside>
  );
}
