import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../../context/AuthContext";
import {
  createManualUser,
  deleteUser,
  fetchAllRegisteredUsers,
  fetchOrgUsers,
  inviteUser,
  setUserBlocked,
  updateUserRole,
  type OrgUser,
} from "../../services/adminService";
import AdminUsersTable from "../../components/admin/AdminUsersTable";

const PAGE_SIZE = 10;

function buildCsv(users: OrgUser[]) {
  const header = [
    "id",
    "full_name",
    "email",
    "mobile_number",
    "role",
    "organization_name",
    "organization_plan",
    "signup_source",
    "signup_city",
    "signup_country",
    "signup_ip",
    "signup_locale",
    "signup_timezone",
    "created_at",
  ];
  const rows = users.map((u) => [
    String(u.id),
    String(u.full_name || ""),
    String(u.email || ""),
    String(u.mobile_number || ""),
    String(u.role || ""),
    String(u.organization_name || ""),
    String(u.organization_plan || ""),
    String(u.signup_source || ""),
    String(u.signup_city || ""),
    String(u.signup_country || ""),
    String(u.signup_ip || ""),
    String(u.signup_locale || ""),
    String(u.signup_timezone || ""),
    String(u.created_at || ""),
  ]);
  return [header, ...rows]
    .map((cols) =>
      cols
        .map((c) => `"${String(c).replace(/"/g, '""')}"`)
        .join(",")
    )
    .join("\n");
}

