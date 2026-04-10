import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import { useUsage } from "../../context/UsageContext";
import toast from "react-hot-toast";
import { motion } from "framer-motion";
import type { ReportResponse } from "../../types/report";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const { usage } = useUsage();
  const navigate = useNavigate();

  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);

  const rawPlan = user?.subscription?.plan_name?.toLowerCase() || "none";
  const currentPlan =
    rawPlan === "pro" ? "standard" : rawPlan === "premium" ? "enterprise" : rawPlan;

  const isActive = user?.subscription?.is_active ?? false;

  const used = usage?.reports_used || 0;
  const limit = usage?.reports_limit || 0;
  const remaining = Math.max(limit - used, 0);

  const usagePercent =
    limit > 0 ? Math.min((used / limit) * 100, 100) : 0;

  const fetchReports = async () => {
    try {
      const res = await API.get("/reports/");
      setReports(res.data);
    } catch {
      toast.error("Failed to fetch reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const latestReport = reports[0];
  const coreMetrics = latestReport?.content?.core_metrics;
  const lifeStability =
    coreMetrics?.life_stability_index ??
    latestReport?.content?.deterministic?.numbers?.personal_year;
  const riskBand = coreMetrics?.risk_band || "--";

  return (
    <div className="space-y-6 md:space-y-8">

      {/* HEADER */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-bold md:text-3xl">
            Welcome back, {user?.full_name || user?.mobile_number || user?.email || "User"}
          </h1>
          <p className="text-gray-400 mt-1">
            Your Life Intelligence Executive Dashboard
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <PlanBadge plan={currentPlan} />
          <button
            onClick={logout}
            className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded-lg text-sm font-semibold transition"
          >
            Logout
          </button>
        </div>
      </div>

      {/* USAGE BAR */}
      <div className="rounded-2xl bg-gray-900 p-4 shadow-lg sm:p-6">
        <div className="flex justify-between text-sm mb-2">
          <span>
            Reports Used: {used} / {limit}
          </span>
          <span>{remaining} remaining</span>
        </div>

        <div className="w-full bg-gray-800 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all ${
              usagePercent > 80
                ? "bg-red-500"
                : usagePercent > 50
                ? "bg-yellow-500"
                : "bg-emerald-500"
            }`}
            style={{ width: `${usagePercent}%` }}
          />
        </div>
      </div>

      {/* KPI CARDS */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Total Reports"
          value={loading ? "..." : reports.length}
        />

        <MetricCard
          label="Latest Stability Score"
          value={lifeStability ?? "--"}
        />

        <MetricCard
          label="Overall Risk Level"
          value={riskBand}
        />

        <MetricCard
          label="Confidence Score"
          value={
            coreMetrics?.confidence_score !== undefined
              ? `${coreMetrics.confidence_score}`
              : "--"
          }
        />
      </div>

      {/* ACTIONS */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">

        {/* 🔥 Now only navigation — NOT API call */}
        <motion.button
          whileHover={{ scale: 1.03 }}
          onClick={() => navigate("/generate-report")}
          disabled={!isActive || limit <= 0 || used >= limit}
          className="bg-indigo-600 hover:bg-indigo-500 p-6 rounded-xl font-semibold transition disabled:opacity-50"
        >
          {!isActive || limit <= 0
            ? "No Active Plan"
            : used >= limit
            ? "Limit Reached"
            : "Generate AI Report"}
        </motion.button>

        <Link
          to="/reports"
          className="bg-indigo-600 hover:bg-indigo-500 p-6 rounded-xl font-semibold text-center"
        >
          View All Reports
        </Link>

        {(!isActive || used >= limit) && (
          <Link
            to="/billing"
            className="bg-emerald-600 hover:bg-emerald-500 p-6 rounded-xl font-semibold text-center"
          >
            Upgrade Plan
          </Link>
        )}
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: any }) {
  return (
    <motion.div
      whileHover={{ scale: 1.04 }}
      className="bg-gray-900 p-6 rounded-2xl shadow-lg"
    >
      <p className="text-sm text-gray-400">{label}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
    </motion.div>
  );
}

function PlanBadge({ plan }: { plan: string }) {
  return (
    <div
      className={`px-4 py-2 rounded-full text-sm font-semibold ${
        plan === "enterprise"
          ? "bg-purple-600"
          : plan === "standard"
          ? "bg-emerald-600"
          : "bg-gray-700"
      }`}
    >
      {plan.toUpperCase()} PLAN
    </div>
  );
}
