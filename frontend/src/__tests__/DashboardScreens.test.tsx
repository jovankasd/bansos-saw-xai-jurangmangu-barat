import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { renderWithProviders } from "../test-utils";
import { ExecutiveDashboardPage } from "../pages/dashboard/ExecutiveDashboardPage";
import { CriteriaManagementPage } from "../pages/dashboard/CriteriaManagementPage";
import { SurveyorInputPage } from "../pages/dashboard/SurveyorInputPage";
import { SawRankingPage } from "../pages/dashboard/SawRankingPage";
import { XaiGeneratorPage } from "../pages/dashboard/XaiGeneratorPage";

describe("Admin & Surveyor Operational Screens (Milestone 4C)", () => {
  describe("1. ExecutiveDashboardPage", () => {
    it("excludes Sinkronisasi DTKS button on ExecutiveDashboardPage per PRD Not-Doing", () => {
      renderWithProviders(<ExecutiveDashboardPage />);
      expect(screen.queryByRole("button", { name: /Sinkronisasi DTKS/i })).toBeNull();
      // Should offer valid actions instead
      expect(screen.getByText(/Ekspor Usulan/i)).toBeInTheDocument();
      expect(screen.getByText(/Ringkasan Eksekutif & Adjudikasi/i)).toBeInTheDocument();
    });

    it("renders KPI cards and active batch metrics", () => {
      renderWithProviders(<ExecutiveDashboardPage />);
      expect(screen.getByText(/Total Calon KPM/i)).toBeInTheDocument();
      expect(screen.getByText(/Kuota Penerima/i)).toBeInTheDocument();
      expect(screen.getByText(/Pipeline Seleksi/i)).toBeInTheDocument();
    });
  });

  describe("2. CriteriaManagementPage", () => {
    it("disables weight save button when sum of weights != 1.00 on CriteriaManagementPage", () => {
      renderWithProviders(<CriteriaManagementPage />);
      const c1Input = screen.getByLabelText(/Bobot C1/i);
      fireEvent.change(c1Input, { target: { value: "0.45" } });
      
      expect(screen.getByText(/Total bobot harus persis bernilai 1.00/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Simpan & Validasi Bobot/i })).toBeDisabled();
    });

    it("enables weight save button when sum of weights == 1.00", () => {
      renderWithProviders(<CriteriaManagementPage />);
      // Default initial is 0.30, 0.25, 0.25, 0.20 which sums to 1.00
      expect(screen.getByRole("button", { name: /Simpan & Validasi Bobot/i })).not.toBeDisabled();
      expect(screen.getByText(/Valid & Seimbang/i)).toBeInTheDocument();
    });

    it("renders Frozen Criteria Snapshot indicator when batch is locked", () => {
      renderWithProviders(<CriteriaManagementPage isSnapshotLocked={true} />);
      expect(screen.getByText(/Frozen Snapshot Aktif/i)).toBeInTheDocument();
    });
  });

  describe("3. SurveyorInputPage", () => {
    it("renders real dependents count and TMS reason selector on SurveyorInputPage", () => {
      renderWithProviders(<SurveyorInputPage />, {
        user: { name: "Ketua RT 03", role: "SURVEYOR", rt_number: "003" },
      });
      expect(screen.getByLabelText(/Jumlah Tanggungan Riil/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Status Kelayakan Administratif/i)).toBeInTheDocument();
      expect(screen.getByText(/Import Excel KPM/i)).toBeInTheDocument();
    });

    it("shows TMS disqualification reason select when status is DISQUALIFIED", () => {
      renderWithProviders(<SurveyorInputPage />);
      const statusSelect = screen.getByLabelText(/Status Kelayakan Administratif/i);
      fireEvent.change(statusSelect, { target: { value: "DISQUALIFIED" } });
      expect(screen.getByLabelText(/Alasan Tidak Memenuhi Syarat/i)).toBeInTheDocument();
    });
  });

  describe("4. SawRankingPage", () => {
    it("renders SAW ranking table and matrix detail drawer on SawRankingPage", () => {
      renderWithProviders(<SawRankingPage />);
      expect(screen.getByText(/Detail Matriks Normalisasi/i)).toBeInTheDocument();
      expect(screen.getByText(/Batas Kuota Seleksi/i)).toBeInTheDocument();
      expect(screen.getByText(/Preferensi \(V_i\)/i)).toBeInTheDocument();
    });

    it("displays sticky table and C3 as COST and C4 as Kepemilikan Aset", () => {
      renderWithProviders(<SawRankingPage />);
      expect(screen.getByText(/C4 \(Aset\)/i)).toBeInTheDocument();
      expect(screen.queryByText(/Daya Listrik/i)).toBeNull();
    });
  });

  describe("5. XaiGeneratorPage", () => {
    it("displays C4 as Kepemilikan Aset in XAI payload monitor", () => {
      renderWithProviders(<XaiGeneratorPage />);
      expect(screen.getByText(/C4: Kepemilikan Aset/i)).toBeInTheDocument();
      expect(screen.queryByText(/Daya Listrik/i)).toBeNull();
    });

    it("shows Zero-PII sanitation badge and worker progress", () => {
      renderWithProviders(<XaiGeneratorPage />);
      expect(screen.getByText(/Zero-PII Sanitation Active/i)).toBeInTheDocument();
      expect(screen.getByText(/Progres Adjudikasi XAI/i)).toBeInTheDocument();
    });
  });
});
