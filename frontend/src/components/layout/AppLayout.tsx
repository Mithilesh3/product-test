import { Outlet, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export default function AppLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-dvh bg-gray-950 text-white">
      <Sidebar mobileOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onMenuToggle={() => setMobileNavOpen((prev) => !prev)} />
        <main className="flex-1 overflow-auto p-3 sm:p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
