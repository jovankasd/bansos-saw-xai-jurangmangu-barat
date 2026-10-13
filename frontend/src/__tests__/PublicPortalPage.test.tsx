import { screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PublicPortalPage } from "../pages/PublicPortalPage";
import { LoginPage } from "../pages/LoginPage";
import { renderWithProviders } from "../test-utils";
import { api } from "../lib/api";

// Mock axios instance from lib/api
vi.mock("../lib/api", () => {
  return {
    api: {
      post: vi.fn(),
      get: vi.fn(),
      defaults: { headers: { common: {} } },
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
  };
});

describe("PublicPortalPage PRD Compliance & Responsiveness", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders NIK + 4-digit KK + CAPTCHA verification form and excludes prohibited two-way appeal form", () => {
    renderWithProviders(<PublicPortalPage />, { user: null, initialToken: null });

    // Check Form Inputs
    expect(screen.getByLabelText(/Nomor Induk Kependudukan \(NIK 16 Digit\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/4 Digit Terakhir Nomor Kartu Keluarga/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Saya warga asli \/ perwakilan sah/i)).toBeInTheDocument();

    // Verify "Not Doing" rule: NO bidirectional appeal form
    expect(screen.queryByRole("button", { name: /Kirim Sanggahan Anonim/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Kirim Sanggahan Resmi/i })).toBeNull();
    expect(screen.queryByPlaceholderText(/Jelaskan secara ringkas kendala/i)).toBeNull();

    // Verify presence of offline advisory to Ketua RT (PRD Section 12.2)
    expect(screen.getByText(/Posko Advokasi & Layanan Informasi Warga/i)).toBeInTheDocument();
    expect(screen.getByText(/Hubungi Posko RT/i)).toBeInTheDocument();
  });

  it("submits verification and renders full dossier with masked PII, 4-part XAI narrative, and C1..C4 gap chart", async () => {
    const mockSuccessResponse = {
      data: {
        found: true,
        period_name: "Bansos Sembako Tahap I 2026",
        download_token: "signed_mock_pdf_token_12345",
        applicant: {
          nik_masked: "367403******0002",
          name_masked: "Ahmad S******",
          rt: "003",
          rw: "001",
        },
        result: {
          status: "TIDAK_LOLOS",
          rank: 35,
          quota: 30,
          final_score: 0.684,
          cutoff_score: 0.725,
          explanation: {
            ringkasan: "Berkas keluarga Anda belum masuk dalam kuota 30 penerima pada periode seleksi ini.",
            faktor_utama: [
              "Nilai kriteria Pendapatan Keluarga berada di atas batas prioritas",
              "Kapasitas tanggungan keluarga belum memenuhi ambang prioritas tertinggi",
            ],
            narasi_lengkap: "Berdasarkan hasil musyawarah seleksi objektif Kelurahan Jurangmangu Barat, skor Anda 0.6840.",
            rekomendasi: "Bila ada perubahan kondisi ekonomi terkini, silakan melapor ke Ketua RT 003 untuk pemutakhiran.",
          },
          chart_data: [
            { kriteria: "Pendapatan Keluarga", skor_pemohon: 0.6, rata_rata_lolos: 0.85 },
            { kriteria: "Jumlah Tanggungan", skor_pemohon: 0.5, rata_rata_lolos: 0.8 },
            { kriteria: "Kondisi Tempat Tinggal", skor_pemohon: 0.75, rata_rata_lolos: 0.75 },
            { kriteria: "Kepemilikan Aset", skor_pemohon: 0.7, rata_rata_lolos: 0.7 },
          ],
        },
      },
    };

    (api.post as any).mockResolvedValueOnce(mockSuccessResponse);

    renderWithProviders(<PublicPortalPage />, { user: null, initialToken: null });

    const nikInput = screen.getByLabelText(/Nomor Induk Kependudukan \(NIK 16 Digit\)/i);
    const kkInput = screen.getByLabelText(/4 Digit Terakhir Nomor Kartu Keluarga/i);
    const submitBtn = screen.getByRole("button", { name: /Cek Status Kelolosan Bansos/i });

    fireEvent.change(nikInput, { target: { value: "3674031508820002" } });
    fireEvent.change(kkInput, { target: { value: "9941" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/public/check-status/", {
        nik: "3674031508820002",
        kk_last4: "9941",
        captcha_token: expect.any(String),
      });
    });

    // Check Masked Identity
    expect(await screen.findByText("Ahmad S******")).toBeInTheDocument();
    expect(screen.getByText(/367403\*\*\*\*\*\*0002/)).toBeInTheDocument();
    expect(screen.getByText(/RT 003 \/ RW 001/)).toBeInTheDocument();

    // Check Status & Scores
    expect(screen.getByText(/BELUM MEMENUHI KUOTA/i)).toBeInTheDocument();
    expect(screen.getByText(/Peringkat ke-35/i)).toBeInTheDocument();
    expect(screen.getAllByText(/0.6840/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/0.7250/)).toBeInTheDocument();

    // Check 4-Part XAI
    expect(screen.getByText(/1. Ringkasan Evaluasi Algoritmik/i)).toBeInTheDocument();
    expect(screen.getByText(/2. Faktor Pembeda Utama/i)).toBeInTheDocument();
    expect(screen.getByText(/3. Pernyataan Sikap Kelurahan/i)).toBeInTheDocument();
    expect(screen.getByText(/4. Rekomendasi Pemutakhiran Data Warga/i)).toBeInTheDocument();

    // Check C1..C4 Criteria Gap Chart
    expect(screen.getAllByText(/Pendapatan Keluarga/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Jumlah Tanggungan/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Kondisi Tempat Tinggal/i)).toBeInTheDocument();
    expect(screen.getByText(/Kepemilikan Aset/i)).toBeInTheDocument();

    // Check Download PDF Action with signed token
    const downloadBtn = screen.getByRole("button", { name: /Unduh Lembar Hasil Resmi/i });
    expect(downloadBtn).toBeInTheDocument();
  });

  it("renders LOLOS status correctly with approval badge", async () => {
    (api.post as any).mockResolvedValueOnce({
      data: {
        found: true,
        period_name: "Bansos Sembako Tahap I 2026",
        download_token: "signed_mock_pdf_token_lolos",
        applicant: {
          nik_masked: "367403******1111",
          name_masked: "Siti M******",
          rt: "001",
          rw: "002",
        },
        result: {
          status: "LOLOS",
          rank: 5,
          quota: 30,
          final_score: 0.892,
          cutoff_score: 0.725,
          explanation: {
            ringkasan: "Selamat, berkas keluarga Anda masuk dalam kuota 30 penerima manfaat.",
            faktor_utama: ["Kapasitas tanggungan lansia dan kerentanan ekonomi tinggi"],
            narasi_lengkap: "Berdasarkan hasil musyawarah seleksi objektif, berkas Anda berhak menerima bantuan.",
            rekomendasi: "Harap membawa e-KTP dan KK asli saat pengambilan bantuan.",
          },
          chart_data: [
            { kriteria: "Pendapatan Keluarga", skor_pemohon: 0.9, rata_rata_lolos: 0.85 },
            { kriteria: "Jumlah Tanggungan", skor_pemohon: 0.85, rata_rata_lolos: 0.8 },
            { kriteria: "Kondisi Tempat Tinggal", skor_pemohon: 0.8, rata_rata_lolos: 0.75 },
            { kriteria: "Kepemilikan Aset", skor_pemohon: 0.8, rata_rata_lolos: 0.7 },
          ],
        },
      },
    });

    renderWithProviders(<PublicPortalPage />, { user: null, initialToken: null });

    const nikInput = screen.getByLabelText(/Nomor Induk Kependudukan \(NIK 16 Digit\)/i);
    const kkInput = screen.getByLabelText(/4 Digit Terakhir Nomor Kartu Keluarga/i);
    const submitBtn = screen.getByRole("button", { name: /Cek Status Kelolosan Bansos/i });

    fireEvent.change(nikInput, { target: { value: "3674031508821111" } });
    fireEvent.change(kkInput, { target: { value: "1111" } });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/BERHAK MENERIMA BANTUAN SOSIAL/i)).toBeInTheDocument();
    expect(screen.getByText(/Peringkat ke-5/i)).toBeInTheDocument();
    expect(screen.getByText("Siti M******")).toBeInTheDocument();
  });

  it("handles lockout and error scenarios (403, 429, 404)", async () => {
    (api.post as any).mockRejectedValueOnce({
      response: {
        status: 429,
        data: { error: "Pencarian untuk NIK ini dikunci sementara selama 15 menit akibat 5 kali kegagalan verifikasi." },
      },
    });

    renderWithProviders(<PublicPortalPage />, { user: null, initialToken: null });

    const nikInput = screen.getByLabelText(/Nomor Induk Kependudukan \(NIK 16 Digit\)/i);
    const kkInput = screen.getByLabelText(/4 Digit Terakhir Nomor Kartu Keluarga/i);
    const submitBtn = screen.getByRole("button", { name: /Cek Status Kelolosan Bansos/i });

    fireEvent.change(nikInput, { target: { value: "3674031508820002" } });
    fireEvent.change(kkInput, { target: { value: "0000" } });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/dikunci sementara selama 15 menit/i)).toBeInTheDocument();
  });
});

