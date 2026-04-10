import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface SuperAdminRouteProps {
  children: React.ReactNode;
}

export default function SuperAdminRoute({ children }: SuperAdminRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (user.role !== "super_admin") {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}
