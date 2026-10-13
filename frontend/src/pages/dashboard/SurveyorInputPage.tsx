import React, { useState } from "react";
import {
  UserPlus,
  UploadCloud,
  FileSpreadsheet,
  CheckCircle2,
  Save,
  Download,
  ShieldAlert,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";
import { useAuth } from "../../context/AuthContext";

interface CandidateRecord {
  id: string;
  name: string;
  nik: string;
  dependents: number;
  status: "ELIGIBLE" | "DISQUALIFIED" | string;
  scoreEst?: number;
  disqualificationReason?: string;
}

export const SurveyorInputPage: React.FC = () => {
  const { user } = useAuth();
  const currentRt = user?.rt_number || "003";

  // Form State
  const [formData, setFormData] = useState({
    nik: "",
    noKk: "",
    name: "",
    phoneNumber: "",
    address: `Jl. Menjangan RT ${currentRt}/RW 02`,
    realDependentsCount: 4,
    c1Crips: "3", // Crips 1-4 for income
    c2Crips: "3", // Crips 1-4 for dependents
    c3Crips: "2", // Crips 1-3 for housing
    c4Crips: "3", // Crips 1-4 for assets
    eligibilityStatus: "ELIGIBLE" as "ELIGIBLE" | "DISQUALIFIED",
    disqualificationReason: "ASN",
  });

  const [importStatus, setImportStatus] = useState<string | null>(null);
  const [submissionSuccess, setSubmissionSuccess] = useState(false);

  // Mock list of recorded candidates in current RT
  const [recordedList, setRecordedList] = useState<CandidateRecord[]>([
    {
      id: "KPM-RT03-01",
      name: "Budi Santoso",
      nik: "367403******0012",
      dependents: 4,
      status: "ELIGIBLE",
      scoreEst: 0.942,
    },
    {
      id: "KPM-RT03-02",
      name: "Siti Rahmawati",
      nik: "367403******4419",
      dependents: 3,
      status: "ELIGIBLE",
      scoreEst: 0.884,
    },
    {
      id: "KPM-RT03-03",
      name: "Hendra Wijaya",
      nik: "367403******9910",
      dependents: 2,
      status: "DISQUALIFIED",
      disqualificationReason: "ASN / TNI / POLRI",
    },
  ]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newEntry = {
      id: `KPM-RT${currentRt}-${recordedList.length + 1}`,
      name: formData.name || "Calon KPM Baru",
      nik: formData.nik ? `${formData.nik.slice(0, 6)}******${formData.nik.slice(12)}` : "367403******0099",
      dependents: Number(formData.realDependentsCount),
      status: formData.eligibilityStatus,
      disqualificationReason:
        formData.eligibilityStatus === "DISQUALIFIED"
          ? formData.disqualificationReason
          : undefined,
      scoreEst: formData.eligibilityStatus === "ELIGIBLE" ? 0.75 : 0,
    };

    setRecordedList([newEntry, ...recordedList]);
    setSubmissionSuccess(true);
    setTimeout(() => setSubmissionSuccess(false), 3500);

    // Reset form
    setFormData({
      ...formData,
      nik: "",
      noKk: "",
      name: "",
      phoneNumber: "",
      realDependentsCount: 3,
      eligibilityStatus: "ELIGIBLE",
    });
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setImportStatus(`Mengunggah "${file.name}"... Berhasil memproses 18 data usulan.`);
      setTimeout(() => setImportStatus(null), 4000);
    }
  };

  return (
    <AppShell
      title="Pendataan Lapangan KPM & Import RT"
      breadcrumb={["Surveyor Lapangan", `Wilayah RT ${currentRt}`, "Input Data KPM"]}
    >
      <div className="space-y-6">
        {/* Header & Sub-header Context */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                Portal RT {currentRt}
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                Tahap Pengumpulan (Collecting)
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Pengusulan Calon KPM & Verifikasi TMS Lapangan
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Ketua RT bertugas mendaftarkan keluarga rentan, mengisi jumlah tanggungan riil, dan menandai warga TMS sejak pintu gerbang awal.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="/templates/template_usulan_kpm.xlsx"
              download
              className="flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium bg-white hover:bg-surface border border-border-subtle rounded-lg text-secondary transition-colors"
            >
              <Download className="w-4 h-4" />
              <span>Format Excel (.xlsx)</span>
            </a>
          </div>
        </div>

        {/* Bulk Import Zone */}
        <div className="bg-white rounded-xl p-5 border border-dashed border-primary/30 shadow-xs space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-primary" />
              <h3 className="font-bold text-on-surface text-sm sm:text-base">
                Import Excel KPM Massal
              </h3>
            </div>
            <span className="text-xs font-mono text-secondary">POST /api/citizens/import-excel/</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200">
            <div className="p-3 rounded-full bg-emerald-50 text-emerald-800 shrink-0">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div className="flex-1 text-center sm:text-left space-y-1">
              <span className="text-xs sm:text-sm font-semibold text-on-surface block">
                Unggah File Spreadsheet Rekap RT (.xlsx / .csv)
              </span>
              <span className="text-xs text-secondary block">
                Sistem otomatis memetakan kolom NIK, No KK, Pendapatan, Tanggungan, dan menyaring duplikasi.
              </span>
            </div>
            <label className="px-4 py-2 bg-primary hover:bg-primary-container text-white text-xs sm:text-sm font-semibold rounded-lg cursor-pointer transition-colors shadow-xs shrink-0">
              <span>Pilih Berkas Excel</span>
              <input
                type="file"
                accept=".xlsx,.xls,.csv"
                className="hidden"
                onChange={handleFileUpload}
              />
            </label>
          </div>

          {importStatus && (
            <div className="text-xs font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 p-2.5 rounded-lg flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{importStatus}</span>
            </div>
          )}
        </div>

        {/* Master Form Grid: Single Entry Form (7 cols) vs Recorded List (5 cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Single Entry Form */}
          <div className="lg:col-span-7 bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="border-b border-border-subtle pb-3">
              <h3 className="text-base font-bold text-on-surface flex items-center gap-2">
                <UserPlus className="w-4 h-4 text-primary" />
                Form Input Mandiri Calon KPM
              </h3>
              <p className="text-xs text-secondary mt-0.5">
                Masukkan berkas hasil verifikasi door-to-door dengan akurat.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs sm:text-sm">
              {/* Identity Fields */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label htmlFor="nik-input" className="font-semibold text-on-surface text-xs block">
                    16 Digit NIK Kepala Keluarga *
                  </label>
                  <input
                    id="nik-input"
                    type="text"
                    required
                    maxLength={16}
                    placeholder="Contoh: 3674031201850001"
                    value={formData.nik}
                    onChange={(e) => setFormData({ ...formData, nik: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1">
                  <label htmlFor="kk-input" className="font-semibold text-on-surface text-xs block">
                    16 Digit Nomor Kartu Keluarga (KK) *
                  </label>
                  <input
                    id="kk-input"
                    type="text"
                    required
                    maxLength={16}
                    placeholder="Contoh: 3674031201080005"
                    value={formData.noKk}
                    onChange={(e) => setFormData({ ...formData, noKk: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label htmlFor="name-input" className="font-semibold text-on-surface text-xs block">
                    Nama Lengkap Kepala Keluarga *
                  </label>
                  <input
                    id="name-input"
                    type="text"
                    required
                    placeholder="Sesuai KTP"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div className="space-y-1">
                  <label htmlFor="phone-input" className="font-semibold text-on-surface text-xs block">
                    Nomor WhatsApp / HP
                  </label>
                  <input
                    id="phone-input"
                    type="tel"
                    placeholder="0812xxxxxxxx"
                    value={formData.phoneNumber}
                    onChange={(e) => setFormData({ ...formData, phoneNumber: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>
              </div>

              {/* CRITICAL PRD FIELD: real_dependents_count */}
              <div className="p-3 bg-sky-50 rounded-lg border border-sky-200 space-y-1.5">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="real-dependents-count"
                    className="font-bold text-sky-900 text-xs flex items-center gap-1.5"
                  >
                    <span>Jumlah Tanggungan Riil</span>
                    <span className="font-mono text-[10px] bg-sky-200 text-sky-900 px-1.5 py-0.2 rounded">
                      Tie-Breaker L3
                    </span>
                  </label>
                  <span className="text-xs font-mono text-sky-800 font-semibold">
                    {formData.realDependentsCount} Jiwa
                  </span>
                </div>
                <input
                  id="real-dependents-count"
                  aria-label="Jumlah Tanggungan Riil"
                  type="number"
                  min="0"
                  max="20"
                  required
                  value={formData.realDependentsCount}
                  onChange={(e) =>
                    setFormData({ ...formData, realDependentsCount: parseInt(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-2 bg-white border border-sky-300 rounded-lg font-mono font-bold text-sky-950 focus:outline-none focus:ring-1 focus:ring-sky-600"
                />
                <p className="text-[11px] text-sky-800">
                  Data jiwa riil ini disimpan khusus ke kolom database <code className="font-mono">real_dependents_count</code> untuk resolusi skor kembar di ambang kuota.
                </p>
              </div>

              {/* Crips Selection C1 - C4 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <label htmlFor="c1-crips" className="font-semibold text-on-surface text-xs block">
                    C1: Pendapatan Keluarga
                  </label>
                  <select
                    id="c1-crips"
                    value={formData.c1Crips}
                    onChange={(e) => setFormData({ ...formData, c1Crips: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-xs"
                  >
                    <option value="4">&lt; Rp 1.500.000 (Crips 4 - Paling Rentan)</option>
                    <option value="3">Rp 1.500.000 - Rp 2.500.000 (Crips 3)</option>
                    <option value="2">Rp 2.500.000 - Rp 3.500.000 (Crips 2)</option>
                    <option value="1">&gt; Rp 3.500.000 (Crips 1)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label htmlFor="c2-crips" className="font-semibold text-on-surface text-xs block">
                    C2: Jumlah Tanggungan (Interval)
                  </label>
                  <select
                    id="c2-crips"
                    value={formData.c2Crips}
                    onChange={(e) => setFormData({ ...formData, c2Crips: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-xs"
                  >
                    <option value="4">≥ 5 Orang (Crips 4 - Prioritas Tinggi)</option>
                    <option value="3">3 - 4 Orang (Crips 3)</option>
                    <option value="2">2 Orang (Crips 2)</option>
                    <option value="1">1 Orang (Crips 1)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label htmlFor="c3-crips" className="font-semibold text-on-surface text-xs block">
                    C3: Kondisi Rumah
                  </label>
                  <select
                    id="c3-crips"
                    value={formData.c3Crips}
                    onChange={(e) => setFormData({ ...formData, c3Crips: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-xs"
                  >
                    <option value="3">RTLH / Tidak Layak Huni (Crips 3)</option>
                    <option value="2">Rumah Semi Permanen (Crips 2)</option>
                    <option value="1">Rumah Permanen (Crips 1)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label htmlFor="c4-crips" className="font-semibold text-on-surface text-xs block">
                    C4: Kepemilikan Aset
                  </label>
                  <select
                    id="c4-crips"
                    value={formData.c4Crips}
                    onChange={(e) => setFormData({ ...formData, c4Crips: e.target.value })}
                    className="w-full px-3 py-2 bg-surface border border-border-subtle rounded-lg text-xs"
                  >
                    <option value="4">Tanpa Kendaraan / Sepeda (Crips 4)</option>
                    <option value="3">1 Unit Sepeda Motor (Crips 3)</option>
                    <option value="2">&gt; 1 Unit Motor (Crips 2)</option>
                    <option value="1">Memiliki Mobil Pribadi (Crips 1)</option>
                  </select>
                </div>
              </div>

              {/* FR-02 TMS GATEKEEPER SELECTOR */}
              <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <label
                    htmlFor="eligibility-status-select"
                    className="font-bold text-on-surface text-xs flex items-center gap-1.5"
                  >
                    <ShieldAlert className="w-4 h-4 text-slate-700" />
                    <span>Status Kelayakan Administratif</span>
                  </label>
                  <span className="text-[11px] font-mono text-secondary">FR-02 Filter TMS</span>
                </div>

                <select
                  id="eligibility-status-select"
                  aria-label="Status Kelayakan Administratif"
                  value={formData.eligibilityStatus}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      eligibilityStatus: e.target.value as "ELIGIBLE" | "DISQUALIFIED",
                    })
                  }
                  className={`w-full px-3 py-2 rounded-lg font-semibold text-xs border ${
                    formData.eligibilityStatus === "ELIGIBLE"
                      ? "bg-emerald-50 text-emerald-900 border-emerald-300"
                      : "bg-rose-50 text-rose-900 border-rose-300"
                  }`}
                >
                  <option value="ELIGIBLE">ELIGIBLE (Memenuhi Syarat Administratif)</option>
                  <option value="DISQUALIFIED">DISQUALIFIED (Tidak Memenuhi Syarat - TMS)</option>
                </select>

                {formData.eligibilityStatus === "DISQUALIFIED" && (
                  <div className="space-y-1 pt-1">
                    <label
                      htmlFor="tms-reason-select"
                      className="font-bold text-rose-900 text-xs block"
                    >
                      Alasan Tidak Memenuhi Syarat (Wajib Dipilih) *
                    </label>
                    <select
                      id="tms-reason-select"
                      aria-label="Alasan Tidak Memenuhi Syarat"
                      value={formData.disqualificationReason}
                      onChange={(e) =>
                        setFormData({ ...formData, disqualificationReason: e.target.value })
                      }
                      className="w-full px-3 py-2 bg-white border border-rose-300 rounded-lg text-rose-950 font-medium text-xs focus:ring-1 focus:ring-rose-500"
                    >
                      <option value="ASN / TNI / POLRI">Anggota ASN / TNI / POLRI Aktif</option>
                      <option value="PKH Ganda / BPNT Aktif">Penerima Bansos Reguler Ganda (PKH/BPNT)</option>
                      <option value="Pindah Domisili">Pindah Domisili Luar Kelurahan</option>
                      <option value="Meninggal Dunia">Meninggal Dunia Tanpa Ahli Waris</option>
                    </select>
                    <p className="text-[11px] text-rose-700 leading-relaxed">
                      Warga TMS akan dikecualikan dari komputasi SAW agar tidak mendistorsi nilai min/max kriteria, namun tetap tercatat dalam Lampiran Berita Acara resmi.
                    </p>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                className="w-full py-2.5 bg-primary hover:bg-primary-container text-white font-semibold rounded-lg flex items-center justify-center gap-2 transition-colors shadow-xs"
              >
                <Save className="w-4 h-4" />
                <span>Simpan Usulan Calon KPM</span>
              </button>

              {submissionSuccess && (
                <div className="p-2.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 shrink-0" />
                  <span>Data warga berhasil disimpan ke basis data RT {currentRt}!</span>
                </div>
              )}
            </form>
          </div>

          {/* Right Column: Recorded Candidates List in Current RT (5 cols) */}
          <div className="lg:col-span-5 bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <div>
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Daftar Usulan Terdaftar (RT {currentRt})
                </h3>
                <span className="text-xs text-secondary">
                  Total: {recordedList.length} berkas KPM
                </span>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface text-secondary">
                RW 02
              </span>
            </div>

            <div className="space-y-2.5 max-h-[620px] overflow-y-auto pr-1">
              {recordedList.map((kpm) => (
                <div
                  key={kpm.id}
                  className="p-3 bg-surface rounded-lg border border-slate-100 hover:border-border-subtle transition-colors space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-on-surface text-sm">{kpm.name}</span>
                    {kpm.status === "ELIGIBLE" ? (
                      <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200 font-mono text-[10px] font-bold">
                        ELIGIBLE
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-rose-50 text-rose-800 border border-rose-200 font-mono text-[10px] font-bold">
                        TMS
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-secondary font-mono text-[11px]">
                    <span>NIK: {kpm.nik}</span>
                    <span>{kpm.dependents} Jiwa</span>
                  </div>

                  {kpm.status === "DISQUALIFIED" && kpm.disqualificationReason && (
                    <div className="text-[11px] text-rose-700 font-medium">
                      Alasan TMS: {kpm.disqualificationReason}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default SurveyorInputPage;