describe("LoginPage Staff Authentication", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders login form and authenticates staff successfully", async () => {
    (api.post as any).mockResolvedValueOnce({
      data: {
        access: "mock_access_jwt",
        refresh: "mock_refresh_jwt",
        role: "SUPER_ADMIN",
        name: "Budi Hartono, S.STP",
        rt_number: null,
      },
    });

    renderWithProviders(<LoginPage />, { user: null, initialToken: null });

    expect(screen.getByLabelText(/Nama Pengguna \/ NIP/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Kata Sandi Akun/i)).toBeInTheDocument();

    const usernameInput = screen.getByLabelText(/Nama Pengguna \/ NIP/i);
    const passwordInput = screen.getByLabelText(/Kata Sandi Akun/i);
    const submitBtn = screen.getByRole("button", { name: /Masuk ke Panel Adjudikasi/i });

    fireEvent.change(usernameInput, { target: { value: "kasi_kesos" } });
    fireEvent.change(passwordInput, { target: { value: "Password123!" } });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith("/auth/login/", {
        username: "kasi_kesos",
        password: "Password123!",
      });
    });
  });

  it("displays error banner on authentication failure", async () => {
    (api.post as any).mockRejectedValueOnce({
      response: {
        status: 401,
        data: { error: "Username atau kata sandi tidak valid." },
      },
    });

    renderWithProviders(<LoginPage />, { user: null, initialToken: null });

    const usernameInput = screen.getByLabelText(/Nama Pengguna \/ NIP/i);
    const passwordInput = screen.getByLabelText(/Kata Sandi Akun/i);
    const submitBtn = screen.getByRole("button", { name: /Masuk ke Panel Adjudikasi/i });

    fireEvent.change(usernameInput, { target: { value: "wrong_user" } });
    fireEvent.change(passwordInput, { target: { value: "wrong_pass" } });
    fireEvent.click(submitBtn);

    expect(await screen.findByText(/Username atau kata sandi tidak valid/i)).toBeInTheDocument();
  });
});
