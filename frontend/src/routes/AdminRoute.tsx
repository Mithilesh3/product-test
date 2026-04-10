import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface AdminRouteProps {
  children: React.ReactNode;
}

export default function AdminRoute({ children }: AdminRouteProps) {
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

  // Allow both admin and super_admin
  if (user.role !== "admin" && user.role !== "super_admin") {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}