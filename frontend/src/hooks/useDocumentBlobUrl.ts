import { useEffect, useState } from "react";
import { documentsApi } from "../api/client";

/** Fetches a document's original file as a blob URL for inline preview
 * (iframe/img src), revoking it on unmount or when the id changes. */
export function useDocumentBlobUrl(documentId: string | null) {
  const [state, setState] = useState<{ url: string; mimeType: string } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) {
      setState(null);
      return;
    }
    let cancelled = false;
    let currentUrl: string | null = null;
    setLoading(true);
    setError(null);
    documentsApi
      .fetchFileBlobUrl(documentId)
      .then((res) => {
        if (cancelled) {
          URL.revokeObjectURL(res.url);
          return;
        }
        currentUrl = res.url;
        setState(res);
      })
      .catch((e) => !cancelled && setError(e.message || "Failed to load file"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [documentId]);

  return { ...state, loading, error };
}

export async function openDocumentInNewTab(documentId: string) {
  const { url } = await documentsApi.fetchFileBlobUrl(documentId);
  window.open(url, "_blank", "noopener,noreferrer");
}
