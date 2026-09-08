// Thin, typed fetch wrapper. Deliberately not axios: one small file covers
// everything this app needs (JSON, auth header injection, 401 -> refresh ->
// retry once, SSE streaming for chat) without an extra dependency.
import type {
  AuditLogEntry,
  ChatMessage,
  ChatSession,
  Citation,
  Curation,
  CurationListItem,
  CurationPriority,
  CurationStatus,
  DocumentChunk,
  DocumentItem,
  HealthStatus,
  Patient,
  PatientListItem,
  SectionDecisionValue,
  TrendMarker,
  User,
  WikiFact,
  WikiRevision,
  WikiSection,
  WikiSectionType,
} from "../types";

const TOKEN_KEY = "cw_access_token";
const REFRESH_KEY = "cw_refresh_token";

export function getAccessToken() {
  return localStorage.getItem(TOKEN_KEY);
}
function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}
export function setTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}
export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let refreshPromise: Promise<boolean> | null = null;

async function doRefresh(): Promise<boolean> {
  const refresh_token = getRefreshToken();
  if (!refresh_token) return false;
  const resp = await fetch("/api/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token }),
  });
  if (!resp.ok) return false;
  const data = await resp.json();
  setTokens(data.access_token, data.refresh_token);
  return true;
}

interface RequestOpts {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
  signal?: AbortSignal;
}

async function request<T>(path: string, opts: RequestOpts = {}): Promise<T> {
  const doFetch = async (): Promise<Response> => {
    const headers: Record<string, string> = {};
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    let body: BodyInit | undefined;
    if (opts.body !== undefined) {
      if (opts.isFormData) {
        body = opts.body as FormData;
      } else {
        headers["Content-Type"] = "application/json";
        body = JSON.stringify(opts.body);
      }
    }
    return fetch(`/api${path}`, { method: opts.method || "GET", headers, body, signal: opts.signal });
  };

  let resp = await doFetch();
  if (resp.status === 401 && getRefreshToken()) {
    refreshPromise = refreshPromise || doRefresh();
    const ok = await refreshPromise;
    refreshPromise = null;
    if (ok) resp = await doFetch();
  }
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const data = await resp.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
    } catch {
      /* ignore parse failure */
    }
    throw new ApiError(resp.status, detail || `Request failed (${resp.status})`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

// ------------------------------------------------------------------- auth
export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; refresh_token: string }>("/auth/login", {
      method: "POST",
      body: { email, password },
    }),
  me: () => request<User>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
};

