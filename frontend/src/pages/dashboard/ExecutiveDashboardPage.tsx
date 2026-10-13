import React, { useState } from "react";
import {
  Users,
  Award,
  Activity,
  CheckCircle2,
  FileSpreadsheet,
  RefreshCw,
  Shield,
  Layers,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";
import { useAuth } from "../../context/AuthContext";

export const ExecutiveDashboardPage: React.FC = () => {
  const { user } = useAuth();
  const [activeBatch, setActiveBatch] = useState("2026-Q1");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  const handleExport = () => {
    window.open("/api/citizens/export-excel/", "_blank");
  };

  // Mock batch data for display
  const metrics = {
    totalCandidates: 120,
    eligibleCount: 114,
    disqualifiedCount: 6,
    quota: 30,
    pipelineStage: "Narrated",
    pipelineStep: 4,
    totalSteps: 6,
    cutoffScore: 0.725,
    engineStatus: "Online",
    llmModel: "Gemini 2.5 Flash",
  };

  const rtDistributions = [
    { rt: "RT 01", rw: "RW 01", count: 14, eligible: 13, tms: 1, quotaEst: 4 },
    { rt: "RT 02", rw: "RW 01", count: 11, eligible: 11, tms: 0, quotaEst: 3 },
    { rt: "RT 03", rw: "RW 02", count: 18, eligible: 17, tms: 1, quotaEst: 5 },
    { rt: "RT 04", rw: "RW 02", count: 12, eligible: 11, tms: 1, quotaEst: 3 },
    { rt: "RT 05", rw: "RW 03", count: 10, eligible: 10, tms: 0, quotaEst: 2 },
    { rt: "RT 06", rw: "RW 03", count: 15, eligible: 14, tms: 1, quotaEst: 4 },
    { rt: "RT 07", rw: "RW 04", count: 13, eligible: 12, tms: 1, quotaEst: 3 },
    { rt: "RT 08", rw: "RW 04", count: 9, eligible: 9, tms: 0, quotaEst: 2 },
    { rt: "RT 09", rw: "RW 05", count: 11, eligible: 10, tms: 1, quotaEst: 3 },
    { rt: "RT 10", rw: "RW 05", count: 7, eligible: 7, tms: 0, quotaEst: 1 },
  ];

  const recentAudits = [
    {
      id: "AUD-104",
      action: "BATCH_CALCULATED",
      actor: "Budi Hartono (Kasi Kesos)",
      time: "10 menit lalu",
      detail: "Kalkulasi SAW 114 KPM selesai dengan 2 kasus tie-breaker.",
    },
    {
      id: "AUD-103",
      action: "XAI_NARRATION_BATCH",
      actor: "Worker Asinkron #01",
      time: "15 menit lalu",
      detail: "Pembangkitan narasi Zero-PII Gemini Flash: 114/114 selesai.",
    },
    {
      id: "AUD-102",
      action: "TMS_FLAGGED",
      actor: "Ketua RT 03",
      time: "1 jam lalu",
      detail: "1 warga ditandai TMS: Terdaftar aktif sebagai ASN/PNS.",
    },
    {
      id: "AUD-101",
      action: "BATCH_CRITERIA_FREEZE",
      actor: "Sistem Otomatis",
      time: "2 jam lalu",
      detail: "Bobot preferensi dibekukan ke BATCH_CRITERIA snapshot.",
    },
  ];

  return (
    <AppShell
      title="Ringkasan Eksekutif & Adjudikasi"
      breadcrumb={["Tata Kelola", "Overview", "Batch Aktif"]}
    >
      <div className="space-y-6">
        {/* Top Header & Operational Actions Cluster */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 bg-white p-4 sm:p-5 rounded-xl border border-border-subtle shadow-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-label-md text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                Batch Aktif
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Tahap 4: Narrated
              </span>
              <span className="text-xs font-mono text-secondary">
                ID: BNS-JUBAR-2026-T1
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Alokasi Bansos Sembako Tahap I 2026 — Kelurahan Jurangmangu Barat
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Selamat bertugas, <span className="font-semibold text-primary">{user?.name || "Staf Kelurahan"}</span>. Pantau alur adjudikasi objektif SAW dan hasil sintesis penjelasan XAI.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <select
              aria-label="Pilih Batch Seleksi"
              value={activeBatch}
              onChange={(e) => setActiveBatch(e.target.value)}
              className="px-3 py-2 text-xs sm:text-sm font-medium bg-surface border border-border-subtle rounded-lg text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="2026-Q1">Batch 2026-Q1 (Tahap I)</option>
              <option value="2025-Q4">Batch 2025-Q4 (Arsip)</option>
            </select>

            <button
              onClick={handleRefresh}
              className="flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium bg-white hover:bg-surface border border-border-subtle rounded-lg text-secondary hover:text-on-surface transition-colors shadow-xs"
              title="Perbarui Data"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">Refresh Data</span>
            </button>

            {/* Replaced prohibited "Sinkronisasi DTKS" button with permitted official action */}
            <button
              onClick={handleExport}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs sm:text-sm font-semibold bg-primary hover:bg-primary-container text-white rounded-lg transition-colors shadow-xs"
            >
              <FileSpreadsheet className="w-4 h-4" />
              <span>Ekspor Usulan (.xlsx)</span>
            </button>
          </div>
        </div>

        {/* Bento Grid: 4 Metric Cards (Responsive: 1 col on mobile, 2 col on tablet, 4 col on desktop) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          {/* Card 1: Total Usulan & TMS Breakdown */}
          <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between text-secondary">
              <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                Total Calon KPM
              </span>
              <div className="p-2 rounded-lg bg-surface text-primary">
                <Users className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2">
              <div className="text-2xl sm:text-3xl font-bold font-mono text-on-surface">
                {metrics.totalCandidates}
              </div>
              <div className="flex items-center gap-2 mt-1.5 text-xs">
                <span className="font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                  {metrics.eligibleCount} Memenuhi Syarat
                </span>
                <span className="font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                  {metrics.disqualifiedCount} TMS
                </span>
              </div>
            </div>
          </div>

          {/* Card 2: Kuota & Ambang Kelolosan */}
          <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between text-secondary">
              <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                Kuota Penerima
              </span>
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-800">
                <Award className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2">
              <div className="text-2xl sm:text-3xl font-bold font-mono text-emerald-800">
                {metrics.quota}{" "}
                <span className="text-xs font-normal text-secondary font-sans">
                  Kepala Keluarga
                </span>
              </div>
              <div className="mt-1.5 text-xs text-secondary">
                Ambang Batas Skor:{" "}
                <span className="font-mono font-bold text-on-surface">
                  V_i ≥ {metrics.cutoffScore.toFixed(4)}
                </span>
              </div>
            </div>
          </div>

          {/* Card 3: Pipeline Engine Status */}
          <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between text-secondary">
              <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                Pipeline Seleksi
              </span>
              <div className="p-2 rounded-lg bg-surface text-primary">
                <Layers className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2">
              <div className="text-base sm:text-lg font-bold text-on-surface">
                Tahap {metrics.pipelineStep}/6: {metrics.pipelineStage}
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full mt-2 overflow-hidden">
                <div
                  className="bg-primary h-full rounded-full transition-all duration-500"
                  style={{ width: `${(metrics.pipelineStep / metrics.totalSteps) * 100}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-secondary">
                Siap diajukan ke Lurah untuk pengesahan Berita Acara.
              </p>
            </div>
          </div>

          {/* Card 4: Engine & Zero-PII Status */}
          <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col justify-between">
            <div className="flex items-center justify-between text-secondary">
              <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                Integritas & AI
              </span>
              <div className="p-2 rounded-lg bg-emerald-50 text-emerald-800">
                <Shield className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-600 animate-pulse" />
                <span className="text-sm font-bold text-on-surface">
                  {metrics.llmModel} Online
                </span>
              </div>
              <div className="mt-2 flex flex-col gap-1 text-xs text-secondary">
                <span className="text-emerald-700 font-medium">✓ Zero-PII Sanitation Aktif</span>
                <span className="text-slate-600">✓ Enkripsi AES-256 NIK at-Rest</span>
              </div>
            </div>
          </div>
        </div>

        {/* Master Detail Section: Distribution per RT & Recent Audits */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Aggregates per RT (8 cols) */}
          <div className="lg:col-span-8 bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
              <div>
                <h3 className="text-base font-bold text-on-surface">
                  Rekapitulasi Usulan Lapangan per RT
                </h3>
                <p className="text-xs text-secondary">
                  Distribusi sebaran berkas warga dari Ketua RT 01 s/d RT 10 di Kelurahan Jurangmangu Barat.
                </p>
              </div>
              <span className="text-xs font-mono text-secondary px-2.5 py-1 bg-surface rounded">
                10 RT Terverifikasi
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs sm:text-sm">
                <thead>
                  <tr className="border-b border-border-subtle font-mono text-xs text-secondary uppercase tracking-wider">
                    <th className="py-2.5 px-3">Wilayah</th>
                    <th className="py-2.5 px-3 text-right">Total Berkas</th>
                    <th className="py-2.5 px-3 text-right text-emerald-700">Eligible</th>
                    <th className="py-2.5 px-3 text-right text-rose-700">TMS</th>
                    <th className="py-2.5 px-3 text-right">Estimasi Lolos</th>
                    <th className="py-2.5 px-3 text-right">Proporsi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {rtDistributions.map((row) => {
                    const pct = Math.round((row.eligible / metrics.eligibleCount) * 100);
                    return (
                      <tr key={row.rt} className="hover:bg-slate-50 transition-colors">
                        <td className="py-2.5 px-3 font-semibold text-on-surface">
                          {row.rt} <span className="text-xs text-secondary font-normal font-mono">({row.rw})</span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-medium text-on-surface">
                          {row.count}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-800">
                          {row.eligible}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono text-rose-700">
                          {row.tms > 0 ? row.tms : "-"}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono font-semibold text-primary">
                          {row.quotaEst} KPM
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 bg-slate-100 h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-primary h-full rounded-full"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="font-mono text-xs text-secondary w-8">{pct}%</span>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Right Column: Live Audit Trail & Quick Guide (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-border-subtle pb-3">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" />
                  <h3 className="text-sm font-bold text-on-surface">
                    Audit Log Adjudikasi
                  </h3>
                </div>
                <span className="text-[10px] font-mono text-secondary uppercase bg-surface px-1.5 py-0.5 rounded">
                  Live
                </span>
              </div>

              <div className="space-y-3">
                {recentAudits.map((audit) => (
                  <div
                    key={audit.id}
                    className="p-3 bg-surface rounded-lg border border-slate-100 text-xs space-y-1 hover:border-border-subtle transition-colors"
                  >
                    <div className="flex items-center justify-between text-secondary">
                      <span className="font-mono font-semibold text-primary">
                        {audit.action}
                      </span>
                      <span className="text-[11px] font-mono">{audit.time}</span>
                    </div>
                    <p className="text-on-surface font-medium leading-relaxed">
                      {audit.detail}
                    </p>
                    <div className="text-[11px] text-secondary">Oleh: {audit.actor}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Statutory Compliance Notice */}
            <div className="bg-emerald-900 text-white rounded-xl p-5 shadow-xs space-y-2">
              <div className="flex items-center gap-2 text-emerald-200">
                <CheckCircle2 className="w-4 h-4" />
                <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                  Kepatuhan SPBE & UU PDP
                </span>
              </div>
              <p className="text-xs text-emerald-100 leading-relaxed">
                Setiap mutasi data dan kalkulasi pembobotan dicatat secara kriptografis ke dalam basis data kelurahan. Nama warga dan NIK disanitasi sebelum dikirimkan ke model penjelasan AI.
              </p>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default ExecutiveDashboardPage;
