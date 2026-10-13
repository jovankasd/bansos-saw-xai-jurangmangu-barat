import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AppShell } from "../components/layout/AppShell";
import { renderWithProviders } from "../test-utils";

describe("AppShell Responsive & RBAC Layout", () => {
  it("toggles mobile drawer via hamburger button and closes via backdrop", () => {
    renderWithProviders(
      <AppShell title="Dashboard Adjudikasi" breadcrumb={["Tata Kelola", "Tahap I 2026"]}>
        <div>Konten Adjudikasi</div>
      </AppShell>,
      { user: { name: "Budi Hartono, S.STP", role: "SUPER_ADMIN" } }
    );

    const drawer = screen.getByRole("navigation", { name: /menu utama/i });
    expect(drawer).toHaveAttribute("data-drawer-open", "false");

    const menuBtn = screen.getByRole("button", { name: /buka menu navigasi/i });
    fireEvent.click(menuBtn);
    expect(drawer).toHaveAttribute("data-drawer-open", "true");

    const closeBtn = screen.getByRole("button", { name: /tutup menu navigasi/i });
    fireEvent.click(closeBtn);
    expect(drawer).toHaveAttribute("data-drawer-open", "false");
  });

  it("enforces RBAC: hides mutation actions from Viewer (Lurah) and displays approval menu", () => {
    renderWithProviders(
      <AppShell title="Pengesahan Batch" breadcrumb={["Tata Kelola", "Tahap I 2026"]}>
        <div>Konten Pengesahan</div>
      </AppShell>,
      { user: { name: "H. Ahmad Syarif, M.Si", role: "VIEWER" } }
    );

    // Lurah must NOT see batch execution mutation button
    expect(screen.queryByRole("button", { name: /Eksekusi Batch SAW/i })).toBeNull();
    // Lurah must NOT see weight configuration mutation menu
    expect(screen.queryByRole("link", { name: /Konfigurasi Bobot SAW/i })).toBeNull();

    // Lurah should see Read-Only & Approval Menus
    expect(screen.getByRole("link", { name: /Dashboard Adjudikasi/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Pengesahan Berita Acara/i })).toBeInTheDocument();
    expect(screen.getByText(/H. Ahmad Syarif, M.Si/i)).toBeInTheDocument();
    expect(screen.getByText("Lurah Jurangmangu Barat")).toBeInTheDocument();
    expect(screen.getByText("Lurah")).toBeInTheDocument();
  });

  it("enforces RBAC: allows Super Admin to see all governance modules including SAW execution and weight config", () => {
    renderWithProviders(
      <AppShell title="Manajemen Kriteria" breadcrumb={["Pengaturan", "Kriteria"]}>
        <div>Konten Kriteria</div>
      </AppShell>,
      { user: { name: "Budi Hartono, S.STP", role: "SUPER_ADMIN" } }
    );

    expect(screen.getByRole("button", { name: /Eksekusi Batch SAW/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Konfigurasi Bobot SAW/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Evaluasi Skripsi/i })).toBeInTheDocument();
    expect(screen.getByText(/Kasi Kesos Kelurahan/i)).toBeInTheDocument();
  });

  it("enforces RBAC: scopes Surveyor (Ketua RT) strictly to RT operations", () => {
    renderWithProviders(
      <AppShell title="Entri Data Warga RT" breadcrumb={["Pendataan", "RT 003"]}>
        <div>Konten RT</div>
      </AppShell>,
      { user: { name: "Suryanto", role: "SURVEYOR", rt_number: "003" } }
    );

    expect(screen.queryByRole("button", { name: /Eksekusi Batch SAW/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /Konfigurasi Bobot SAW/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /Pengesahan Berita Acara/i })).toBeNull();
    expect(screen.getByRole("link", { name: /Data Warga RT/i })).toBeInTheDocument();
    // Verify both profile card and topbar badge display RT 003
    expect(screen.getAllByText(/Ketua RT 003/i)).toHaveLength(2);
  });
});
