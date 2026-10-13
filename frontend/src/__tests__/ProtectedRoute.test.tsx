import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "../context/AuthContext";
import { ProtectedRoute } from "../components/auth/ProtectedRoute";
import { User } from "../types/auth";

describe("ProtectedRoute Security & RBAC Guards", () => {
  const renderWithAuth = (
    initialPath: string,
    user: User | null,
    token: string | null = user ? "fake_access_token" : null
  ) => {
    return render(
      <AuthProvider initialUser={user} initialToken={token}>
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/admin/login" element={<div>Halaman Login Staf</div>} />
            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "VIEWER"]}>
                  <div>Dashboard Eksekutif</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/criteria"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN"]}>
                  <div>Manajemen Kriteria Bobot</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/citizens"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "SURVEYOR"]}>
                  <div>Portal Surveyor Input RT</div>
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin/berita-acara"
              element={
                <ProtectedRoute allowedRoles={["SUPER_ADMIN", "VIEWER"]}>
                  <div>Pengesahan Berita Acara Lurah</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );
  };

  it("redirects unauthenticated visitor to /admin/login when accessing protected route", () => {
    renderWithAuth("/admin/dashboard", null, null);
    expect(screen.getByText("Halaman Login Staf")).toBeInTheDocument();
    expect(screen.queryByText("Dashboard Eksekutif")).not.toBeInTheDocument();
  });

  it("permits SUPER_ADMIN to access admin criteria management", () => {
    const adminUser: User = { name: "Kasi Kesos", role: "SUPER_ADMIN" };
    renderWithAuth("/admin/criteria", adminUser);
    expect(screen.getByText("Manajemen Kriteria Bobot")).toBeInTheDocument();
  });

  it("redirects SURVEYOR attempting to access criteria management to /admin/citizens", () => {
    const surveyorUser: User = { name: "Ketua RT 03", role: "SURVEYOR", rt_number: "03" };
    renderWithAuth("/admin/criteria", surveyorUser);
    expect(screen.getByText("Portal Surveyor Input RT")).toBeInTheDocument();
    expect(screen.queryByText("Manajemen Kriteria Bobot")).not.toBeInTheDocument();
  });

  it("redirects VIEWER (Lurah) attempting to access criteria management to /admin/berita-acara", () => {
    const lurahUser: User = { name: "Lurah Jubar", role: "VIEWER" };
    renderWithAuth("/admin/criteria", lurahUser);
    expect(screen.getByText("Pengesahan Berita Acara Lurah")).toBeInTheDocument();
    expect(screen.queryByText("Manajemen Kriteria Bobot")).not.toBeInTheDocument();
  });

  it("permits VIEWER (Lurah) to access Berita Acara pengesahan", () => {
    const lurahUser: User = { name: "Lurah Jubar", role: "VIEWER" };
    renderWithAuth("/admin/berita-acara", lurahUser);
    expect(screen.getByText("Pengesahan Berita Acara Lurah")).toBeInTheDocument();
  });
});
