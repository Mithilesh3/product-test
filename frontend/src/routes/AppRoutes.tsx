import { Suspense, lazy } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

import AppLayout from "../components/layout/AppLayout";

import DashboardPage from "../pages/dashboard/DashboardPage";
import ReportsListPage from "../pages/reports/ReportsListPage";
import GenerateReportPage from "../pages/reports/GenerateReportPage"; // ✅ NEW

import UpgradePage from "../pages/upgrade/UpgradePage";
import BillingPage from "../pages/billing/BillingPage";
import SettingsPage from "../pages/settings/SettingsPage";
import SwarkigyanPage from "../pages/swarkigyan/SwarkigyanPage";

import AdminDashboard from "../pages/admin/AdminDashboard";
import AdminUsersPage from "../pages/admin/AdminUsersPage";
import AdminKnowledgePage from "../pages/admin/AdminKnowledgePage";

import CosmicLogin from "../pages/CosmicLogin";
import RegisterPage from "../pages/auth/RegisterPage";
import SuperAdminLoginPage from "../pages/auth/SuperAdminLoginPage";

import NotFoundPage from "../pages/errors/NotFoundPage";
import ForbiddenPage from "../pages/errors/ForbiddenPage";

import ProtectedRoute from "../components/ProtectedRoute";
import AdminRoute from "./AdminRoute";
import SuperAdminRoute from "./SuperAdminRoute";

const ReportDetailPage = lazy(() => import("../pages/reports/ReportDetailPage"));

export default function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950 text-white">
        Loading...
      </div>
    );
  }

  return (
    <Routes>
      {/* PUBLIC ROUTES */}
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <CosmicLogin />}
      />

      <Route
        path="/register"
        element={user ? <Navigate to="/dashboard" replace /> : <RegisterPage />}
      />

      <Route
        path="/super-admin/login"
        element={user ? <Navigate to="/dashboard" replace /> : <SuperAdminLoginPage />}
      />

      {/* PROTECTED ROUTES WITH LAYOUT */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="reports" element={<ReportsListPage />} />
        <Route
          path="reports/:id"
          element={
            <Suspense
              fallback={
                <div className="min-h-screen bg-[#efe7d7] text-[#173a63] flex items-center justify-center">
                  Loading report...
                </div>
              }
            >
              <ReportDetailPage />
            </Suspense>
          }
        />
        
        {/* ✅ NEW ROUTE ADDED HERE */}
        <Route path="generate-report" element={<GenerateReportPage />} />

        <Route path="settings" element={<SettingsPage />} />
        <Route path="swarkigyan" element={<SwarkigyanPage />} />
        <Route path="upgrade" element={<UpgradePage />} />

        {/* BILLING (Plan Protected) */}
        <Route
          path="billing"
          element={<BillingPage />}
        />

        {/* ADMIN ROUTES */}
        <Route
          path="admin"
          element={
            <AdminRoute>
              <AdminDashboard />
            </AdminRoute>
          }
        />

        <Route
          path="admin/users"
          element={
            <AdminRoute>
              <AdminUsersPage />
            </AdminRoute>
          }
        />

        <Route
          path="admin/knowledge"
          element={
            <SuperAdminRoute>
              <AdminKnowledgePage />
            </SuperAdminRoute>
          }
        />
      </Route>

      {/* ERROR ROUTES */}
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
