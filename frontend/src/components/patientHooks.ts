import { useContext } from "react";
import { PatientContext } from "../contexts/PatientContext";

/** Like useActivePatient, but returns undefined instead of throwing when
 * rendered outside a PatientProvider (e.g. TopBar, which renders on every
 * route including ones with no selected patient). */
export function useActivePatientMaybe() {
  return useContext(PatientContext);
}
