import { useEffect, useState } from "react";
import { adminApi } from "../api/client";
import type { AuditLogEntry, User, UserRole } from "../types";
import { Badge, Button, ErrorState, Spinner } from "../components/ui";
import { useToast } from "../contexts/ToastContext";

type Tab = "users" | "audit" | "settings";

export function AdminPage() {
  const [tab, setTab] = useState<Tab>("users");

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-lg font-semibold mb-1">Admin / Settings</h1>
      <p className="text-sm text-[var(--color-text-muted)] mb-4">Users, audit log, and ingestion configuration</p>
      <div className="flex gap-1 border-b border-[var(--color-border)] mb-4">
        {(["users", "audit", "settings"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 text-sm border-b-2 -mb-px ${
              tab === t ? "border-[var(--color-accent)] text-[var(--color-accent)] font-medium" : "border-transparent text-[var(--color-text-muted)]"
            }`}
          >
            {t === "users" ? "Users" : t === "audit" ? "Audit Log" : "Ingestion Settings"}
          </button>
        ))}
      </div>
      {tab === "users" && <UsersTab />}
      {tab === "audit" && <AuditTab />}
      {tab === "settings" && <SettingsTab />}
    </div>
  );
}

function UsersTab() {
  const { toast } = useToast();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  function load() {
    adminApi
      .listUsers()
      .then(setUsers)
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  async function toggleActive(u: User) {
    try {
      const updated = await adminApi.updateUser(u.id, { is_active: !u.is_active });
      setUsers((list) => list!.map((x) => (x.id === u.id ? updated : x)));
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to update user");
    }
  }

  async function changeRole(u: User, role: UserRole) {
    try {
      const updated = await adminApi.updateUser(u.id, { role });
      setUsers((list) => list!.map((x) => (x.id === u.id ? updated : x)));
    } catch (e) {
      toast("error", e instanceof Error ? e.message : "Failed to update role");
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!users) return <Spinner />;

  return (
    <div>
      <div className="flex justify-end mb-3">
        <Button size="sm" onClick={() => setShowCreate(true)}>
          Add user
        </Button>
      </div>
      <div className="bg-white border border-[var(--color-border)] rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
            <tr>
              <th className="text-left px-4 py-2 font-medium">Name</th>
              <th className="text-left px-4 py-2 font-medium">Email</th>
              <th className="text-left px-4 py-2 font-medium">Role</th>
              <th className="text-left px-4 py-2 font-medium">Status</th>
              <th />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {users.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-2.5">{u.full_name}</td>
                <td className="px-4 py-2.5 text-[var(--color-text-muted)]">{u.email}</td>
                <td className="px-4 py-2.5">
                  <select
                    value={u.role}
                    onChange={(e) => changeRole(u, e.target.value as UserRole)}
                    className="rounded-md border border-[var(--color-border)] px-2 py-1 text-xs"
                  >
                    <option value="physician">Physician</option>
                    <option value="curator">Curator</option>
                    <option value="admin">Admin</option>
                  </select>
                </td>
                <td className="px-4 py-2.5">
                  <Badge tone={u.is_active ? "success" : "neutral"}>{u.is_active ? "Active" : "Disabled"}</Badge>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <Button variant="ghost" size="sm" onClick={() => toggleActive(u)}>
                    {u.is_active ? "Disable" : "Enable"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={(u) => {
            setUsers((list) => [...(list || []), u]);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}

function CreateUserModal({ onClose, onCreated }: { onClose: () => void; onCreated: (u: User) => void }) {
  const { toast } = useToast();
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("physician");
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const user = await adminApi.createUser({ email, full_name: fullName, password, role });
      onCreated(user);
    } catch (err) {
      toast("error", err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-lg bg-white p-5 shadow-xl space-y-3">
        <h2 className="text-sm font-semibold">Add user</h2>
        <div>
          <label className="block text-xs font-medium mb-1">Full name</label>
          <input required value={fullName} onChange={(e) => setFullName(e.target.value)} className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Email</label>
          <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Temporary password</label>
          <input required type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Role</label>
          <select value={role} onChange={(e) => setRole(e.target.value as UserRole)} className="w-full rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm">
            <option value="physician">Physician</option>
            <option value="curator">Curator</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={submitting}>
            {submitting ? "Adding…" : "Add user"}
          </Button>
        </div>
      </form>
    </div>
  );
}

function AuditTab() {
  const [entries, setEntries] = useState<AuditLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function load() {
    adminApi
      .auditLog()
      .then(setEntries)
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!entries) return <Spinner />;

  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-xs uppercase tracking-wide text-[var(--color-text-muted)]">
          <tr>
            <th className="text-left px-4 py-2 font-medium">When</th>
            <th className="text-left px-4 py-2 font-medium">Action</th>
            <th className="text-left px-4 py-2 font-medium">Resource</th>
            <th className="text-left px-4 py-2 font-medium">IP</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-border)]">
          {entries.map((e) => (
            <tr key={e.id}>
              <td className="px-4 py-2 text-[var(--color-text-muted)] whitespace-nowrap">
                {new Date(e.created_at).toLocaleString()}
              </td>
              <td className="px-4 py-2">{e.action}</td>
              <td className="px-4 py-2 text-[var(--color-text-muted)]">
                {e.resource_type} {e.resource_id?.slice(0, 8)}
              </td>
              <td className="px-4 py-2 text-[var(--color-text-muted)]">{e.ip_address || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SettingsTab() {
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminApi
      .ingestionSettings()
      .then(setSettings)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;
  if (!settings) return <Spinner />;

  return (
    <div className="bg-white border border-[var(--color-border)] rounded-lg p-4">
      <p className="text-xs text-[var(--color-text-muted)] mb-3">
        Read-only. These come from the deployment's environment configuration — change them by updating .env and
        restarting the backend, not here.
      </p>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
        {Object.entries(settings).map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-[var(--color-text-muted)]">{key}</dt>
            <dd className="font-mono text-xs">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
