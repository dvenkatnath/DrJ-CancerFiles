import { useCallback, useEffect, useState } from "react";
import { CalendarDays, ShieldAlert } from "lucide-react";
import { useActivePatient } from "../contexts/PatientContext";
import { documentsApi, wikiApi } from "../api/client";
import type { DocumentItem, TrendMarker, WikiSection, WikiSectionType } from "../types";
import { useAuth } from "../contexts/AuthContext";
import { ErrorState, Skeleton } from "../components/ui";
import { WikiSectionCard } from "../components/WikiSectionCard";
import { DocumentTimeline } from "../components/DocumentTimeline";
import { LabTrends } from "../components/LabTrends";

const SECTION_ORDER: { type: WikiSectionType; title: string }[] = [
  { type: "problem_list", title: "Problem List" },
  { type: "medications", title: "Medications" },
  { type: "allergies", title: "Allergies" },
  { type: "lab_highlights", title: "Lab Highlights" },
  { type: "visit_timeline", title: "Visit Timeline" },
  { type: "care_plan", title: "Care Plan" },
  { type: "notes", title: "Notes" },
];

function ageFromDob(dob: string | null): number | null {
  if (!dob) return null;
  const d = new Date(dob);
  const today = new Date();
  let age = today.getFullYear() - d.getFullYear();
  const m = today.getMonth() - d.getMonth();
  if (m < 0 || (m === 0 && today.getDate() < d.getDate())) age--;
  return age;
}

export function PatientSummaryPage() {
  const { patient, loading: patientLoading, error: patientError } = useActivePatient();
  const { user } = useAuth();
  const [sections, setSections] = useState<WikiSection[] | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[] | null>(null);
  const [trends, setTrends] = useState<TrendMarker[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!patient) return;
    setError(null);
    Promise.all([wikiApi.list(patient.id), documentsApi.list(patient.id), wikiApi.trends(patient.id)])
      .then(([w, d, t]) => {
        setSections(w);
        setDocuments(d);
        setTrends(t);
      })
      .catch((e) => setError(e.message || "Failed to load summary"));
  }, [patient]);

  useEffect(() => {
    load();
  }, [load]);

  if (patientLoading) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-3">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (patientError || !patient) {
    return <ErrorState message={patientError || "Patient not found"} />;
  }

  const sectionByType = new Map(sections?.map((s) => [s.section_type, s]));
  const allergyFacts = sectionByType.get("allergies")?.content || [];
  const problemFacts = sectionByType.get("problem_list")?.content || [];
  const medFacts = sectionByType.get("medications")?.content || [];
  const age = ageFromDob(patient.date_of_birth);
  const canEdit = user?.role === "physician" || user?.role === "curator" || user?.role === "admin";

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      {/* At-a-glance header -- visible without scrolling */}
      <div className="bg-white border border-[var(--color-border)] rounded-lg p-5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <h1 className="text-lg font-semibold">{patient.name}</h1>
          <span className="text-sm text-[var(--color-text-muted)]">
            {age !== null ? `${age}y` : "age unknown"} · {patient.sex} · MRN {patient.mrn}
          </span>
        </div>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm">
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-1 flex items-center gap-1">
              <ShieldAlert size={12} /> Allergies
            </p>
            {allergyFacts.length === 0 ? (
              <p className="text-[var(--color-text-muted)]">None documented</p>
            ) : (
              <ul className="space-y-0.5">
                {allergyFacts.map((f) => (
                  <li key={f.id}>{f.text}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-1">Active problems</p>
            {problemFacts.length === 0 ? (
              <p className="text-[var(--color-text-muted)]">None documented</p>
            ) : (
              <ul className="space-y-0.5">
                {problemFacts.slice(0, 4).map((f) => (
                  <li key={f.id} className="truncate">
                    {f.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-1">Current medications</p>
            {medFacts.length === 0 ? (
              <p className="text-[var(--color-text-muted)]">None documented</p>
            ) : (
              <ul className="space-y-0.5">
                {medFacts.slice(0, 4).map((f) => (
                  <li key={f.id} className="truncate">
                    {f.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      {documents && documents.length > 0 && (
        <div className="bg-white border border-[var(--color-border)] rounded-lg p-4">
          <p className="text-xs uppercase tracking-wide text-[var(--color-text-muted)] mb-2 flex items-center gap-1">
            <CalendarDays size={12} /> Document timeline
          </p>
          <DocumentTimeline documents={documents} />
        </div>
      )}

      <LabTrends markers={trends} />

      {error && <ErrorState message={error} onRetry={load} />}

      {!error && sections === null && (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      )}

      {!error &&
        sections !== null &&
        SECTION_ORDER.map(({ type, title }) => (
          <WikiSectionCard
            key={type}
            patientId={patient.id}
            sectionType={type}
            title={title}
            section={sectionByType.get(type)}
            canEdit={canEdit}
            onChanged={load}
          />
        ))}
    </div>
  );
}
