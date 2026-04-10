import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import {
  fetchAdminAnalytics,
  fetchAllRegisteredUsers,
  fetchOrgUsers,
  type AdminAnalytics,
  type OrgUser,
} from "../../services/adminService";

type DashboardState =
  | { status: "loading" }
  | { status: "ready"; analytics: AdminAnalytics | null; users: OrgUser[] }
  | { status: "error"; message: string };

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5 shadow-sm">
      <p className="text-xs uppercase tracking-wider text-gray-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
      <p className="mt-2 text-sm text-gray-400">{hint}</p>
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [state, setState] = useState<DashboardState>({ status: "loading" });

  useEffect(() => {
    let mounted = true;

    const load = async () => {
      try {
        const isSuperAdmin = user?.role === "super_admin";
        const usersPromise = isSuperAdmin ? fetchAllRegisteredUsers() : fetchOrgUsers();
        const analyticsPromise = isSuperAdmin
          ? fetchAdminAnalytics()
          : Promise.resolve<AdminAnalytics | null>(null);

        const [analyticsResult, usersResult] = await Promise.allSettled([
          analyticsPromise,
          usersPromise,
        ]);

        if (!mounted) return;

        const analytics =
          analyticsResult.status === "fulfilled" ? analyticsResult.value : null;
        const users = usersResult.status === "fulfilled" ? usersResult.value : [];

        setState({ status: "ready", analytics, users });
      } catch {
        if (!mounted) return;
        setState({
          status: "error",
          message: "Unable to load admin dashboard at the moment.",
        });
      }
    };

    load();
    return () => {
      mounted = false;
    };
  }, [user?.role]);

  const recentUsers = useMemo(() => {
    if (state.status !== "ready") return [];
    return [...state.users]
      .sort((a, b) => {
        const aTime = a.created_at ? new Date(a.created_at).getTime() : 0;
        const bTime = b.created_at ? new Date(b.created_at).getTime() : 0;
        return bTime - aTime;
      })
      .slice(0, 6);
  }, [state]);

  if (state.status === "loading") {
    return <div className="p-4 text-gray-300 md:p-6">Loading admin dashboard...</div>;
  }

  if (state.status === "error") {
    return <div className="p-4 text-rose-300 md:p-6">{state.message}</div>;
  }

  const isSuperAdmin = user?.role === "super_admin";
  const usersCount =
    state.analytics?.total_users ?? state.users.length ?? 0;
  const reportsCount = state.analytics?.total_reports ?? 0;
  const orgCount = state.analytics?.total_organizations ?? 1;
  const activeSubs = state.analytics?.active_subscriptions ?? 0;

  return (
    <div className="space-y-5 md:space-y-6">
      <div className="rounded-2xl border border-gray-800 bg-gradient-to-r from-gray-900 to-gray-950 p-6">
        <p className="text-xs uppercase tracking-[0.18em] text-indigo-300">
          {isSuperAdmin ? "Super Admin Control" : "Admin Control"}
        </p>
        <h1 className="mt-2 text-3xl font-semibold text-white">
          {isSuperAdmin ? "Super Admin Operations Dashboard" : "Operations Dashboard"}
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-300">
          Manage registered users, role assignments, and onboarding health from
          one place. This panel uses existing secure backend endpoints.
        </p>
        {!isSuperAdmin ? (
          <div className="mt-4 rounded-xl border border-amber-700/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            Super admin analytics are restricted. You can still manage users in
            your organization.
          </div>
        ) : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total Users"
          value={String(usersCount)}
          hint="Registered accounts available in the system view."
        />
        <StatCard
          label="Total Reports"
          value={String(reportsCount)}
          hint="Generated reports count."
        />
        <StatCard
          label="Organizations"
          value={String(orgCount)}
          hint="Active tenant organizations."
        />
        <StatCard
          label="Active Subscriptions"
          value={String(activeSubs)}
          hint="Currently active paid plans."
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-[2fr,1fr]">
        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Recent Users</h2>
            <Link
              to="/admin/users"
              className="rounded-lg border border-indigo-500/50 px-3 py-1.5 text-sm font-medium text-indigo-300 hover:bg-indigo-500/10"
            >
              Open User Manager
            </Link>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-gray-400">
                <tr>
                  <th className="pb-2 pr-4 font-medium">Email</th>
                  <th className="pb-2 pr-4 font-medium">Role</th>
                  <th className="pb-2 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {recentUsers.length ? (
                  recentUsers.map((entry) => (
                    <tr key={entry.id} className="border-t border-gray-800">
                      <td className="py-2 pr-4 text-gray-200">
                        {entry.email || "No email"}
                      </td>
                      <td className="py-2 pr-4 text-gray-300 capitalize">
                        {entry.role}
                      </td>
                      <td className="py-2 text-gray-400">
                        {entry.created_at
                          ? new Date(entry.created_at).toLocaleDateString()
                          : "-"}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td className="py-4 text-gray-400" colSpan={3}>
                      No users available.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-2xl border border-gray-800 bg-gray-900 p-5">
          <h2 className="text-lg font-semibold text-white">Go-Live Checklist</h2>
          <ul className="mt-4 space-y-2 text-sm text-gray-300">
            <li>- Verify super admin login before launch.</li>
            <li>- Confirm invite flow for new operators.</li>
            <li>- Export user snapshot before release.</li>
            <li>- Keep one backup admin account.</li>
            <li>- Monitor /admin and /users API responses.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
