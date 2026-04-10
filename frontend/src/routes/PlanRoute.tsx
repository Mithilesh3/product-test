import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface PlanRouteProps {
  children: React.ReactNode;
}

export default function PlanRoute({ children }: PlanRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen text-white">
        Loading...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // If subscription inactive → send to billing
  if (!user.subscription?.is_active) {
    return <Navigate to="/billing" replace />;
  }

  return <>{children}</>;
}