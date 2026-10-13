import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { renderWithProviders } from "../test-utils";
import { LurahApprovalPage } from "../pages/dashboard/LurahApprovalPage";
import { ThesisEvaluationPage } from "../pages/dashboard/ThesisEvaluationPage";

describe("Lurah Approval & Thesis Evaluation Pages (Milestone 5 & 6 UI)", () => {
  describe("1. LurahApprovalPage", () => {
    it("renders Berita Acara preview, XAI spot-check tabs, and unclipped approval action for Viewer", () => {
      renderWithProviders(<LurahApprovalPage />, {
        user: { name: "H. Ahmad Syarif", role: "VIEWER" },
      });
      expect(screen.getByText(/Pratinjau Berita Acara Resmi/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Sahkan & Terbitkan/i })).toBeInTheDocument();
      // Lurah as Viewer should not see technical execution buttons
      expect(screen.queryByText(/Eksekusi Batch SAW/i)).toBeNull();
    });

    it("renders municipal letterhead, cutoff table, TMS appendix, and QR verification stamp", () => {
      renderWithProviders(<LurahApprovalPage />);
      expect(screen.getByText(/PEMERINTAH KOTA TANGERANG SELATAN/i)).toBeInTheDocument();
      expect(screen.getAllByText(/KELURAHAN JURANGMANGU BARAT/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/Nomor: 460\/082-Kesos\/JB\/2026/i)).toBeInTheDocument();
      expect(screen.getByText(/AMBANG BATAS KUOTA 50 KPM/i)).toBeInTheDocument();
      expect(screen.getByText(/TIDAK MEMENUHI SYARAT \(TMS/i)).toBeInTheDocument();
      expect(screen.getByText(/Verifikasi Publik Keabsahan Dokumen/i)).toBeInTheDocument();
    });

    it("switches XAI spot-check tabs between Top, Cutoff, and Cadangan cases", () => {
      renderWithProviders(<LurahApprovalPage />);
      expect(screen.getByText(/Uji Petik Transparansi Narasi XAI/i)).toBeInTheDocument();

      const topTab = screen.getByRole("button", { name: /Rank #1 \(Top\)/i });
      fireEvent.click(topTab);
      expect(screen.getAllByText(/Budi Santoso/i).length).toBeGreaterThan(0);

      const cutoffTab = screen.getByRole("button", { name: /Rank #50 \(Cutoff\)/i });
      fireEvent.click(cutoffTab);
      expect(screen.getAllByText(/Rochmat H/i).length).toBeGreaterThan(0);

      const cadanganTab = screen.getByRole("button", { name: /Rank #51 \(Cadangan\)/i });
      fireEvent.click(cadanganTab);
      expect(screen.getAllByText(/Sumiyati B/i).length).toBeGreaterThan(0);
    });

    it("allows Lurah to sign and approve Berita Acara with feedback toast", () => {
      renderWithProviders(<LurahApprovalPage />, {
        user: { name: "H. Ahmad Syarif", role: "VIEWER" },
      });
      const approveBtn = screen.getByRole("button", { name: /Sahkan & Terbitkan/i });
      fireEvent.click(approveBtn);
      expect(screen.getByText(/Berita Acara Berhasil Disahkan/i)).toBeInTheDocument();
    });
  });

  describe("2. ThesisEvaluationPage", () => {
    it("renders Fidelity Score, Hallucination Rate, and SUS evaluation cards", () => {
      renderWithProviders(<ThesisEvaluationPage />);
      expect(screen.getAllByText(/Fidelity Score/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Hallucination Rate/i).length).toBeGreaterThan(0);
      expect(screen.getByText(/System Usability Scale \(SUS\)/i)).toBeInTheDocument();
    });

    it("displays SAW accuracy white-box test and stress test metrics", () => {
      renderWithProviders(<ThesisEvaluationPage />);
      expect(screen.getByText(/Akurasi White-Box SAW/i)).toBeInTheDocument();
      expect(screen.getByText(/100.0% Cocok Sempurna/i)).toBeInTheDocument();
      expect(screen.getAllByText(/Uji Ketahanan Asinkron/i).length).toBeGreaterThan(0);
    });

    it("renders SUS 10-item standard questionnaire table and Excel dataset export button", () => {
      renderWithProviders(<ThesisEvaluationPage />);
      expect(screen.getByText(/Rekapitulasi 10 Butir Instrumen SUS/i)).toBeInTheDocument();
      expect(screen.getByText(/Ekspor Dataset Evaluasi Skripsi/i)).toBeInTheDocument();
    });
  });
});
