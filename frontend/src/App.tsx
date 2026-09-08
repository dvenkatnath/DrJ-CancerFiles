import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { ProtectedRoute } from "./routes/ProtectedRoute";
import { AppShell } from "./components/AppShell";
import { PatientLayout } from "./components/PatientLayout";
import { LoginPage } from "./pages/LoginPage";
import { PatientsPage } from "./pages/PatientsPage";
import { PatientSummaryPage } from "./pages/PatientSummaryPage";
import { PatientDocumentsPage } from "./pages/PatientDocumentsPage";
import { PatientChatPage } from "./pages/PatientChatPage";
import { CurationQueuePage } from "./pages/CurationQueuePage";
import { CurationDetailPage } from "./pages/CurationDetailPage";
import { AdminPage } from "./pages/AdminPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/" element={<Navigate to="/patients" replace />} />
              <Route path="/patients" element={<PatientsPage />} />

              <Route path="/patients/:patientId" element={<PatientLayout />}>
                <Route index element={<Navigate to="summary" replace />} />
                <Route path="summary" element={<PatientSummaryPage />} />
                <Route path="documents" element={<PatientDocumentsPage />} />
                <Route path="chat" element={<PatientChatPage />} />
              </Route>

              <Route path="/curation-queue" element={<CurationQueuePage />} />
              <Route path="/curation/:curationId" element={<CurationDetailPage />} />

              <Route element={<ProtectedRoute roles={["admin"]} />}>
                <Route path="/admin" element={<AdminPage />} />
              </Route>
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </ToastProvider>
    </AuthProvider>
  );
}