// ---------------------------------------------------------------- patients
export const patientsApi = {
  list: (q?: string) => request<PatientListItem[]>(`/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  get: (id: string) => request<Patient>(`/patients/${id}`),
  create: (body: { mrn: string; name: string; date_of_birth?: string | null; sex?: string }) =>
    request<Patient>("/patients", { method: "POST", body }),
  update: (id: string, body: Partial<Patient>) => request<Patient>(`/patients/${id}`, { method: "PATCH", body }),
};

// --------------------------------------------------------------- documents
export const documentsApi = {
  list: (patientId: string) => request<DocumentItem[]>(`/patients/${patientId}/documents`),
  get: (id: string) => request<DocumentItem>(`/documents/${id}`),
  chunks: (id: string) => request<DocumentChunk[]>(`/documents/${id}/chunks`),
  /** The /file endpoint requires a Bearer header, which a plain <a href> or
   * <iframe src> can't send -- fetch it as a blob and hand back an object URL
   * instead, for both the preview pane and "open original" links. Caller is
   * responsible for revoking the URL (see useDocumentBlobUrl) when done. */
  fetchFileBlobUrl: async (id: string): Promise<{ url: string; mimeType: string }> => {
    const token = getAccessToken();
    const resp = await fetch(`/api/documents/${id}/file`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!resp.ok) throw new ApiError(resp.status, "Failed to load the original file");
    const blob = await resp.blob();
    return { url: URL.createObjectURL(blob), mimeType: blob.type };
  },
  upload: async (patientId: string, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData();
    form.append("file", file);
    // XHR instead of fetch so we get real upload progress events.
    return new Promise<DocumentItem>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `/api/patients/${patientId}/documents`);
      const token = getAccessToken();
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) resolve(JSON.parse(xhr.responseText));
        else reject(new ApiError(xhr.status, xhr.responseText || "Upload failed"));
      };
      xhr.onerror = () => reject(new ApiError(0, "Network error during upload"));
      xhr.send(form);
    });
  },
  confirm: (id: string, body: { doc_type?: string | null; doc_date?: string | null }) =>
    request<DocumentItem>(`/documents/${id}/confirm`, { method: "PATCH", body }),
};

// -------------------------------------------------------------------- wiki
export const wikiApi = {
  list: (patientId: string) => request<WikiSection[]>(`/patients/${patientId}/wiki`),
  get: (patientId: string, sectionType: WikiSectionType) =>
    request<WikiSection>(`/patients/${patientId}/wiki/${sectionType}`),
  edit: (patientId: string, sectionType: WikiSectionType, content: WikiFact[], note?: string) =>
    request<WikiSection>(`/patients/${patientId}/wiki/${sectionType}`, {
      method: "PUT",
      body: { content, note },
    }),
  revisions: (patientId: string, sectionType: WikiSectionType) =>
    request<WikiRevision[]>(`/patients/${patientId}/wiki/${sectionType}/revisions`),
  trends: (patientId: string) => request<TrendMarker[]>(`/patients/${patientId}/wiki/trends`),
};

// --------------------------------------------------------------- curation
export const curationApi = {
  queue: (params?: { status?: CurationStatus; priority?: CurationPriority; assigned_to?: string }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.priority) qs.set("priority", params.priority);
    if (params?.assigned_to) qs.set("assigned_to", params.assigned_to);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<CurationListItem[]>(`/curation-queue${suffix}`);
  },
  get: (id: string) => request<Curation>(`/curation/${id}`),
  assign: (id: string, body: { assigned_to?: string | null; priority?: CurationPriority }) =>
    request<Curation>(`/curation/${id}/assign`, { method: "PATCH", body }),
  decideSection: (
    id: string,
    sectionType: WikiSectionType,
    body: { decision: SectionDecisionValue; final_content?: WikiFact[] | null; reviewer_note?: string | null },
  ) =>
    request<Curation>(`/curation/${id}/decisions/${sectionType}`, {
      method: "PUT",
      body: { section_type: sectionType, ...body },
    }),
  publish: (id: string) => request<Curation>(`/curation/${id}/publish`, { method: "POST" }),
};

// -------------------------------------------------------------------- chat
export const chatApi = {
  starters: (patientId: string) => request<{ starters: string[] }>(`/patients/${patientId}/chat/starters`),
  listSessions: (patientId: string) => request<ChatSession[]>(`/patients/${patientId}/chat/sessions`),
  createSession: (patientId: string) =>
    request<ChatSession>(`/patients/${patientId}/chat/sessions`, { method: "POST" }),
  messages: (sessionId: string) => request<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`),
  ask: async (
    sessionId: string,
    question: string,
    handlers: {
      onDelta: (chunk: string) => void;
      onDone: (result: { citations: Citation[]; pending_curation_flag: boolean; message_id: string }) => void;
      onError: (err: Error) => void;
    },
  ) => {
    try {
      const token = getAccessToken();
      const resp = await fetch(`/api/chat/sessions/${sessionId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ question }),
      });
      if (!resp.ok || !resp.body) throw new ApiError(resp.status, "Failed to reach chat endpoint");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const payload = JSON.parse(line.slice(5).trim());
          if (payload.delta) handlers.onDelta(payload.delta);
          if (payload.done) handlers.onDone(payload);
        }
      }
    } catch (e) {
      handlers.onError(e instanceof Error ? e : new Error(String(e)));
    }
  },
};

// ------------------------------------------------------------------- admin
export const adminApi = {
  listUsers: () => request<User[]>("/admin/users"),
  createUser: (body: { email: string; full_name: string; password: string; role: string }) =>
    request<User>("/admin/users", { method: "POST", body }),
  updateUser: (id: string, body: Partial<Pick<User, "full_name" | "role" | "is_active">>) =>
    request<User>(`/admin/users/${id}`, { method: "PATCH", body }),
  auditLog: (params?: { patient_id?: string; user_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.patient_id) qs.set("patient_id", params.patient_id);
    if (params?.user_id) qs.set("user_id", params.user_id);
    const suffix = qs.toString() ? `?${qs}` : "";
    return request<AuditLogEntry[]>(`/admin/audit-log${suffix}`);
  },
  ingestionSettings: () => request<Record<string, unknown>>("/admin/ingestion-settings"),
};

export const healthApi = {
  get: () => request<HealthStatus>("/health"),
};
