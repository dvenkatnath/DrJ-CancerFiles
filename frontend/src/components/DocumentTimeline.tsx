import type { DocumentItem } from "../types";
import { openDocumentInNewTab } from "../hooks/useDocumentBlobUrl";

const statusDot: Record<string, string> = {
  uploaded: "bg-gray-300",
  extracting: "bg-blue-300",
  summarized: "bg-blue-400",
  pending_review: "bg-[var(--color-warning)]",
  curated: "bg-[var(--color-success)]",
  error: "bg-[var(--color-danger)]",
};

export function DocumentTimeline({ documents }: { documents: DocumentItem[] }) {
  const dated = documents.filter((d) => d.doc_date).sort((a, b) => (a.doc_date! < b.doc_date! ? -1 : 1));
  const undated = documents.filter((d) => !d.doc_date);

  if (dated.length === 0) {
    return <p className="text-sm text-[var(--color-text-muted)]">No dated documents yet.</p>;
  }

  return (
    <div>
      <div className="flex overflow-x-auto gap-0 pb-2">
        {dated.map((d, i) => (
          <button
            key={d.id}
            onClick={() => openDocumentInNewTab(d.id)}
            className="group relative flex flex-col items-center shrink-0 px-3 min-w-[140px] text-left"
            title={d.filename}
          >
            <span className="text-[11px] text-[var(--color-text-muted)] mb-1 whitespace-nowrap">
              {d.doc_date}
            </span>
            <span className={`h-2.5 w-2.5 rounded-full ${statusDot[d.status]} ring-4 ring-white`} />
            {i < dated.length - 1 && (
              <span className="absolute top-[22px] left-1/2 w-full h-px bg-[var(--color-border)]" />
            )}
            <span className="mt-1 text-xs truncate max-w-[130px] group-hover:text-[var(--color-accent)] group-hover:underline">
              {d.doc_type || d.filename}
            </span>
          </button>
        ))}
      </div>
      {undated.length > 0 && (
        <p className="text-xs text-[var(--color-text-muted)] mt-1">
          {undated.length} document{undated.length === 1 ? "" : "s"} with an unconfirmed date not shown here — see
          the Documents tab.
        </p>
      )}
    </div>
  );
}
