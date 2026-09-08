import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Spinner } from "../components/ui";
import type { UserRole } from "../types";

export function ProtectedRoute({ roles }: { roles?: UserRole[] }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <Spinner label="Checking your session…" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex h-full items-center justify-center p-10 text-center">
        <div>
          <p className="text-sm font-medium">You don't have access to this page</p>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            This area requires a different role than {user.role}.
          </p>
        </div>
      </div>
    );
  }
  return <Outlet />;
}
