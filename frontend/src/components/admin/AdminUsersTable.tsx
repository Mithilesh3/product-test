import type { OrgUser } from "../../services/adminService";

type Props = {
  users: OrgUser[];
  currentUserId?: number;
  showGlobalColumns?: boolean;
  roleUpdateBusyId?: number | null;
  deleteBusyId?: number | null;
  blockBusyId?: number | null;
  onDelete: (id: number) => void;
  onRoleChange: (id: number, role: string) => void;
  onToggleBlock?: (id: number, blocked: boolean) => void;
};

const ROLE_OPTIONS = ["admin", "manager", "user"];

export default function AdminUsersTable({
  users,
  currentUserId,
  showGlobalColumns = false,
  roleUpdateBusyId,
  deleteBusyId,
  blockBusyId,
  onDelete,
  onRoleChange,
  onToggleBlock,
}: Props) {
  if (!users.length) {
    return (
      <div className="rounded-2xl border border-gray-800 bg-gray-900 p-6 text-gray-400">
        No users found for selected filters.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-gray-800 bg-gray-900">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[900px] text-left text-sm text-gray-200">
          <thead className="bg-gray-950/60 text-xs uppercase tracking-wider text-gray-400">
            <tr>
              <th className="px-4 py-3 font-medium">User</th>
              {showGlobalColumns ? (
                <th className="px-4 py-3 font-medium">Organization</th>
              ) : null}
              {showGlobalColumns ? (
                <th className="px-4 py-3 font-medium">Signup Details</th>
              ) : null}
              <th className="px-4 py-3 font-medium">Role</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>

          <tbody>
            {users.map((u) => {
              const isSelf = currentUserId === u.id;
              const isRoleBusy = roleUpdateBusyId === u.id;
              const isDeleteBusy = deleteBusyId === u.id;
              const isBlockBusy = blockBusyId === u.id;

              return (
                <tr key={u.id} className="border-t border-gray-800/90">
                  <td className="px-4 py-3">
                    <div className="font-medium text-white">{u.full_name || "No name"}</div>
                    <div className="text-xs text-gray-300">{u.email || "No email"}</div>
                    <div className="text-xs text-gray-400">User ID: {u.id}</div>
                    {u.mobile_number ? (
                      <div className="text-xs text-gray-400">Mobile: {u.mobile_number}</div>
                    ) : null}
                  </td>

                  {showGlobalColumns ? (
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-200">
                        {u.organization_name || `Tenant ${u.tenant_id || "-"}`}
                      </div>
                      <div className="text-xs text-gray-400 capitalize">
                        Plan: {u.organization_plan || "-"}
                      </div>
                    </td>
                  ) : null}

                  {showGlobalColumns ? (
                    <td className="px-4 py-3">
                      <div className="text-xs text-gray-200">
                        Source: {u.signup_source || "-"}
                      </div>
                      <div className="text-xs text-gray-400">
                        Location: {u.signup_city || "-"}, {u.signup_country || "-"}
                      </div>
                      <div className="text-xs text-gray-400">
                        IP: {u.signup_ip || "-"}
                      </div>
                    </td>
                  ) : null}

                  <td className="px-4 py-3">
                    <select
                      value={u.role}
                      disabled={isRoleBusy}
                      onChange={(e) => onRoleChange(u.id, e.target.value)}
                      className="w-36 rounded-lg border border-gray-700 bg-gray-800 px-2 py-1.5 text-sm text-white disabled:opacity-60"
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role} value={role}>
                          {role}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td className="px-4 py-3 text-gray-300">
                    {u.created_at
                      ? new Date(u.created_at).toLocaleString()
                      : "-"}
                  </td>

                  <td className="px-4 py-3">
                    {u.is_blocked ? (
                      <span className="inline-flex rounded-full border border-rose-700/40 bg-rose-500/10 px-2.5 py-1 text-xs text-rose-300">
                        Blocked
                      </span>
                    ) : u.kyc_verified === false ? (
                      <span className="inline-flex rounded-full border border-amber-700/40 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200">
                        KYC Pending
                      </span>
                    ) : (
                      <span className="inline-flex rounded-full border border-emerald-700/40 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-300">
                        Active
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {onToggleBlock ? (
                        <button
                          disabled={isSelf || isBlockBusy}
                          onClick={() => onToggleBlock(u.id, !u.is_blocked)}
                          className={`rounded-lg border px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed disabled:opacity-40 ${
                            u.is_blocked
                              ? "border-emerald-700/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                              : "border-amber-700/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20"
                          }`}
                          title={isSelf ? "You cannot block your own account" : u.is_blocked ? "Unblock user" : "Block user"}
                        >
                          {isBlockBusy ? "Saving..." : u.is_blocked ? "Unblock" : "Block"}
                        </button>
                      ) : null}

                      <button
                        disabled={isSelf || isDeleteBusy}
                        onClick={() => onDelete(u.id)}
                        className="rounded-lg border border-rose-700/40 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 disabled:cursor-not-allowed disabled:opacity-40"
                        title={isSelf ? "You cannot delete your own account" : "Delete user"}
                      >
                        {isDeleteBusy ? "Deleting..." : "Delete"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
