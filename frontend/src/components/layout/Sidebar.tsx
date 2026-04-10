import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

type SidebarProps = {
  mobileOpen: boolean;
  onClose: () => void;
};

const Sidebar = ({ mobileOpen, onClose }: SidebarProps) => {
  const { user } = useAuth();
  const location = useLocation();

  const linkClass = (path: string) =>
    `block rounded px-3 py-2 transition ${
      location.pathname.startsWith(path)
        ? "bg-gray-800 text-white"
        : "text-gray-400 hover:text-indigo-400"
    }`;

  const canManageUsers =
    user?.role === "admin" || user?.role === "super_admin";
  const isSuperAdmin = user?.role === "super_admin";

  return (
    <>
      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/45 lg:hidden"
          aria-label="Close navigation"
          onClick={onClose}
        />
      ) : null}

      <aside
        className={`fixed left-0 top-0 z-40 h-full w-64 bg-gray-900 p-4 text-white transition-transform duration-200 lg:static lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center justify-between lg:justify-start">
          <h2 className="text-xl font-bold">LifeSignify</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-gray-700 px-2 py-1 text-xs text-gray-300 lg:hidden"
          >
            Close
          </button>
        </div>

        <nav className="space-y-2">
          <Link to="/dashboard" className={linkClass("/dashboard")}>
            Dashboard
          </Link>

          <Link to="/reports" className={linkClass("/reports")}>
            Reports
          </Link>

          <Link to="/billing" className={linkClass("/billing")}>
            Billing
          </Link>

          <Link to="/settings" className={linkClass("/settings")}>
            Settings
          </Link>

          <Link to="/swarkigyan" className={linkClass("/swarkigyan")}>
            SwarPrana AI
          </Link>

          {canManageUsers && (
            <>
              <Link to="/admin" className={linkClass("/admin")}>
                {isSuperAdmin ? "Super Admin Dashboard" : "Admin Dashboard"}
              </Link>
              <Link to="/admin/users" className={linkClass("/admin/users")}>
                {isSuperAdmin ? "Global User Manager" : "User Manager"}
              </Link>
              {isSuperAdmin && (
                <Link to="/admin/knowledge" className={linkClass("/admin/knowledge")}>
                  Knowledge Studio
                </Link>
              )}
            </>
          )}
        </nav>
      </aside>
    </>
  );
};

export default Sidebar;
