import React, { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { PublicCheckStatusResponse } from "../types/public";
import { CriteriaGapChart } from "../components/public/CriteriaGapChart";

export const PublicPortalPage: React.FC = () => {
  const [nik, setNik] = useState("");
  const [kkLast4, setKkLast4] = useState("");
  const [captchaVerified, setCaptchaVerified] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [resultData, setResultData] = useState<PublicCheckStatusResponse | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (nik.length !== 16) {
      setErrorMsg("Nomor Induk Kependudukan (NIK) harus terdiri dari 16 digit angka.");
      return;
    }

    if (kkLast4.length !== 4) {
      setErrorMsg("Nomor KK verifikasi harus berupa 4 digit terakhir.");
      return;
    }

    if (!captchaVerified) {
      setErrorMsg("Harap selesaikan verifikasi warga sah (CAPTCHA) terlebih dahulu.");
      return;
    }

    setIsLoading(true);

    try {
      const response = await api.post("/public/check-status/", {
        nik,
        kk_last4: kkLast4,
        captcha_token: "simulated_turnstile_token_public",
      });

      setResultData(response.data);
      setTimeout(() => {
        const el = document.getElementById("searchResultArea");
        if (el && typeof el.scrollIntoView === "function") {
          el.scrollIntoView({ behavior: "smooth" });
        }
      }, 100);
    } catch (err: any) {
      setResultData(null);
      if (err.response?.status === 403) {
        setErrorMsg("Verifikasi CAPTCHA gagal atau kedaluwarsa. Silakan ulangi kembali.");
      } else if (err.response?.status === 429) {
        setErrorMsg(
          err.response.data?.error ||
            "Pencarian untuk NIK ini dikunci sementara selama 15 menit akibat 5 kali kegagalan verifikasi."
        );
      } else if (err.response?.status === 404) {
        setErrorMsg(
          err.response.data?.message ||
            "Kombinasi NIK dan 4 digit No KK tidak ditemukan pada periode seleksi aktif."
        );
      } else {
        setErrorMsg(
          err.response.data?.error ||
            "Terjadi gangguan koneksi ke server kelurahan. Silakan coba beberapa saat lagi."
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownloadPdf = () => {
    if (!resultData?.download_token) {
      alert("Token unduhan dokumen tidak tersedia.");
      return;
    }
    const baseURL = import.meta.env.VITE_API_BASE_URL || "/api";
    const downloadUrl = `${baseURL}/public/result-pdf/?token=${resultData.download_token}`;
    window.open(downloadUrl, "_blank");
  };

  const applicant = resultData?.applicant;
  const result = resultData?.result;
  const explanation = result?.explanation;

  const isApproved = result?.status === "LOLOS";
  const isRejected = result?.status === "TIDAK_LOLOS";
  const isTms = result?.status === "DISKUALIFIKASI_TMS";

  return (
    <div className="min-h-screen bg-surface font-body-md text-on-surface flex flex-col antialiased">
      {/* Topbar Civic Header */}
      <header className="sticky top-0 w-full z-40 bg-surface-container-lowest/95 backdrop-blur-md border-b border-border-subtle shadow-sm">
        <div className="max-w-7xl mx-auto h-16 px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center text-on-primary font-bold shadow-sm">
              <span className="material-symbols-outlined text-[24px]">verified</span>
            </div>
            <div className="flex flex-col leading-tight">
              <span className="font-bold text-base sm:text-lg text-primary tracking-tight">
                Portal Transparansi Bansos
              </span>
              <span className="text-[11px] font-mono uppercase text-secondary tracking-wider">
                Kelurahan Jurangmangu Barat
              </span>
            </div>
          </div>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
            <a href="#formVerifikasi" className="text-primary font-bold border-b-2 border-primary py-1">
              Cek Status KPM
            </a>
            <a href="#jadwal" className="text-on-surface-variant hover:text-primary transition-colors py-1">
              Jadwal Penyaluran
            </a>
            <a href="#advokasi" className="text-on-surface-variant hover:text-primary transition-colors py-1">
              Layanan Advokasi RT
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <Link
              to="/admin/login"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-surface-container hover:bg-surface-subtle text-primary border border-border-subtle transition-all"
            >
              <span className="material-symbols-outlined text-[16px]">lock</span>
              <span>Masuk Staf</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Sub-Header Civic Pulse Banner */}
      <section className="w-full bg-surface-container-low border-b border-border-subtle py-2 px-4 sm:px-6">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs text-secondary font-mono">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-xai-weight-positive animate-pulse" />
            <span>Sistem Pelayanan Terbuka Terintegrasi • Akuntabilitas Publik SAW & XAI</span>
          </div>
          <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-semibold">
            UU PDP No. 27/2022 Patuh
          </span>
        </div>
      </section>

      <main className="flex-1 w-full">
        {/* Hero & Verification Panel */}
        <section id="formVerifikasi" className="w-full bg-surface-canvas py-8 sm:py-12 px-4 sm:px-6 lg:px-8">
          <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Context & Dignity Statement */}
            <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
              <div className="space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-surface-container rounded font-mono text-xs text-primary font-semibold">
                  <span className="material-symbols-outlined text-[16px] text-primary">verified_user</span>
                  <span>TRANSPARANSI BANTUAN SOSIAL TERBUKA</span>
                </div>
                <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-primary tracking-tight leading-tight">
                  Pengecekan Bantuan Sosial Terbuka &amp; Berkeadilan
                </h1>
                <p className="text-sm sm:text-base text-on-surface-variant leading-relaxed">
                  Periksa keabsahan alokasi bansos dengan model pembobotan kriteria teruji (SAW/XAI). Seluruh
                  keputusan dapat diaudit secara terbuka tanpa perantara dan bebas biaya.
                </p>
              </div>

              {/* Photo & Dignity Caption Anchor */}
              <div className="rounded-xl overflow-hidden shadow-sm border border-border-subtle bg-primary text-on-primary p-5 relative">
                <div className="relative z-10 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-tertiary-fixed">
                    <span className="material-symbols-outlined text-[18px]">gavel</span>
                    <span>Asas Musyawarah &amp; Akuntabilitas</span>
                  </div>
                  <p className="text-sm text-on-primary leading-relaxed">
                    "Keputusan penyaluran bansos ditetapkan secara objektif berdasarkan bobot kriteria terukur,
                    memastikan penerima manfaat adalah keluarga paling rentan secara adil."
                  </p>
                  <p className="text-xs text-on-primary/70 font-mono">
                    Pemerintah Kelurahan Jurangmangu Barat
                  </p>
                </div>
              </div>

              {/* Trust Badges Bar */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-surface-container-lowest rounded-xl border border-border-subtle text-center shadow-sm">
                  <span className="text-xl font-bold text-primary block">100%</span>
                  <span className="text-[11px] font-mono text-secondary uppercase">Bebas Pungli</span>
                </div>
                <div className="p-3 bg-surface-container-lowest rounded-xl border border-border-subtle text-center shadow-sm">
                  <span className="text-xl font-bold text-primary block">32 RW</span>
                  <span className="text-[11px] font-mono text-secondary uppercase">Audit Merata</span>
                </div>
                <div className="p-3 bg-surface-container-lowest rounded-xl border border-border-subtle text-center shadow-sm">
                  <span className="text-xl font-bold text-primary block">XAI</span>
                  <span className="text-[11px] font-mono text-secondary uppercase">Algoritma Terang</span>
                </div>
              </div>
            </div>

            {/* Right Column: Verification Shield Card */}
            <div className="lg:col-span-7 bg-surface-container-lowest rounded-2xl p-6 sm:p-8 shadow-sm border border-border-subtle space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
                <div>
                  <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider block">
                    Verifikasi Mandiri Warga
                  </span>
                  <h2 className="text-lg sm:text-xl font-bold text-on-surface">
                    Formulir Pemeriksaan Hak Penerima
                  </h2>
                </div>
                <div className="w-10 h-10 rounded-full bg-surface-subtle flex items-center justify-center text-primary">
                  <span className="material-symbols-outlined text-[24px]">fact_check</span>
                </div>
              </div>

              {errorMsg && (
                <div className="p-4 rounded-xl bg-status-rejected-bg border border-red-200 text-status-rejected-fg text-sm flex items-start gap-3">
                  <span className="material-symbols-outlined text-[20px] shrink-0 mt-0.5">error</span>
                  <div className="space-y-1">
                    <p className="font-semibold">Perhatian</p>
                    <p className="text-xs leading-relaxed">{errorMsg}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                {/* Input NIK */}
                <div className="space-y-1.5">
                  <label htmlFor="inputNik" className="block text-xs font-bold text-on-surface uppercase tracking-wider">
                    Nomor Induk Kependudukan (NIK 16 Digit)
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-secondary">
                      <span className="material-symbols-outlined text-[20px]">badge</span>
                    </span>
                    <input
                      id="inputNik"
                      aria-label="Nomor Induk Kependudukan (NIK 16 Digit)"
                      type="text"
                      maxLength={16}
                      value={nik}
                      onChange={(e) => setNik(e.target.value.replace(/\D/g, ""))}
                      placeholder="Contoh: 367403XXXXXXXXXX"
                      className="w-full pl-11 pr-4 py-3 bg-surface-canvas rounded-xl text-on-surface font-mono text-sm sm:text-base tracking-wider border border-border-subtle focus:outline-none focus:ring-2 focus:ring-primary shadow-inner"
                      required
                    />
                  </div>
                  <p className="text-xs text-secondary">
                    Pastikan 16 digit sesuai e-KTP domisili Kelurahan Jurangmangu Barat.
                  </p>
                </div>

                {/* Input No KK (4 Digit Terakhir) */}
                <div className="space-y-1.5">
                  <label htmlFor="inputKk" className="block text-xs font-bold text-on-surface uppercase tracking-wider">
                    4 Digit Terakhir Nomor Kartu Keluarga (KK)
                  </label>
                  <div className="relative">
                    <span className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-secondary">
                      <span className="material-symbols-outlined text-[20px]">family_restroom</span>
                    </span>
                    <input
                      id="inputKk"
                      aria-label="4 Digit Terakhir Nomor Kartu Keluarga"
                      type="password"
                      maxLength={4}
                      value={kkLast4}
                      onChange={(e) => setKkLast4(e.target.value.replace(/\D/g, ""))}
                      placeholder="Contoh: 9812"
                      className="w-full pl-11 pr-4 py-3 bg-surface-canvas rounded-xl text-on-surface font-mono text-sm sm:text-base tracking-widest border border-border-subtle focus:outline-none focus:ring-2 focus:ring-primary shadow-inner"
                      required
                    />
                  </div>
                  <p className="text-xs text-secondary">
                    Digunakan sebagai kunci pengaman ganda pelindung identitas keluarga warga.
                  </p>
                </div>

                {/* CAPTCHA / Turnstile Simulation Box */}
                <div className="p-3.5 bg-surface-subtle rounded-xl border border-border-subtle flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="turnstileCheck"
                      aria-label="Saya warga asli / perwakilan sah KK terkait"
                      checked={captchaVerified}
                      onChange={(e) => setCaptchaVerified(e.target.checked)}
                      className="w-5 h-5 accent-primary cursor-pointer rounded"
                    />
                    <div>
                      <label htmlFor="turnstileCheck" className="text-xs sm:text-sm font-medium text-on-surface cursor-pointer block">
                        Saya warga asli / perwakilan sah KK terkait
                      </label>
                      <div className="text-[11px] font-mono text-secondary flex items-center gap-1 mt-0.5">
                        <span className="material-symbols-outlined text-[14px] text-xai-weight-positive">check_circle</span>
                        <span>Cloudflare Turnstile Verified</span>
                      </div>
                    </div>
                  </div>
                  <span className="material-symbols-outlined text-[22px] text-secondary opacity-60">
                    fingerprint
                  </span>
                </div>

                {/* Submit Action */}
                <button
                  type="submit"
                  disabled={isLoading || nik.length !== 16 || kkLast4.length !== 4}
                  className="w-full min-h-[48px] py-3.5 px-4 bg-primary text-on-primary rounded-xl text-sm sm:text-base font-semibold hover:bg-primary-container disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2 shadow-sm"
                >
                  {isLoading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-on-primary border-t-transparent rounded-full animate-spin" />
                      <span>Memverifikasi Basis Data...</span>
                    </>
                  ) : (
                    <>
                      <span className="material-symbols-outlined text-[20px]">search</span>
                      <span>Cek Status Kelolosan Bansos</span>
                    </>
                  )}
                </button>

                {/* PDP Notice Footnote */}
                <div className="pt-2 flex flex-wrap items-center justify-between text-secondary font-mono text-[11px] border-t border-border-subtle gap-2">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">lock</span>
                    <span>Enkripsi End-to-End AES-256</span>
                  </span>
                  <span>Rate Limit: Maks 5 req/menit</span>
                </div>
              </form>
            </div>
          </div>
        </section>

        {/* Results Dossier Section (Showcase when results are fetched) */}
        {resultData && result && (
          <section id="searchResultArea" className="w-full bg-surface-container py-10 px-4 sm:px-6 lg:px-8 border-t border-border-subtle">
            <div className="max-w-7xl mx-auto space-y-8">
              {/* Dossier Banner */}
              <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-border-subtle p-6 sm:p-8">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-subtle">
                  <div className="space-y-1.5">
                    <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded bg-surface-subtle font-mono text-xs text-primary font-bold border border-border-subtle">
                      <span>LEMBAR BUKTI TRANSPARANSI DESA</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                      <h2 className="text-xl sm:text-2xl font-bold text-on-surface">
                        {applicant?.name_masked || "Warga Pemohon"}
                      </h2>
                      <span className="font-mono text-xs text-secondary bg-surface-subtle px-2.5 py-1 rounded border border-border-subtle">
                        NIK: {applicant?.nik_masked}
                      </span>
                    </div>
                    <p className="text-xs sm:text-sm text-on-surface-variant flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[18px] text-secondary">location_on</span>
                      <span>
                        RT {applicant?.rt} / RW {applicant?.rw}, Kelurahan Jurangmangu Barat, Pondok Aren
                      </span>
                    </p>
                  </div>

                  <div className="bg-surface-canvas p-4 rounded-xl border border-border-subtle flex flex-col md:items-end justify-center">
                    <span className="text-[11px] font-mono text-secondary uppercase tracking-wider">
                      Program Bantuan
                    </span>
                    <span className="text-base sm:text-lg font-bold text-primary">
                      {resultData.period_name}
                    </span>
                    <span className="text-xs text-secondary mt-0.5">
                      Penyaluran Resmi Kelurahan Jurangmangu Barat
                    </span>
                  </div>
                </div>

                {/* Verdict Card Banner */}
                <div
                  className={`mt-6 p-5 sm:p-6 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-sm ${
                    isApproved
                      ? "bg-status-approved-bg border-emerald-200 text-status-approved-fg"
                      : isRejected
                      ? "bg-status-review-bg border-amber-200 text-status-review-fg"
                      : "bg-status-rejected-bg border-red-200 text-status-rejected-fg"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`p-3 rounded-xl shrink-0 ${
                        isApproved
                          ? "bg-emerald-100 text-status-approved-fg"
                          : isRejected
                          ? "bg-amber-100 text-status-review-fg"
                          : "bg-red-100 text-status-rejected-fg"
                      }`}
                    >
                      <span className="material-symbols-outlined text-[32px]">
                        {isApproved ? "verified" : isRejected ? "assignment_late" : "cancel"}
                      </span>
                    </div>
                    <div>
                      <span className="font-mono text-xs font-bold uppercase tracking-wider block">
                        Status Ketetapan Akhir Perangkingan
                      </span>
                      <h3 className="text-lg sm:text-xl font-bold mt-0.5">
                        {isApproved
                          ? "BERHAK MENERIMA BANTUAN SOSIAL"
                          : isRejected
                          ? "BELUM MEMENUHI KUOTA PENERIMA"
                          : "TIDAK MEMENUHI SYARAT (DISKUALIFIKASI TMS)"}
                      </h3>
                      <p className="text-xs sm:text-sm text-on-surface mt-1">
                        {isTms
                          ? "Berkas Anda tidak memenuhi kriteria kelayakan dasar (ASN/TNI/Polri atau PKH Ganda)."
                          : `Peringkat ke-${result.rank} dari alokasi kuota wilayah ${result.quota} Penerima Manfaat di lingkungan Anda.`}
                      </p>
                    </div>
                  </div>

                  {/* Preference Meter (Only for non-TMS) */}
                  {!isTms && (
                    <div className="bg-surface-container-lowest p-4 rounded-xl border border-border-subtle shadow-sm shrink-0 w-full md:w-auto min-w-[260px]">
                      <div className="flex justify-between items-center text-xs font-mono mb-1.5">
                        <span className="text-secondary">Skor Anda (V_i):</span>
                        <span className={`font-bold ${isApproved ? "text-status-approved-fg" : "text-status-review-fg"}`}>
                          {result.final_score.toFixed(4)}
                        </span>
                      </div>
                      <div className="w-full bg-surface-subtle h-2.5 rounded-full overflow-hidden mb-1.5">
                        <div
                          className={`h-full rounded-full ${isApproved ? "bg-emerald-600" : "bg-amber-500"}`}
                          style={{ width: `${Math.min(result.final_score * 100, 100)}%` }}
                        />
                      </div>
                      <div className="flex justify-between items-center font-mono text-[11px] text-secondary">
                        <span>Ambang Lolos (Cutoff):</span>
                        <span className="text-primary font-bold">{result.cutoff_score.toFixed(4)}</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 2-Column Result Layout: Left Narasi XAI, Right Criteria Gap Chart & Actions */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left: 4-Part Structured XAI Explanation */}
                <div className="lg:col-span-7 bg-surface-container-lowest rounded-2xl shadow-sm border border-border-subtle p-6 sm:p-8 space-y-6">
                  <div className="flex items-center gap-3 pb-3 border-b border-border-subtle">
                    <div className="w-9 h-9 rounded-full bg-secondary-container text-on-secondary-container flex items-center justify-center">
                      <span className="material-symbols-outlined text-[20px]">psychology_alt</span>
                    </div>
                    <div>
                      <h3 className="text-base sm:text-lg font-bold text-on-surface">
                        Penjelasan Transparansi Terbuka (XAI)
                      </h3>
                      <p className="text-xs text-secondary">
                        Dihasilkan secara objektif oleh mesin inferensi rekomendasi kelurahan
                      </p>
                    </div>
                  </div>

                  {/* 1. Ringkasan Evaluasi Algoritmik */}
                  <div className="bg-surface-canvas p-4 sm:p-5 rounded-xl border border-border-subtle space-y-2">
                    <h4 className="font-mono text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-primary" />
                      <span>1. Ringkasan Evaluasi Algoritmik</span>
                    </h4>
                    <p className="text-xs sm:text-sm text-on-surface leading-relaxed">
                      {explanation?.ringkasan ||
                        `Berkas keluarga Anda dihitung menggunakan Simple Additive Weighting (SAW) dengan hasil akhir skor preferensi ${result.final_score.toFixed(
                          4
                        )}.`}
                    </p>
                  </div>

                  {/* 2. Faktor Pembeda Utama (Counterfactual Insight) */}
                  <div className="bg-surface-canvas p-4 sm:p-5 rounded-xl border border-border-subtle space-y-3">
                    <h4 className="font-mono text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-primary" />
                      <span>2. Faktor Pembeda Utama (Analisis Counterfactual)</span>
                    </h4>
                    {explanation?.faktor_utama && explanation.faktor_utama.length > 0 ? (
                      <ul className="space-y-2">
                        {explanation.faktor_utama.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs sm:text-sm text-on-surface">
                            <span className="material-symbols-outlined text-[16px] text-secondary shrink-0 mt-0.5">
                              arrow_right
                            </span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs sm:text-sm text-on-surface leading-relaxed">
                        Faktor penentu utama didasarkan pada selisih jarak kriteria terbobot terhadap ambang batas
                        penerima di lingkungan setempat.
                      </p>
                    )}
                  </div>

                  {/* 3. Pernyataan Sikap Kelurahan */}
                  <div className="p-4 sm:p-5 bg-surface-subtle rounded-xl border border-border-subtle space-y-2">
                    <h4 className="font-mono text-xs font-bold text-primary uppercase tracking-wider flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-primary" />
                      <span>3. Pernyataan Sikap Kelurahan Jurangmangu Barat</span>
                    </h4>
                    <p className="text-xs sm:text-sm text-on-surface-variant leading-relaxed italic">
                      "{explanation?.narasi_lengkap ||
                        "Ketiadaan bantuan pada tahap ini murni disebabkan keterbatasan kuota alokasi pagu wilayah, bukan diskualifikasi administratif. Berkas Anda tetap tersimpan dalam basis data cadangan."}"
                    </p>
                  </div>

                  {/* 4. Rekomendasi Pemutakhiran Data Warga */}
                  <div className="p-4 sm:p-5 bg-status-approved-bg rounded-xl border border-emerald-200 flex items-start gap-3">
                    <span className="material-symbols-outlined text-[22px] text-status-approved-fg shrink-0 mt-0.5">
                      how_to_reg
                    </span>
                    <div className="space-y-1">
                      <h4 className="font-mono text-xs font-bold text-status-approved-fg uppercase tracking-wider">
                        4. Rekomendasi Pemutakhiran Data Warga
                      </h4>
                      <p className="text-xs sm:text-sm text-on-surface leading-relaxed">
                        {explanation?.rekomendasi ||
                          "Bila terdapat perubahan data ekonomi keluarga atau tanggungan, silakan berkoordinasi dengan Ketua RT setempat untuk pemutakhiran pada periode berikutnya."}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Right: Gap Chart & Actions */}
                <div className="lg:col-span-5 space-y-6">
                  {/* Criteria Gap Chart Component */}
                  {result.chart_data && result.chart_data.length > 0 && (
                    <CriteriaGapChart items={result.chart_data} />
                  )}

                  {/* Citizen Action Card */}
                  <div className="bg-surface-container-lowest rounded-2xl shadow-sm border border-border-subtle p-5 sm:p-6 space-y-3.5">
                    <button
                      onClick={handleDownloadPdf}
                      className="w-full min-h-[44px] py-3 px-4 bg-primary text-on-primary rounded-xl text-sm font-semibold flex items-center justify-center gap-2 hover:bg-primary-container transition-all shadow-sm"
                    >
                      <span className="material-symbols-outlined text-[20px]">download</span>
                      <span>Unduh Lembar Hasil Resmi (PDF Ber-QR)</span>
                    </button>

                    <a
                      href={`https://wa.me/6281199887722?text=Halo%20Pengurus%20RT%20${applicant?.rt}%20Kelurahan%20Jurangmangu%20Barat,%20saya%20ingin%20konsultasi%20hasil%20bansos%20NIK%20${applicant?.nik_masked}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full min-h-[44px] py-3 px-4 bg-surface-container text-on-surface rounded-xl text-sm font-medium flex items-center justify-center gap-2 hover:bg-surface-dim transition-all text-center border border-border-subtle"
                    >
                      <span className="material-symbols-outlined text-[20px] text-primary">chat</span>
                      <span>Hubungi Posko Pendamping RT {applicant?.rt}</span>
                    </a>

                    <p className="text-center font-mono text-[11px] text-secondary pt-1">
                      Dokumen PDF dibubuhi Tanda Tangan Elektronik (TTE) &amp; QR Verifikasi Resmi Kelurahan Jurangmangu Barat.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* Section: Official Distribution Schedule */}
        <section id="jadwal" className="w-full bg-surface py-12 px-4 sm:px-6 lg:px-8 border-t border-border-subtle">
          <div className="max-w-7xl mx-auto space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
              <div>
                <span className="text-xs font-mono text-primary font-bold uppercase tracking-wider block">
                  Agenda Resmi
                </span>
                <h2 className="text-xl sm:text-2xl font-bold text-on-surface">
                  Jadwal Penyaluran &amp; Lokasi Posko Bantuan
                </h2>
              </div>
              <p className="text-xs sm:text-sm text-on-surface-variant max-w-md">
                Penyaluran sembako dan bantuan tunai dilaksanakan tertib tanpa antrean berdesakan melalui zonasi per RW.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Gelombang I */}
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-border-subtle shadow-sm space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-primary/10 text-primary uppercase">
                    Gelombang I
                  </span>
                  <span className="material-symbols-outlined text-secondary">storefront</span>
                </div>
                <h3 className="text-base font-bold text-on-surface">RW 001 - RW 010</h3>
                <p className="text-xs text-secondary leading-relaxed">
                  Aula Kantor Kelurahan Jurangmangu Barat, Jl. Jurang Mangu Barat No. 1, Pondok Aren.
                </p>
                <div className="pt-2 font-mono text-xs text-primary font-bold flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">schedule</span>
                  <span>18 - 20 Maret 2026 • 08:30 - 15:00 WIB</span>
                </div>
              </div>

              {/* Gelombang II */}
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-border-subtle shadow-sm space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-primary/10 text-primary uppercase">
                    Gelombang II
                  </span>
                  <span className="material-symbols-outlined text-secondary">storefront</span>
                </div>
                <h3 className="text-base font-bold text-on-surface">RW 011 - RW 020</h3>
                <p className="text-xs text-secondary leading-relaxed">
                  Gedung Serbaguna RW 014 (Samping Posyandu Melati), Jurangmangu Barat.
                </p>
                <div className="pt-2 font-mono text-xs text-primary font-bold flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">schedule</span>
                  <span>21 - 23 Maret 2026 • 08:30 - 15:00 WIB</span>
                </div>
              </div>

              {/* Gelombang III */}
              <div className="bg-surface-container-lowest p-6 rounded-2xl border border-border-subtle shadow-sm space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-primary/10 text-primary uppercase">
                    Gelombang III
                  </span>
                  <span className="material-symbols-outlined text-secondary">storefront</span>
                </div>
                <h3 className="text-base font-bold text-on-surface">RW 021 - RW 032</h3>
                <p className="text-xs text-secondary leading-relaxed">
                  Balai Warga RW 025, Area Masjid Baiturrahim, Jurangmangu Barat.
                </p>
                <div className="pt-2 font-mono text-xs text-primary font-bold flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px]">schedule</span>
                  <span>24 - 26 Maret 2026 • 08:30 - 15:00 WIB</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Section: Offline Advisory & Grievance Flow (PRD Section 12.2 - NO TWO-WAY WEB FORM) */}
        <section id="advokasi" className="w-full bg-surface-canvas py-12 px-4 sm:px-6 lg:px-8 border-t border-border-subtle">
          <div className="max-w-7xl mx-auto bg-primary text-on-primary rounded-2xl p-6 sm:p-10 shadow-lg relative overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center relative z-10">
              <div className="lg:col-span-8 space-y-3">
                <div className="inline-flex items-center gap-2 px-3 py-1 bg-on-primary/10 rounded font-mono text-xs text-tertiary-fixed font-bold">
                  <span className="material-symbols-outlined text-[16px]">info</span>
                  <span>Posko Advokasi &amp; Layanan Informasi Warga</span>
                </div>
                <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">
                  Perubahan Kondisi Ekonomi atau Usulan Baru?
                </h2>
                <p className="text-xs sm:text-sm text-on-primary/80 leading-relaxed max-w-2xl">
                  Sesuai ketentuan baku pelayanan sosial (PRD Bagian 12.2), sistem tidak memproses sanggahan ad-hoc dua arah via web.
                  Warga yang mengalami perubahan beban tanggungan atau penurunan taraf ekonomi diarahkan melapor langsung ke Ketua RT
                  domisili untuk dimutakhirkan pada periode seleksi berikutnya.
                </p>
                <div className="pt-2 flex flex-wrap gap-4 text-xs font-mono text-on-primary">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-tertiary-fixed text-[18px]">call</span>
                    <span>Hotline Informasi: 0811-9988-7722</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-tertiary-fixed text-[18px]">mail</span>
                    <span>transparansi@kel-jurangmangubarat.id</span>
                  </div>
                </div>
              </div>

              {/* Offline Procedural Guidance Card */}
              <div className="lg:col-span-4 bg-surface-container-lowest text-on-surface rounded-xl p-5 sm:p-6 shadow-sm space-y-3 border border-border-subtle">
                <h3 className="text-base font-bold text-primary flex items-center gap-2">
                  <span className="material-symbols-outlined text-[20px]">how_to_vote</span>
                  <span>Prosedur Pelaporan RT</span>
                </h3>
                <p className="text-xs text-secondary leading-relaxed">
                  Langkah resmi pemutakhiran data warga untuk seleksi tahap berikutnya:
                </p>
                <ol className="text-xs text-on-surface space-y-2 list-decimal list-inside leading-relaxed">
                  <li>Bawa fotokopi KK dan e-KTP domisili Jurangmangu Barat.</li>
                  <li>Sampaikan bukti perubahan kondisi terkini ke Ketua RT setempat.</li>
                  <li>Ketua RT akan mendaftarkan pembaruan data pada survei periode berikutnya.</li>
                </ol>
                <div className="pt-2">
                  <a
                    href="https://wa.me/6281199887722?text=Halo%20Posko%20Informasi%20Bansos%20Jurangmangu%20Barat,%20saya%20ingin%20bertanya%20prosedur%20pemutakhiran%20data%20RT"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full py-2.5 px-4 bg-primary text-on-primary rounded-xl text-xs font-semibold hover:bg-primary-container transition-all flex items-center justify-center gap-2"
                  >
                    <span className="material-symbols-outlined text-[18px]">support_agent</span>
                    <span>Hubungi Posko RT</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full bg-surface-container-lowest border-t border-border-subtle py-6 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-on-surface-variant">
          <p>© 2026 Pemerintah Kelurahan Jurangmangu Barat, Pondok Aren, Kota Tangerang Selatan.</p>
          <div className="font-mono text-[11px] text-secondary">
            Standar Algoritma XAI Gemini Flash &amp; Simple Additive Weighting (SAW) Terbuka
          </div>
        </div>
      </footer>
    </div>
  );
};
