import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="h-screen flex items-center justify-center text-center">
      <div>
        <p className="text-2xl font-semibold">404</p>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">This page doesn't exist.</p>
        <Link to="/patients" className="text-sm text-[var(--color-accent)] mt-3 inline-block">
          Back to Patients
        </Link>
      </div>
    </div>
  );
}
