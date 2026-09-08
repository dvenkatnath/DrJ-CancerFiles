// Mirrors backend/app/schemas/*.py. Kept as one file since the two sides of
// this app are still built together; if the API ever grows a separate
// consumer, generate this from the OpenAPI schema (FastAPI exposes one at
// /api/openapi.json) instead of hand-maintaining it.

export type UserRole = "physician" | "curator" | "admin";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  mfa_enabled: boolean;
}

export type PatientSex = "female" | "male" | "other" | "unknown";
export type PatientStatus = "active" | "pending_review" | "archived";

export interface PatientListItem {
  id: string;
  mrn: string;
  name: string;
  status: PatientStatus;
  updated_at: string;
  pending_review_count: number;
  document_count: number;
}

export interface Patient {
  id: string;
  mrn: string;
  name: string;
  date_of_birth: string | null;
  sex: PatientSex;
  status: PatientStatus;
  created_at: string;
  updated_at: string;
}

export type DocumentStatus =
  | "uploaded"
  | "extracting"
  | "summarized"
  | "pending_review"
  | "curated"
  | "error";

export type DateConfidence = "parsed_exact" | "parsed_fuzzy" | "user_confirmed" | "unresolved";

export interface DocumentItem {
  id: string;
  patient_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  doc_type: string | null;
  doc_type_confirmed: boolean;
  doc_date: string | null;
  doc_date_confidence: DateConfidence;
  doc_date_confirmed: boolean;
  status: DocumentStatus;
  error_message: string | null;
  ocr_used: boolean;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  text: string;
  page: number | null;
  section_label: string | null;
}

export type WikiSectionType =
  | "at_a_glance"
  | "problem_list"
  | "medications"
  | "allergies"
  | "lab_highlights"
  | "visit_timeline"
  | "care_plan"
  | "notes";

export interface WikiSource {
  document_id: string;
  document_name?: string | null;
  page?: number | null;
  section_label?: string | null;
}

export interface WikiFact {
  id: string;
  text: string;
  sources?: WikiSource[];
  confidence?: number | null;
  status?: "reviewed" | "unreviewed";
  last_updated?: string | null;
  /** When the clinical event happened (from the source document's detected
   * date), as opposed to last_updated (when this row was extracted/edited). */
  event_date?: string | null;
  /** Structured lab fields -- present only on lab_highlights facts that are
   * one specific numeric result. Powers the Lab Trends panel. */
  test?: string | null;
  value?: number | null;
  unit?: string | null;
}

export interface TrendPoint {
  date: string | null;
  value: number;
  unit?: string | null;
  document_id?: string | null;
  fact_id?: string | null;
}

export interface TrendMarker {
  test: string;
  unit?: string | null;
  points: TrendPoint[];
  direction: "rising" | "falling" | "stable" | "insufficient_data";
  latest_value: number;
  latest_date?: string | null;
}

export interface WikiSection {
  id: string;
  patient_id: string;
  section_type: WikiSectionType;
  content: WikiFact[];
  version: number;
  is_reviewed: boolean;
  updated_at: string;
}

export interface WikiRevision {
  id: string;
  version: number;
  content: WikiFact[];
  change_source: "ai_extraction" | "curator_edit" | "physician_edit" | "system_seed";
  changed_by: string | null;
  note: string | null;
  created_at: string;
}

export type CurationStatus = "pending" | "in_progress" | "published" | "rejected";
export type CurationPriority = "low" | "normal" | "high" | "urgent";
export type SectionDecisionValue = "pending" | "accepted" | "edited" | "rejected";

export interface ProposedSectionChange {
  additions: WikiFact[];
  modifications: unknown[];
  deletions: unknown[];
}

export interface CurationSectionDecisionOut {
  id: string;
  section_type: WikiSectionType;
  decision: SectionDecisionValue;
  final_content: WikiFact[] | null;
  reviewer_note: string | null;
  decided_by: string | null;
  decided_at: string | null;
}

export interface Curation {
  id: string;
  document_id: string;
  patient_id: string;
  status: CurationStatus;
  priority: CurationPriority;
  assigned_to: string | null;
  proposed_changes: Record<string, ProposedSectionChange>;
  created_at: string;
  updated_at: string;
  section_decisions: CurationSectionDecisionOut[];
}

export interface CurationListItem {
  id: string;
  document_id: string;
  patient_id: string;
  patient_name: string;
  document_filename: string;
  status: CurationStatus;
  priority: CurationPriority;
  assigned_to: string | null;
  created_at: string;
  section_count: number;
}

export interface ChatSession {
  id: string;
  patient_id: string;
  user_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  document_id: string;
  chunk_id?: string | null;
  document_name: string;
  page?: number | null;
  section_label?: string | null;
  snippet: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: Citation[];
  pending_curation_flag: boolean;
  created_at: string;
}

export interface HealthStatus {
  status: string;
  environment: string;
  database: { ok: boolean; error: string | null };
  llm: {
    mode: string;
    unavailable: boolean;
    base_url: string;
    chat_model: string;
    extraction_model: string;
    embedding_model: string;
  };
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  patient_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}
