import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import API from "../../services/api";
import toast from "react-hot-toast";
import type { ReportResponse as _ReportResponse } from "../../types/report";

interface ReportContentMeta {
  plan_tier?: string;
  section_count?: number;
}

interface ReportContentSectionSelector {
  selected_section_count?: number;
}

interface ReportContent {
  meta?: ReportContentMeta;
  section_selector?: ReportContentSectionSelector;
}

interface SafeReportResponse {
  id: string | number;
  title?: string;
  created_at: string;
  content?: ReportContent;
}

export default function ReportsListPage() {
  const [reports, setReports] = useState<SafeReportResponse[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>("");

  const fetchReports = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const res = await API.get("/reports/");
      
      // Type guard to ensure data structure
      const safeReports: SafeReportResponse[] = Array.isArray(res.data) 
        ? res.data.map((report: any) => ({
            id: report.id || '',
            title: report.title,
            created_at: report.created_at || new Date().toISOString(),
            content: report.content
          }))
        : [];
      
      setReports(safeReports);
    } catch (err) {
      const errorMessage = "Failed to load reports.";
      setError(errorMessage);
      toast.error(errorMessage);
      console.error("Fetch reports error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          Loading Reports...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 text-red-400 flex items-center justify-center p-8">
        <div className="text-center max-w-md">
          <h2 className="text-xl font-bold mb-4">Error Loading Reports</h2>
          <p>{error}</p>
          <button
            onClick={fetchReports}
            className="mt-4 bg-indigo-600 hover:bg-indigo-500 px-6 py-2 rounded-lg transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-8 space-y-4 md:space-y-6">
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold md:text-3xl">My Reports</h1>
        <Link
          to="/generate-report"
          className="bg-indigo-600 hover:bg-indigo-500 px-5 py-2 rounded-lg transition text-white font-medium shadow-lg hover:shadow-xl"
        >
          Generate New Report
        </Link>
      </div>

      {reports.length === 0 ? (
        <div className="bg-gray-900 p-8 rounded-xl text-center text-gray-400 border-2 border-dashed border-gray-700">
          <div className="max-w-md mx-auto">
            <h3 className="text-lg font-semibold text-gray-300 mb-2">No reports yet</h3>
            <p>Generate your first AI insight report to get started.</p>
          </div>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <div
              key={String(report.id)}
              className="flex flex-col gap-4 rounded-xl bg-gray-900 p-6 transition-all duration-200 hover:bg-gray-800 hover:shadow-2xl hover:-translate-y-1 border border-gray-800 sm:flex-row sm:items-center sm:justify-between"
            >
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold truncate mb-1">
                  {report.title || `Report #${report.id}`}
                </h3>
                <p className="text-sm text-gray-400 mb-2">
                  Created: {new Date(report.created_at).toLocaleString()}
                </p>
                <div className="space-y-1 text-xs">
                  <p className="text-indigo-400 font-medium">
                    Tier: {((report.content?.meta?.plan_tier || "basic") ?? "basic").toUpperCase()}
                  </p>
                  <p className="text-gray-500">
                    Sections: {report.content?.meta?.section_count ?? 
                             report.content?.section_selector?.selected_section_count ?? 
                             "--"}
                  </p>
                </div>
              </div>

              <Link
                to={`/reports/${report.id}`}
                className="bg-indigo-600 hover:bg-indigo-500 px-6 py-2 rounded-lg transition-all duration-200 font-medium shadow-lg hover:shadow-xl whitespace-nowrap"
              >
                View Report
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}