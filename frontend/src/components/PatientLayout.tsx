import { Outlet, useParams } from "react-router-dom";
import { PatientProvider } from "../contexts/PatientContext";

/** Wraps the /patients/:patientId/* routes so the active patient is fetched
 * once and shared (via context) across Summary/Documents/Ask -- switching
 * tabs for the same patient never re-triggers a patient fetch, only the
 * per-tab data. */
export function PatientLayout() {
  const { patientId } = useParams();
  if (!patientId) return null;
  return (
    <PatientProvider patientId={patientId}>
      <Outlet />
    </PatientProvider>
  );
}