function downloadCsv(filename: string, body: string) {
  const blob = new Blob([body], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function AdminUsersPage() {
  const { user } = useAuth();
  const [users, setUsers] = useState<OrgUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [page, setPage] = useState(1);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("user");
  const [inviteLoading, setInviteLoading] = useState(false);

  const [roleUpdateBusyId, setRoleUpdateBusyId] = useState<number | null>(null);
  const [deleteBusyId, setDeleteBusyId] = useState<number | null>(null);
  const [blockBusyId, setBlockBusyId] = useState<number | null>(null);

  const [manualName, setManualName] = useState("");
  const [manualMobile, setManualMobile] = useState("");
  const [manualEmail, setManualEmail] = useState("");
  const [manualPassword, setManualPassword] = useState("");
  const [manualRole, setManualRole] = useState<"admin" | "manager" | "user">("user");
  const [manualOrgName, setManualOrgName] = useState("");
  const [manualCreating, setManualCreating] = useState(false);

  const loadUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data =
        user?.role === "super_admin"
          ? await fetchAllRegisteredUsers()
          : await fetchOrgUsers();
      setUsers(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    loadUsers();
  }, [user?.role]);

  useEffect(() => {
    setPage(1);
  }, [search, roleFilter]);

  const filteredUsers = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users
      .filter((u) => {
        if (roleFilter !== "all" && u.role !== roleFilter) return false;
        if (!q) return true;
        const email = (u.email || "").toLowerCase();
        return email.includes(q) || String(u.id).includes(q);
      })
      .sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bTime - aTime;
      });
  }, [users, search, roleFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pagedUsers = filteredUsers.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const roleCounts = useMemo(() => {
    return users.reduce(
      (acc, u) => {
        acc.total += 1;
        if (u.role === "admin") acc.admin += 1;
        if (u.role === "manager") acc.manager += 1;
        if (u.role === "user") acc.user += 1;
        return acc;
      },
      { total: 0, admin: 0, manager: 0, user: 0 }
    );
  }, [users]);

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const handleDelete = async (id: number) => {
    clearMessages();
    const target = users.find((u) => u.id === id);
    const confirmed = window.confirm(
      `Delete user ${target?.email || `#${id}`}? This marks the user as deleted.`
    );
    if (!confirmed) return;

    setDeleteBusyId(id);
    try {
      await deleteUser(id);
      setSuccess("User deleted successfully.");
      await loadUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to delete user.");
    } finally {
      setDeleteBusyId(null);
    }
  };

  const handleRoleChange = async (id: number, role: string) => {
    clearMessages();
    setRoleUpdateBusyId(id);
    try {
      await updateUserRole(id, role);
      setSuccess("Role updated successfully.");
      await loadUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update role.");
    } finally {
      setRoleUpdateBusyId(null);
    }
  };

  const handleInvite = async () => {
    clearMessages();

    const email = inviteEmail.trim().toLowerCase();
    if (!email) {
      setError("Invite email is required.");
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      setError("Enter a valid email address.");
      return;
    }

    setInviteLoading(true);
    try {
      const res = await inviteUser(email, inviteRole);
      setSuccess(
        `User invited. Temporary password: ${res.temporary_password}`
      );
      setInviteEmail("");
      setInviteRole("user");
      await loadUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to invite user.");
    } finally {
      setInviteLoading(false);
    }
  };

  const handleManualCreate = async () => {
    clearMessages();
    if (!manualEmail.trim() && !manualMobile.trim()) {
      setError("Manual create requires at least mobile number or email.");
      return;
    }

    setManualCreating(true);
    try {
      const result = await createManualUser({
        full_name: manualName.trim() || undefined,
        mobile_number: manualMobile.trim() || undefined,
        email: manualEmail.trim().toLowerCase() || undefined,
        password: manualPassword.trim() || undefined,
        role: manualRole,
        organization_name: manualOrgName.trim() || undefined,
        organization_plan: "basic",
        kyc_verified: true,
      });

      setSuccess(
        `Manual user created (ID: ${result.id}). Login password: ${result.generated_password}`
      );
      setManualName("");
      setManualMobile("");
      setManualEmail("");
      setManualPassword("");
      setManualOrgName("");
      setManualRole("user");
      await loadUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create user manually.");
    } finally {
      setManualCreating(false);
    }
  };

  const handleToggleBlock = async (id: number, blocked: boolean) => {
    clearMessages();
    setBlockBusyId(id);
    try {
      await setUserBlocked(id, blocked);
      setSuccess(blocked ? "User blocked successfully." : "User unblocked successfully.");
      await loadUsers();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to update block status.");
    } finally {
      setBlockBusyId(null);
    }
  };

  const handleExport = () => {
    const csv = buildCsv(filteredUsers);
    const stamp = new Date().toISOString().slice(0, 10);
    downloadCsv(`users-export-${stamp}.csv`, csv);
    setSuccess("CSV export downloaded.");
  };

  return (
    <div className="space-y-4 md:space-y-5">
      <div className="rounded-2xl border border-gray-800 bg-gradient-to-r from-gray-900 to-gray-950 p-6">
        <h1 className="text-2xl font-semibold text-white md:text-3xl">User Manager</h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-300">
          Manage registered users, assign roles, invite operators, and export
          lists for operations.
        </p>
        <p className="mt-2 text-xs uppercase tracking-[0.14em] text-indigo-300">
          {user?.role === "super_admin"
            ? "Global View: All Registered Users"
            : "Organization View: Tenant Users"}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <p className="text-xs text-gray-400">Total Users</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {roleCounts.total}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <p className="text-xs text-gray-400">Admins</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {roleCounts.admin}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <p className="text-xs text-gray-400">Managers</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {roleCounts.manager}
          </p>
        </div>
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <p className="text-xs text-gray-400">Users</p>
          <p className="mt-1 text-2xl font-semibold text-white">
            {roleCounts.user}
          </p>
        </div>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-700/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-xl border border-emerald-700/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
          {success}
        </div>
      ) : null}

      {user?.role === "super_admin" ? (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
          <h2 className="text-lg font-semibold text-white">Super Admin - Manual User Create</h2>
          <p className="mt-2 text-sm text-gray-400">
            Add users directly without signup/KYC flow. Useful for onboarding or recovery.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <input
              type="text"
              placeholder="Full Name"
              value={manualName}
              onChange={(e) => setManualName(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <input
              type="text"
              placeholder="Mobile Number"
              value={manualMobile}
              onChange={(e) => setManualMobile(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <input
              type="email"
              placeholder="Email (Optional)"
              value={manualEmail}
              onChange={(e) => setManualEmail(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <input
              type="text"
              placeholder="Password (optional, auto-generated if empty)"
              value={manualPassword}
              onChange={(e) => setManualPassword(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <input
              type="text"
              placeholder="Organization Name (optional)"
              value={manualOrgName}
              onChange={(e) => setManualOrgName(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <select
              value={manualRole}
              onChange={(e) => setManualRole(e.target.value as "admin" | "manager" | "user")}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            >
              <option value="user">User</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <button
            onClick={handleManualCreate}
            disabled={manualCreating}
            className="mt-4 rounded-lg border border-indigo-500/40 bg-indigo-500/20 px-4 py-2 font-medium text-indigo-200 hover:bg-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {manualCreating ? "Creating..." : "Create User Manually"}
          </button>
        </div>
      ) : (
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
          <h2 className="text-lg font-semibold text-white">Invite New User</h2>
          <div className="mt-4 flex flex-col gap-3 md:flex-row">
            <input
              type="email"
              placeholder="name@company.com"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            />

            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-white outline-none ring-indigo-500 focus:ring-2"
            >
              <option value="user">User</option>
              <option value="manager">Manager</option>
              <option value="admin">Admin</option>
            </select>

            <button
              onClick={handleInvite}
              disabled={inviteLoading}
              className="rounded-lg border border-indigo-500/40 bg-indigo-500/20 px-4 py-2 font-medium text-indigo-200 hover:bg-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {inviteLoading ? "Inviting..." : "Invite User"}
            </button>
          </div>
        </div>
      )}

      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <h2 className="text-lg font-semibold text-white">Registered Users</h2>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by email or ID"
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white outline-none ring-indigo-500 focus:ring-2"
            />
            <select
              value={roleFilter}
              onChange={(e) => setRoleFilter(e.target.value)}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white outline-none ring-indigo-500 focus:ring-2"
            >
              <option value="all">All Roles</option>
              <option value="admin">Admin</option>
              <option value="manager">Manager</option>
              <option value="user">User</option>
            </select>
            <button
              onClick={handleExport}
              className="rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm font-medium text-gray-100 hover:bg-gray-700"
            >
              Export CSV
            </button>
          </div>
        </div>

        <div className="mt-4">
          {loading ? (
            <div className="rounded-xl border border-gray-800 bg-gray-950/40 p-5 text-gray-300">
              Loading users...
            </div>
          ) : (
            <AdminUsersTable
              users={pagedUsers}
              currentUserId={user?.id}
              showGlobalColumns={user?.role === "super_admin"}
              roleUpdateBusyId={roleUpdateBusyId}
              deleteBusyId={deleteBusyId}
              blockBusyId={blockBusyId}
              onDelete={handleDelete}
              onRoleChange={handleRoleChange}
              onToggleBlock={user?.role === "super_admin" ? handleToggleBlock : undefined}
            />
          )}
        </div>

        <div className="mt-4 flex flex-col gap-2 text-sm text-gray-400 sm:flex-row sm:items-center sm:justify-between">
          <p>
            Showing {(currentPage - 1) * PAGE_SIZE + (pagedUsers.length ? 1 : 0)}-
            {(currentPage - 1) * PAGE_SIZE + pagedUsers.length} of{" "}
            {filteredUsers.length}
          </p>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="rounded-md border border-gray-700 px-2 py-1 text-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            <span className="text-gray-300">
              Page {currentPage} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage >= totalPages}
              className="rounded-md border border-gray-700 px-2 py-1 text-gray-200 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
