import React, { useState } from "react";
import {
  FileCheck,
  Download,
  RotateCcw,
  Fingerprint,
  QrCode,
  CheckCircle2,
  Brain,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";
import { useAuth } from "../../context/AuthContext";

export const LurahApprovalPage: React.FC = () => {
  const { user } = useAuth();
  const [selectedCaseTab, setSelectedCaseTab] = useState<"top" | "cutoff" | "cadangan">("cutoff");
  const [isApproved, setIsApproved] = useState(false);
  const [showToast, setShowToast] = useState(false);

  // Case study data for XAI Spot-check
  const spotCheckCases = {
    top: {
      rank: 1,
      name: "Budi Santoso",
      nik: "367403******0012",
      rt: "RT 03/RW 02",
      vi: 0.942,
      status: "Lolos Kuota",
      c1: { val: 0.965, label: "Pendapatan: Rp 750rb/bln (Desil 1)", weight: 0.2895 },
      c2: { val: 0.920, label: "Tanggungan: 5 Jiwa", weight: 0.2300 },
      c3: { val: 0.950, label: "Rumah: Dinding Bambu/RTLH", weight: 0.2375 },
      c4: { val: 0.930, label: "Aset: Tanpa Kendaraan Bermotor", weight: 0.1860 },
      narrative:
        "Berdasarkan hasil musyawarah seleksi objektif Simple Additive Weighting Kelurahan Jurangmangu Barat, berkas Bapak Budi Santoso ditetapkan pada Peringkat #1 dari alokasi 50 KPM dengan skor preferensi 0.9420. Kondisi kerentanan ekonomi keluarga memenuhi seluruh kriteria batas bawah kemiskinan ekstrem di wilayah Kelurahan Jurangmangu Barat.",
    },
    cutoff: {
      rank: 50,
      name: "Rochmat H******",
      nik: "367403******0002",
      rt: "RT 07/RW 03",
      vi: 0.725,
      status: "Penerima Terakhir (Ambang Cutoff)",
      c1: { val: 0.745, label: "Pendapatan: Rp 1.100.000/bln (Desil 1)", weight: 0.2235 },
      c2: { val: 0.720, label: "Tanggungan: 4 Jiwa", weight: 0.1800 },
      c3: { val: 0.710, label: "Rumah: Semi Permanen", weight: 0.1775 },
      c4: { val: 0.720, label: "Aset: 1 Unit Sepeda Motor Tua", weight: 0.1440 },
      narrative:
        "Berdasarkan hasil komputasi SAW dan mekanisme deterministik Hierarchical Tie-Breaker Level 1 (r_C1), berkas Bapak Rochmat H****** ditetapkan pada Peringkat #50 (batas akhir kuota 50 KPM). Skor kembar V_i = 0.7250 berhasil dimenangkan karena tingkat pendapatan keluarga berada pada desil yang lebih rentan dibanding kandidat cadangan.",
    },
    cadangan: {
      rank: 51,
      name: "Sumiyati B******",
      nik: "367403******0003",
      rt: "RT 03/RW 02",
      vi: 0.725,
      status: "Cadangan 1 (Tidak Lolos Alokasi)",
      c1: { val: 0.715, label: "Pendapatan: Rp 1.450.000/bln (Desil 2)", weight: 0.2145 },
      c2: { val: 0.730, label: "Tanggungan: 4 Jiwa", weight: 0.1825 },
      c3: { val: 0.720, label: "Rumah: Semi Permanen", weight: 0.1800 },
      c4: { val: 0.740, label: "Aset: 1 Unit Sepeda Motor", weight: 0.1480 },
      narrative:
        "Berkas Ibu Sumiyati B****** memperoleh skor preferensi identik V_i = 0.7250 pada ambang kuota 50 KPM. Melalui aturan tie-breaker bertingkat kriteria C1 (Pendapatan), usulan ditempatkan sebagai Cadangan Prioritas #1. Apabila terdapat penerima kuota yang mengundurkan diri atau berhalangan tetap, alokasi akan otomatis dialihkan ke berkas ini.",
    },
  };

  const activeCase = spotCheckCases[selectedCaseTab];

  const handleApprove = () => {
    setIsApproved(true);
    setShowToast(true);
    setTimeout(() => setShowToast(false), 4000);
  };

  const handleDownloadPdf = () => {
    window.open("/api/selection/BANSOS-JB-2026-T1/berita-acara-pdf/", "_blank");
  };

  return (
    <AppShell
      title="Pengesahan Berita Acara & Penetapan Hasil"
      breadcrumb={["Tata Kelola", "Persetujuan Dokumen", "Batch 2026-T1"]}
    >
      <div className="space-y-6">
        {/* Governance Executive Header Banner */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                Sidang Pleno Kelurahan
              </span>
              <span className={`text-xs font-bold px-2.5 py-0.5 rounded border ${
                isApproved
                  ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                  : "bg-sky-50 text-sky-800 border-sky-300"
              }`}>
                {isApproved ? "Status: Disahkan & Diterbitkan (Published)" : "Status: Narrated (Siap Disahkan)"}
              </span>
              <span className="text-xs font-mono text-secondary">
                ID Batch: BANSOS-JB-2026-T1
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Pengesahan & Penerbitan Berita Acara Penetapan KPM Bansos
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Pejabat Berwenang: <span className="font-semibold text-primary">{user?.name || "H. Ahmad Syarif, M.Si (Lurah)"}</span>. Tinjau lembar rekapitulasi, lakukan uji petik narasi XAI, dan bubuhkan tanda tangan digital (TTE).
            </p>
          </div>

          {/* Unclipped Action Buttons Toolbar */}
          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => alert("Permintaan revisi dikirimkan kembali ke antrean Kasi Kesos.")}
              className="flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium bg-white hover:bg-rose-50 border border-rose-200 text-rose-800 rounded-lg transition-colors shadow-xs"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Minta Revisi ke Kasi Kesos</span>
            </button>

            <button
              onClick={handleDownloadPdf}
              className="flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium bg-white hover:bg-surface border border-border-subtle text-secondary hover:text-on-surface rounded-lg transition-colors shadow-xs"
            >
              <Download className="w-4 h-4" />
              <span>Unduh Draf PDF</span>
            </button>

            <button
              onClick={handleApprove}
              disabled={isApproved}
              className={`flex items-center gap-2 px-4 py-2 text-xs sm:text-sm font-bold rounded-lg transition-all shadow-xs ${
                isApproved
                  ? "bg-emerald-700 text-white cursor-default"
                  : "bg-primary hover:bg-primary-container text-white cursor-pointer active:scale-95"
              }`}
            >
              <Fingerprint className="w-4 h-4" />
              <span>
                {isApproved
                  ? "Telah Disahkan (TTE Aktif)"
                  : "Sahkan & Terbitkan Berita Acara (TTE)"}
              </span>
            </button>
          </div>
        </div>

        {/* Feedback Alert Toast */}
        {showToast && (
          <div className="p-4 rounded-xl bg-emerald-900 text-white flex items-center justify-between shadow-md">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="w-5 h-5 text-emerald-300 shrink-0" />
              <div className="text-xs sm:text-sm">
                <span className="font-bold block">Berita Acara Berhasil Disahkan & Diterbitkan!</span>
                <span className="text-emerald-200">
                  Status batch telah diperbarui menjadi Published. Warga kini dapat memverifikasi hasil secara mandiri di portal /cek-bansos.
                </span>
              </div>
            </div>
            <span className="font-mono text-xs text-emerald-300">TTE BSrE #JB-2026-9901</span>
          </div>
        )}

        {/* Main Two-Column Workbench: Document Preview (7 cols) vs XAI Spot-check (5 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Official Document A4 Preview (7 cols) */}
          <div className="lg:col-span-7 bg-white rounded-xl p-4 sm:p-6 border border-border-subtle shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-primary" />
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Pratinjau Berita Acara Resmi (Formulir BA-BANSOS-01)
                </h3>
              </div>
              <span className="text-xs font-mono bg-surface px-2 py-0.5 rounded text-secondary border border-border-subtle">
                A4 Resmi • Dokumen Terbuka
              </span>
            </div>

            {/* Authentic Parchment / White Document Container with overflow-x-auto */}
            <div className="overflow-x-auto custom-scroll">
              <div className="min-w-[560px] p-6 sm:p-8 bg-white border border-slate-300 rounded shadow-xs space-y-4 text-xs font-sans text-on-surface relative">
                {/* Official Municipal Letterhead (KOP SURAT) */}
                <div className="text-center pb-3 border-b-2 border-black space-y-0.5">
                  <h4 className="font-bold text-sm tracking-wider">
                    PEMERINTAH KOTA TANGERANG SELATAN
                  </h4>
                  <h5 className="font-bold text-xs tracking-wider">
                    KECAMATAN PONDOK AREN
                  </h5>
                  <h3 className="font-extrabold text-base text-primary tracking-wide">
                    KELURAHAN JURANGMANGU BARAT
                  </h3>
                  <p className="text-[10px] text-secondary font-mono">
                    Jl. Jurang Mangu Barat No. 1, Kec. Pondok Aren, Kota Tangerang Selatan, Banten 15223
                  </p>
                </div>

                {/* Document Title & Number */}
                <div className="text-center space-y-1 pt-2">
                  <h4 className="font-bold text-xs underline uppercase tracking-wide">
                    BERITA ACARA PENETAPAN KELUARGA PENERIMA MANFAAT (KPM)
                    <br />
                    BANTUAN SOSIAL SEMBAKO TAHAP I TAHUN ANGGARAN 2026
                  </h4>
                  <p className="font-mono text-[11px] text-secondary">
                    Nomor: 460/082-Kesos/JB/2026
                  </p>
                </div>

                {/* Considerans Plenary Text */}
                <p className="text-justify text-[11px] leading-relaxed text-slate-800">
                  Pada hari ini, <strong>Jumat</strong> tanggal <strong>Tiga Puluh</strong> bulan <strong>Januari</strong> tahun <strong>Dua Ribu Dua Puluh Enam</strong>, bertempat di Kantor Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, telah dilaksanakan Sidang Pleno Penetapan Akhir KPM Bantuan Sosial Sembako Tahap I Tahun Anggaran 2026 berdasarkan luaran komputasi Simple Additive Weighting (SAW) terbobot baku serta audit integritas naratif kecerdasan buatan.
                </p>

                {/* Summary Matrix Table Around Cutoff Boundary */}
                <div className="space-y-1.5 pt-1">
                  <div className="flex items-center justify-between text-[11px] font-mono">
                    <span className="font-bold text-primary">
                      REKAPITULASI PEMERINGKATAN & AMBANG BATAS CUT-OFF (KUOTA: 50 KPM)
                    </span>
                    <span className="text-secondary">Model Deterministik</span>
                  </div>

                  <table className="w-full text-left text-[11px] border border-slate-300">
                    <thead>
                      <tr className="bg-slate-100 font-mono text-secondary text-[10px] border-b border-slate-300">
                        <th className="p-1.5 text-center w-8">#</th>
                        <th className="p-1.5">Nama KPM</th>
                        <th className="p-1.5 text-center">RT/RW</th>
                        <th className="p-1.5 text-right">Skor V_i</th>
                        <th className="p-1.5 text-center">Status</th>
                        <th className="p-1.5">Catatan Tie-Breaker</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      <tr>
                        <td className="p-1.5 text-center font-mono font-bold">#48</td>
                        <td className="p-1.5 font-semibold">Nurhayati S******</td>
                        <td className="p-1.5 text-center font-mono">RT 04/RW 02</td>
                        <td className="p-1.5 text-right font-mono font-bold">0.7295</td>
                        <td className="p-1.5 text-center">
                          <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-900 font-bold text-[9px]">
                            Lolos Kuota
                          </span>
                        </td>
                        <td className="p-1.5 text-secondary text-[10px]">Lansia Tunggal Rentan</td>
                      </tr>
                      <tr>
                        <td className="p-1.5 text-center font-mono font-bold">#49</td>
                        <td className="p-1.5 font-semibold">Dedi Mulyana K******</td>
                        <td className="p-1.5 text-center font-mono">RT 02/RW 01</td>
                        <td className="p-1.5 text-right font-mono font-bold">0.7280</td>
                        <td className="p-1.5 text-center">
                          <span className="px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-900 font-bold text-[9px]">
                            Lolos Kuota
                          </span>
                        </td>
                        <td className="p-1.5 text-secondary text-[10px]">Tanggungan 4 Jiwa, Buruh Harian</td>
                      </tr>
                      <tr className="bg-emerald-50/70 font-semibold text-emerald-950">
                        <td className="p-1.5 text-center font-mono font-bold text-emerald-800">#50</td>
                        <td className="p-1.5 font-bold text-emerald-950">Rochmat H******</td>
                        <td className="p-1.5 text-center font-mono">RT 07/RW 03</td>
                        <td className="p-1.5 text-right font-mono font-bold text-emerald-800">0.7250</td>
                        <td className="p-1.5 text-center">
                          <span className="px-1.5 py-0.2 rounded bg-emerald-700 text-white font-bold text-[9px]">
                            Penerima Terakhir
                          </span>
                        </td>
                        <td className="p-1.5 text-emerald-800 text-[10px] font-medium">
                          Menang Tie-Break: C1 Pendapatan Terendah (Desil 1)
                        </td>
                      </tr>

                      {/* Explicit Cutoff Boundary Barrier */}
                      <tr className="bg-rose-600 text-white font-mono text-[9px] tracking-wider text-center">
                        <td colSpan={6} className="py-1 font-bold">
                          ⛔ AMBANG BATAS KUOTA 50 KPM (V_i ≥ 0.7250) • TIDAK DAPAT DILAMPAUI BERDASARKAN DPA KELURAHAN ⛔
                        </td>
                      </tr>

                      <tr className="bg-amber-50/50">
                        <td className="p-1.5 text-center font-mono text-secondary">#51</td>
                        <td className="p-1.5 font-medium text-amber-950">Sumiyati B******</td>
                        <td className="p-1.5 text-center font-mono">RT 03/RW 02</td>
                        <td className="p-1.5 text-right font-mono font-bold text-amber-900">0.7250</td>
                        <td className="p-1.5 text-center">
                          <span className="px-1.5 py-0.2 rounded bg-amber-200 text-amber-900 font-bold text-[9px]">
                            Cadangan 1
                          </span>
                        </td>
                        <td className="p-1.5 text-amber-800 text-[10px]">
                          Kalah Tie-Break C1 (Desil 2), Status Antrean Utama
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                {/* Disqualification TMS Appendix Snippet */}
                <div className="space-y-1 pt-1">
                  <span className="font-bold text-primary text-[10px] block">
                    LAMPIRAN TIDAK MEMENUHI SYARAT (TMS - 6 KPM):
                  </span>
                  <div className="bg-slate-50 p-2 rounded border border-slate-200 text-[10px] flex flex-wrap gap-2 text-rose-800 font-medium">
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">1. Bambang S. (Anggota TNI Aktif)</span>
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">2. Ratna W. (Duplikasi PKH Kemensos)</span>
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">3. Hendra T. (Pindah Domisili Luar Tangsel)</span>
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">4. Supardi (Meninggal Dunia Tanpa Ahli Waris)</span>
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">5. Eni K. (Kepemilikan Mobil Pribadi)</span>
                    <span className="bg-white border border-rose-200 px-1.5 py-0.5 rounded">6. Agus B. (Terdaftar ASN Aktif)</span>
                  </div>
                </div>

                {/* Digital Integrity & QR Code Stamp */}
                <div className="p-2.5 bg-emerald-50/60 border border-emerald-200 rounded flex items-center justify-between text-[10px]">
                  <div className="flex items-center gap-2.5">
                    <div className="w-10 h-10 bg-white border border-slate-300 rounded flex items-center justify-center p-1 text-primary">
                      <QrCode className="w-8 h-8" />
                    </div>
                    <div className="space-y-0.5">
                      <span className="font-bold text-emerald-950 block">
                        Verifikasi Publik Keabsahan Dokumen Digital
                      </span>
                      <p className="font-mono text-[9px] text-secondary">
                        Digest SHA-256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
                      </p>
                      <p className="text-[9px] text-emerald-800">
                        Kepatuhan UU No. 27/2022 (PDP): Seluruh NIK & PII disamarkan secara sah.
                      </p>
                    </div>
                  </div>
                  <span className="bg-emerald-700 text-white font-mono text-[8px] px-2 py-0.5 rounded uppercase font-bold shrink-0">
                    BSrE BSSN SEALED
                  </span>
                </div>

                {/* Dual Signature Block */}
                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-slate-300 text-center text-[10px]">
                  {/* Left: Kasi Kesos */}
                  <div className="space-y-1 flex flex-col items-center">
                    <span>Disusun & Diverifikasi oleh,</span>
                    <span className="font-semibold text-secondary">Kasi Kesejahteraan Sosial</span>
                    <div className="my-1 px-2.5 py-1 bg-emerald-50 border border-emerald-300 rounded text-emerald-800 font-mono text-[9px] font-bold">
                      ✓ TERVERIFIKASI TTE
                    </div>
                    <div className="font-bold text-on-surface underline">BUDI HARTONO, S.Sos</div>
                    <div className="text-[9px] font-mono text-secondary">NIP. 19820415 200801 1 008</div>
                  </div>

                  {/* Right: Lurah */}
                  <div className="space-y-1 flex flex-col items-center">
                    <span>Mengetahui & Mengesahkan,</span>
                    <span className="font-semibold text-primary">Lurah Jurangmangu Barat</span>
                    {isApproved ? (
                      <div className="my-1 px-2.5 py-1 bg-emerald-50 border border-emerald-300 rounded text-emerald-800 font-mono text-[9px] font-bold">
                        ✓ DISAHKAN TTE (BSrE)
                      </div>
                    ) : (
                      <div className="my-1 px-2.5 py-1 bg-amber-50 border border-dashed border-amber-400 rounded text-amber-800 font-mono text-[9px] font-semibold">
                        MENUNGGU OTORISASI TTE
                      </div>
                    )}
                    <div className="font-bold text-on-surface underline">H. AHMAD SYARIF, M.Si</div>
                    <div className="text-[9px] font-mono text-secondary">NIP. 19740912 199903 1 004</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Uji Petik Narasi XAI (5 cols) */}
          <div className="lg:col-span-5 bg-white rounded-xl p-4 sm:p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="border-b border-border-subtle pb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Brain className="w-5 h-5 text-primary" />
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Uji Petik Transparansi Narasi XAI
                </h3>
              </div>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Gemini 2.5 Flash
              </span>
            </div>

            {/* Interactive Tab Selector Buttons */}
            <div className="grid grid-cols-3 gap-1.5 bg-surface p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setSelectedCaseTab("top")}
                className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                  selectedCaseTab === "top"
                    ? "bg-white text-primary shadow-xs border border-border-subtle"
                    : "text-secondary hover:text-on-surface"
                }`}
              >
                Rank #1 (Top)
              </button>

              <button
                type="button"
                onClick={() => setSelectedCaseTab("cutoff")}
                className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                  selectedCaseTab === "cutoff"
                    ? "bg-emerald-900 text-white shadow-xs"
                    : "text-secondary hover:text-on-surface"
                }`}
              >
                Rank #50 (Cutoff)
              </button>

              <button
                type="button"
                onClick={() => setSelectedCaseTab("cadangan")}
                className={`py-1.5 px-2 rounded text-xs font-semibold transition-all ${
                  selectedCaseTab === "cadangan"
                    ? "bg-amber-600 text-white shadow-xs"
                    : "text-secondary hover:text-on-surface"
                }`}
              >
                Rank #51 (Cadangan)
              </button>
            </div>

            {/* Active Sample Dossier View */}
            <div className="p-4 bg-surface rounded-xl border border-border-subtle space-y-3 text-xs">
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] font-mono text-secondary uppercase block">
                    Studi Kasus Adjudikasi
                  </span>
                  <h4 className="font-bold text-on-surface text-sm">
                    {activeCase.name} (Rank #{activeCase.rank})
                  </h4>
                  <span className="font-mono text-xs text-primary font-bold">
                    Skor V_i: {activeCase.vi.toFixed(4)} • {activeCase.rt}
                  </span>
                </div>
                <span className="px-2 py-0.5 rounded bg-white text-on-surface border text-[10px] font-bold font-mono">
                  {activeCase.status}
                </span>
              </div>

              {/* Criteria Attribution Decomposition Micro-bars */}
              <div className="space-y-2 pt-1">
                <span className="text-[11px] font-mono uppercase text-secondary font-semibold block">
                  Dekomposisi Pembobotan Kriteria:
                </span>

                <div className="space-y-0.5">
                  <div className="flex justify-between font-mono text-[11px]">
                    <span>C1: {activeCase.c1.label}</span>
                    <span className="font-bold text-emerald-800">w: {activeCase.c1.weight.toFixed(4)}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-900 h-full rounded-full"
                      style={{ width: `${activeCase.c1.val * 100}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-0.5">
                  <div className="flex justify-between font-mono text-[11px]">
                    <span>C2: {activeCase.c2.label}</span>
                    <span className="font-bold text-sky-800">w: {activeCase.c2.weight.toFixed(4)}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-sky-600 h-full rounded-full"
                      style={{ width: `${activeCase.c2.val * 100}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-0.5">
                  <div className="flex justify-between font-mono text-[11px]">
                    <span>C3: {activeCase.c3.label}</span>
                    <span className="font-bold text-teal-800">w: {activeCase.c3.weight.toFixed(4)}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-teal-600 h-full rounded-full"
                      style={{ width: `${activeCase.c3.val * 100}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-0.5">
                  <div className="flex justify-between font-mono text-[11px]">
                    <span>C4: {activeCase.c4.label}</span>
                    <span className="font-bold text-slate-800">w: {activeCase.c4.weight.toFixed(4)}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-slate-700 h-full rounded-full"
                      style={{ width: `${activeCase.c4.val * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Generated AI Explanation Narrative Box */}
              <div className="p-3.5 bg-emerald-950 text-white rounded-lg space-y-1">
                <span className="text-[10px] font-mono uppercase text-emerald-300 font-bold block">
                  Narasi Transparansi Keputusan (Bahasa Indonesia):
                </span>
                <p className="text-xs text-emerald-50 leading-relaxed">
                  "{activeCase.narrative}"
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default LurahApprovalPage;
