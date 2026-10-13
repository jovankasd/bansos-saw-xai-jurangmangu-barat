import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { AppShell } from "./components/layout/AppShell";

// Placeholder Dashboard View for Task 6 Verification
const DashboardPlaceholder: React.FC = () => {
  const { user } = useAuth();
  return (
    <AppShell
      title="Dashboard Adjudikasi"
      breadcrumb={["Tata Kelola", "Ringkasan Eksekutif"]}
    >
      <div className="space-y-6">
        <div className="bg-white rounded-xl p-6 border border-border-subtle shadow-sm">
          <h2 className="text-xl font-bold text-on-surface">
            Selamat Datang, {user?.name || "Staf Kelurahan"}
          </h2>
          <p className="text-sm text-on-surface-variant mt-1">
            Sistem Pendukung Keputusan Hibrida SAW & XAI Bansos Jurangmangu Barat.
          </p>
        </div>
      </div>
    </AppShell>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="/admin/dashboard" element={<DashboardPlaceholder />} />
          <Route path="/admin/*" element={<DashboardPlaceholder />} />
          <Route path="/cek-bansos" element={<div>Portal Publik Cek Bansos</div>} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
