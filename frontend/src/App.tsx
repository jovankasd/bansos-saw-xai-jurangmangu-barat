import React, { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";

// Route-level code-splitting for performance & small initial bundle
const PublicPortalPage = lazy(() =>
  import("./pages/PublicPortalPage").then((m) => ({ default: m.PublicPortalPage }))
);
const LoginPage = lazy(() =>
  import("./pages/LoginPage").then((m) => ({ default: m.LoginPage }))
);
const ExecutiveDashboardPage = lazy(() =>
  import("./pages/dashboard/ExecutiveDashboardPage").then((m) => ({
    default: m.ExecutiveDashboardPage,
  }))
);
const CriteriaManagementPage = lazy(() =>
  import("./pages/dashboard/CriteriaManagementPage").then((m) => ({
    default: m.CriteriaManagementPage,
  }))
);
const SurveyorInputPage = lazy(() =>
  import("./pages/dashboard/SurveyorInputPage").then((m) => ({
    default: m.SurveyorInputPage,
  }))
);
const SawRankingPage = lazy(() =>
  import("./pages/dashboard/SawRankingPage").then((m) => ({
    default: m.SawRankingPage,
  }))
);
const XaiGeneratorPage = lazy(() =>
  import("./pages/dashboard/XaiGeneratorPage").then((m) => ({
    default: m.XaiGeneratorPage,
  }))
);
const LurahApprovalPage = lazy(() =>
  import("./pages/dashboard/LurahApprovalPage").then((m) => ({
    default: m.LurahApprovalPage,
  }))
);
const ThesisEvaluationPage = lazy(() =>
  import("./pages/dashboard/ThesisEvaluationPage").then((m) => ({
    default: m.ThesisEvaluationPage,
  }))
);

// Accessible civic page loading fallback
const PageLoader: React.FC = () => (
  <div className="min-h-screen bg-surface flex items-center justify-center p-6">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-3 border-primary border-t-transparent rounded-full animate-spin" />
      <span className="text-xs font-mono text-secondary">
        Memuat Sistem Bansos JUBAR...
      </span>
    </div>
  </div>
);

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<Navigate to="/cek-bansos" replace />} />
            <Route path="/cek-bansos" element={<PublicPortalPage />} />
            <Route path="/admin/login" element={<LoginPage />} />

            {/* Protected Admin Routes with RBAC Guards */}
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "VIEWER"]}>
                  <ExecutiveDashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/criteria"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
                  <CriteriaManagementPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/citizens"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "SURVEYOR"]}>
                  <SurveyorInputPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/selection"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
                  <SawRankingPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/xai"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
                  <XaiGeneratorPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/berita-acara"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "VIEWER"]}>
                  <LurahApprovalPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/evaluation"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
                  <ThesisEvaluationPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/audit"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "VIEWER"]}>
                  <ExecutiveDashboardPage />
                </ProtectedRoute>
              }
            />
            {/* Fallback Catch-All */}
            <Route
              path="/admin/*"
              element={
                <ProtectedRoute>
                  <ExecutiveDashboardPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
