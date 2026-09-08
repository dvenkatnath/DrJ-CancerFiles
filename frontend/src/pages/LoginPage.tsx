import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { ApiError } from "../api/client";
import { Button } from "../components/ui";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const from = (location.state as { from?: Location })?.from?.pathname || "/patients";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to sign in. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)] px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-6">
          <h1 className="text-lg font-semibold">Clinician Workstation</h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">Sign in to review patient charts</p>
        </div>
        <form onSubmit={onSubmit} className="bg-white border border-[var(--color-border)] rounded-lg p-6 space-y-4">
          {error && (
            <div role="alert" className="rounded-md bg-[var(--color-danger-bg)] text-[var(--color-danger)] text-sm px-3 py-2">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="email" className="block text-sm font-medium mb-1">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-accent)] outline-none"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-[var(--color-border)] px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-accent)] outline-none"
            />
          </div>
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "Signing in…" : "Sign in"}
          </Button>
          <p className="text-xs text-[var(--color-text-muted)] text-center pt-1">
            SSO is not yet enabled for this deployment. Contact your admin for a login.
          </p>
        </form>
      </div>
    </div>
  );
}
