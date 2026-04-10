import { useUsage } from "../../context/UsageContext";
import { Navigate } from "react-router-dom";

interface ReportGuardProps {
  children: React.ReactNode;
}

export default function ReportGuard({ children }: ReportGuardProps) {
  const { usage } = useUsage();

  // Still loading usage
  if (!usage) {
    return (
      <div className="flex items-center justify-center h-screen text-white">
        Checking plan...
      </div>
    );
  }

  const { reports_used, reports_limit } = usage;

  // No reports allowed OR limit reached
  if (reports_limit <= 0 || reports_used >= reports_limit) {
    return <Navigate to="/billing" replace />;
  }

  return <>{children}</>;
}