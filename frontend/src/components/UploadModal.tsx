import { useRef, useState } from "react";
import { UploadCloud, X } from "lucide-react";
import { documentsApi } from "../api/client";
import { Button } from "./ui";

interface FileUpload {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

export function UploadModal({
  patientId,
  onClose,
  onUploaded,
}: {
  patientId: string;
  onClose: () => void;
  onUploaded: () => void;
}) {
  const [uploads, setUploads] = useState<FileUpload[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function addFiles(files: FileList | null) {
    if (!files) return;
    const next = Array.from(files).map((file) => ({ file, progress: 0, status: "pending" as const }));
    setUploads((u) => [...u, ...next]);
  }

  async function startUpload() {
    for (let i = 0; i < uploads.length; i++) {
      if (uploads[i].status !== "pending") continue;
      setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, status: "uploading" } : x)));
      try {
        await documentsApi.upload(patientId, uploads[i].file, (pct) =>
          setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, progress: pct } : x))),
        );
        setUploads((u) => u.map((x, idx) => (idx === i ? { ...x, status: "done", progress: 100 } : x)));
      } catch (e) {
        setUploads((u) =>
          u.map((x, idx) =>
            idx === i ? { ...x, status: "error", error: e instanceof Error ? e.message : "Upload failed" } : x,
          ),
        );
      }
    }
    onUploaded();
  }

  const allDone = uploads.length > 0 && uploads.every((u) => u.status === "done" || u.status === "error");
  const anyUploading = uploads.some((u) => u.status === "uploading");

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold">Upload documents</h2>
          <button onClick={onClose} aria-label="Close" className="text-[var(--color-text-muted)] hover:text-[var(--color-text)]">
            <X size={16} />
          </button>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            addFiles(e.dataTransfer.files);
          }}
          onClick={() => inputRef.current?.click()}
          className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
            dragOver ? "border-[var(--color-accent)] bg-[var(--color-accent-bg)]" : "border-[var(--color-border)]"
          }`}
        >
          <UploadCloud className="mx-auto mb-2 text-[var(--color-text-muted)]" size={28} />
          <p className="text-sm">Drag and drop files here, or click to browse</p>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">PDF, DOCX, TXT, or images · up to 50MB each</p>
          <input
            ref={inputRef}
            type="file"
            multiple
            className="hidden"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
            onChange={(e) => addFiles(e.target.files)}
          />
        </div>

        {uploads.length > 0 && (
          <ul className="mt-4 space-y-2 max-h-56 overflow-y-auto">
            {uploads.map((u, i) => (
              <li key={i} className="text-sm">
                <div className="flex items-center justify-between">
                  <span className="truncate max-w-[70%]">{u.file.name}</span>
                  <span className="text-xs text-[var(--color-text-muted)]">
                    {u.status === "error" ? "Failed" : u.status === "done" ? "Done" : `${u.progress}%`}
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100 mt-1 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${u.status === "error" ? "bg-[var(--color-danger)]" : "bg-[var(--color-accent)]"}`}
                    style={{ width: `${u.status === "error" ? 100 : u.progress}%` }}
                  />
                </div>
                {u.error && <p className="text-xs text-[var(--color-danger)] mt-0.5">{u.error}</p>}
              </li>
            ))}
          </ul>
        )}

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {allDone ? "Close" : "Cancel"}
          </Button>
          {!allDone && (
            <Button size="sm" onClick={startUpload} disabled={uploads.length === 0 || anyUploading}>
              {anyUploading ? "Uploading…" : `Upload ${uploads.length || ""}`}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
