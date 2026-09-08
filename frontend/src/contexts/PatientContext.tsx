import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { patientsApi } from "../api/client";
import type { Patient } from "../types";

interface PatientContextValue {
  patient: Patient | null;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export const PatientContext = createContext<PatientContextValue | undefined>(undefined);

export function PatientProvider({ patientId, children }: { patientId: string; children: ReactNode }) {
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    patientsApi
      .get(patientId)
      .then((p) => !cancelled && setPatient(p))
      .catch((e) => !cancelled && setError(e.message || "Failed to load patient"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [patientId, nonce]);

  return (
    <PatientContext.Provider value={{ patient, loading, error, refresh: () => setNonce((n) => n + 1) }}>
      {children}
    </PatientContext.Provider>
  );
}

export function useActivePatient() {
  const ctx = useContext(PatientContext);
  if (!ctx) throw new Error("useActivePatient must be used within PatientProvider");
  return ctx;
}
