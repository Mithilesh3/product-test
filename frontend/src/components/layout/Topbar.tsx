import { useMemo } from "react";
import { useLocation } from "react-router-dom";

type TopbarProps = {
  onMenuToggle: () => void;
};

function resolveTitle(pathname: string) {
  if (pathname.startsWith("/reports/")) return "Report Details";
  if (pathname.startsWith("/generate-report")) return "Generate Report";

  const titleMap: Record<string, string> = {
    "/dashboard": "Dashboard",
    "/reports": "Reports",
    "/billing": "Billing",
    "/settings": "Settings",
    "/swarkigyan": "SwarPrana AI",
    "/admin": "Admin Dashboard",
    "/admin/users": "User Manager",
    "/admin/knowledge": "Knowledge Studio",
    "/upgrade": "Upgrade",
  };

  return titleMap[pathname] || "LifeSignify";
}

const Topbar = ({ onMenuToggle }: TopbarProps) => {
  const location = useLocation();
  const title = useMemo(() => resolveTitle(location.pathname), [location.pathname]);

  return (
    <header className="flex h-16 items-center justify-between border-b border-gray-800 bg-gray-900 px-3 text-white sm:px-4 md:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuToggle}
          className="rounded-md border border-gray-700 px-2 py-1 text-sm text-gray-200 lg:hidden"
          aria-label="Open navigation menu"
        >
          Menu
        </button>
        <h1 className="font-semibold">{title}</h1>
      </div>
      <div className="hidden text-sm text-gray-400 sm:block">Welcome</div>
    </header>
  );
};

export default Topbar;
