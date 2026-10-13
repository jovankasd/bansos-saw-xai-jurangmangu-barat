import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { PublicPortalPage } from "./pages/PublicPortalPage";
import { LoginPage } from "./pages/LoginPage";
import { ExecutiveDashboardPage } from "./pages/dashboard/ExecutiveDashboardPage";
import { CriteriaManagementPage } from "./pages/dashboard/CriteriaManagementPage";
import { SurveyorInputPage } from "./pages/dashboard/SurveyorInputPage";
import { SawRankingPage } from "./pages/dashboard/SawRankingPage";
import { XaiGeneratorPage } from "./pages/dashboard/XaiGeneratorPage";
import { LurahApprovalPage } from "./pages/dashboard/LurahApprovalPage";
import { ThesisEvaluationPage } from "./pages/dashboard/ThesisEvaluationPage";

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/cek-bansos" replace />} />
          <Route path="/cek-bansos" element={<PublicPortalPage />} />
          <Route path="/admin/login" element={<LoginPage />} />
          <Route path="/admin/dashboard" element={<ExecutiveDashboardPage />} />
          <Route path="/admin/criteria" element={<CriteriaManagementPage />} />
          <Route path="/admin/citizens" element={<SurveyorInputPage />} />
          <Route path="/admin/selection" element={<SawRankingPage />} />
          <Route path="/admin/xai" element={<XaiGeneratorPage />} />
          <Route path="/admin/berita-acara" element={<LurahApprovalPage />} />
          <Route path="/admin/evaluation" element={<ThesisEvaluationPage />} />
          <Route path="/admin/*" element={<ExecutiveDashboardPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
