import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../../services/api";
import toast from "react-hot-toast";
import type { ReportResponse } from "../../types/report";

export default function ReportsListPage() {
  const [reports, setReports] = useState<ReportResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchReports = async () => {
    try {
      const res = await API.get("/reports/");
      setReports(res.data);
    } catch {
      setError("Failed to load reports.");
      toast.error("Failed to load reports");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        Loading Reports...
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 text-red-400 flex items-center justify-center">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4 md:space-y-6">

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold md:text-3xl">My Reports</h1>

        <Link
          to="/generate-report"
          className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2 rounded-lg transition"
        >
          Generate New Report
        </Link>
      </div>

      {reports.length === 0 ? (
        <div className="bg-gray-900 p-8 rounded-xl text-center text-gray-400">
          No reports found. Generate your first AI insight report.
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report) => (
            <div
              key={report.id}
              className="flex flex-col gap-4 rounded-xl bg-gray-900 p-4 transition hover:bg-gray-800 sm:flex-row sm:items-center sm:justify-between sm:p-6"
            >
              <div>
                <p className="text-lg font-semibold">
                  {report.title || `Report #${report.id}`}
                </p>
                <p className="text-sm text-gray-400">
                  Created: {new Date(report.created_at).toLocaleString()}
                </p>
                <p className="text-xs text-indigo-400 mt-1">
                  Tier: {(report.content?.meta?.plan_tier || "basic").toUpperCase()}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Sections: {report.content?.meta?.section_count ?? report.content?.section_selector?.selected_section_count ?? "--"}
                </p>
              </div>

              <Link
                to={`/reports/${report.id}`}
                className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg transition"
              >
                View
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
