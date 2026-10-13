import React, { useState } from "react";
import {
  Cpu,
  Lock,
  Sparkles,
  Play,
  Pause,
  Zap,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";
import { CriteriaGapChart } from "../../components/public/CriteriaGapChart";

export const XaiGeneratorPage: React.FC = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [selectedCandidateCode, setSelectedCandidateCode] = useState("KPM-035");

  // Mock Worker Progress State
  const workerStatus = {
    batchId: "BNS-JUBAR-2026-T1",
    totalCandidates: 114,
    completed: 78,
    geminiSuccess: 76,
    deterministicFallback: 2,
    inProgress: 1,
    pending: 35,
    rpmRate: 12.0,
    elapsedTime: "02m : 15s",
    estRemaining: "~ 01m : 10s",
  };

  const progressPercentage = Math.round(
    (workerStatus.completed / workerStatus.totalCandidates) * 100
  );

  // Mock Candidate List
  const queueList = [
    {
      code: "KPM-001",
      rank: 1,
      status: "COMPLETED",
      source: "GEMINI_API",
      score: 0.942,
    },
    {
      code: "KPM-002",
      rank: 2,
      status: "COMPLETED",
      source: "GEMINI_API",
      score: 0.9345,
    },
    {
      code: "KPM-030",
      rank: 30,
      status: "COMPLETED",
      source: "GEMINI_API",
      score: 0.725,
      isCutoff: true,
    },
    {
      code: "KPM-035",
      rank: 35,
      status: "COMPLETED",
      source: "DETERMINISTIC_FALLBACK",
      score: 0.684,
      isRejected: true,
    },
    {
      code: "KPM-036",
      rank: 36,
      status: "IN_PROGRESS",
      source: "PENDING",
      score: 0.681,
    },
    {
      code: "KPM-037",
      rank: 37,
      status: "PENDING",
      source: "PENDING",
      score: 0.675,
    },
  ];

  // Active Selected Candidate Details (Sanitized Zero-PII Payload)
  const activePayload = {
    applicant_code: "KPM-035",
    rank: 35,
    quota: 30,
    status: "TIDAK_LOLOS",
    final_score: 0.684,
    cutoff_score: 0.725,
    source: "DETERMINISTIC_FALLBACK",
    criteria_data: [
      {
        code: "C1",
        name: "Pendapatan Keluarga",
        weight: 0.30,
        type: "COST",
        normalized_score: 0.60,
        passing_avg: 0.85,
        gap: -0.25,
      },
      {
        code: "C2",
        name: "Jumlah Tanggungan",
        weight: 0.25,
        type: "BENEFIT",
        normalized_score: 0.80,
        passing_avg: 0.78,
        gap: +0.02,
      },
      {
        code: "C3",
        name: "Kondisi Tempat Tinggal",
        weight: 0.25,
        type: "COST",
        normalized_score: 0.70,
        passing_avg: 0.80,
        gap: -0.10,
      },
      {
        code: "C4",
        name: "Kepemilikan Aset", // CORRECTED: Kepemilikan Aset (NOT Daya Listrik)
        weight: 0.20,
        type: "COST",
        normalized_score: 0.65,
        passing_avg: 0.75,
        gap: -0.10,
      },
    ],
    ai_narrative:
      "Berdasarkan hasil musyawarah seleksi objektif Simple Additive Weighting Kelurahan Jurangmangu Barat, berkas Anda berada pada peringkat 35 dari alokasi kuota 30 penerima manfaat (Skor 0.684 vs Ambang Batas 0.725). Meskipun indikator tanggungan keluarga Anda memiliki bobot kerentanan yang tinggi (0.80), faktor pendapatan keluarga dan kepemilikan aset menempatkan usulan Anda pada prioritas cadangan. Apabila terdapat perubahan kondisi ekonomi atau data kependudukan terkini, silakan berkoordinasi dengan Ketua RT setempat untuk pemutakhiran pada periode berikutnya.",
  };

  const chartData = activePayload.criteria_data.map((c) => ({
    kriteria: c.name,
    skor_pemohon: c.normalized_score,
    rata_rata_lolos: c.passing_avg,
  }));

  return (
    <AppShell
      title="Generator Narasi XAI Gemini & Monitor Asinkron"
      breadcrumb={["AI Explainability", "Worker Queue", "Monitoring Narasi"]}
    >
      <div className="space-y-6">
        {/* Top Header & Operational Strip */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                FR-04 & FR-05 Engine
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                <Lock className="w-3.5 h-3.5 text-emerald-700" />
                Zero-PII Sanitation Active
              </span>
              <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded bg-sky-50 text-sky-800 border border-sky-200">
                <Zap className="w-3.5 h-3.5 text-sky-700" />
                Gemini 2.5 Flash Online
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Monitoring Worker Pembangkitan Narasi Transparansi Keputusan
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Narasi penjelasan disusun otomatis dalam Bahasa Indonesia menggunakan Google Gemini Flash berlatensi rendah dengan perlindungan privasi PII mutlak.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={() => setIsProcessing(!isProcessing)}
              className="flex items-center gap-1.5 px-4 py-2 text-xs sm:text-sm font-semibold bg-primary hover:bg-primary-container text-white rounded-lg transition-colors shadow-xs"
            >
              {isProcessing ? (
                <>
                  <Pause className="w-4 h-4" />
                  <span>Jeda Worker</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Jalankan Antrean XAI</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Worker Progress Banner (Real-time Polling State) */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary text-white flex items-center justify-center shrink-0">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-on-surface text-sm sm:text-base">
                    Antrean Pekerja Asinkron: Batch {workerStatus.batchId}
                  </span>
                  <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-surface text-secondary">
                    Rate-Safe Mode
                  </span>
                </div>
                <span className="text-xs text-secondary">
                  Melayani 114 KPM • Rate Limiter: {workerStatus.rpmRate} RPM
                </span>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs font-mono">
              <div>
                <span className="text-secondary block">Waktu Berjalan:</span>
                <span className="font-bold text-on-surface">{workerStatus.elapsedTime}</span>
              </div>
              <div>
                <span className="text-secondary block">Estimasi Sisa:</span>
                <span className="font-bold text-emerald-800">{workerStatus.estRemaining}</span>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="font-bold text-on-surface">Progres Adjudikasi XAI</span>
              <span className="font-bold text-primary">
                {workerStatus.completed} dari {workerStatus.totalCandidates} KPM Selesai ({progressPercentage}%)
              </span>
            </div>
            <div className="w-full bg-slate-100 h-3 rounded-full overflow-hidden border border-slate-200">
              <div
                className="bg-primary h-full rounded-full transition-all duration-500"
                style={{ width: `${progressPercentage}%` }}
              />
            </div>
          </div>

          {/* Unclipped Metric Chips Grid (Responsive 1 col mobile, 2 col tablet, 4 col desktop) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 pt-1">
            <div className="p-3 bg-surface rounded-lg border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-600" />
                <span className="text-xs font-medium text-on-surface">Gemini API Success</span>
              </div>
              <span className="font-mono font-bold text-xs text-on-surface">
                {workerStatus.geminiSuccess} KPM
              </span>
            </div>

            <div className="p-3 bg-surface rounded-lg border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-600" />
                <span className="text-xs font-medium text-amber-900">Deterministic Fallback</span>
              </div>
              <span className="font-mono font-bold text-xs text-amber-800">
                {workerStatus.deterministicFallback} KPM
              </span>
            </div>

            <div className="p-3 bg-surface rounded-lg border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-600 animate-pulse" />
                <span className="text-xs font-medium text-on-surface">Sedang Dihasilkan</span>
              </div>
              <span className="font-mono font-bold text-xs text-sky-800">
                {workerStatus.inProgress} KPM
              </span>
            </div>

            <div className="p-3 bg-surface rounded-lg border border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                <span className="text-xs font-medium text-secondary">Antrean Tertunda</span>
              </div>
              <span className="font-mono font-bold text-xs text-secondary">
                {workerStatus.pending} KPM
              </span>
            </div>
          </div>
        </div>

        {/* Master Detail Grid: Candidate Queue (4 Cols) vs Active XAI Inspection Panel (8 Cols) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Candidate Queue Stack (4 cols) */}
          <div className="lg:col-span-4 bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="border-b border-border-subtle pb-3 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Antrean Kandidat XAI
                </h3>
                <span className="text-xs text-secondary">Klik kode untuk inspeksi narasi</span>
              </div>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-surface text-secondary">
                Live Feed
              </span>
            </div>

            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {queueList.map((kpm) => {
                const isSelected = kpm.code === selectedCandidateCode;
                return (
                  <div
                    key={kpm.code}
                    onClick={() => setSelectedCandidateCode(kpm.code)}
                    className={`p-3 rounded-lg border cursor-pointer transition-all text-xs space-y-1 ${
                      isSelected
                        ? "bg-emerald-50 border-emerald-300 shadow-xs"
                        : "bg-surface border-slate-100 hover:border-border-subtle"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-on-surface">
                        {kpm.code}
                      </span>
                      <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-white text-secondary border">
                        Rank #{kpm.rank}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-secondary font-mono text-[11px]">
                      <span>Skor: {kpm.score.toFixed(4)}</span>
                      {kpm.source === "GEMINI_API" && (
                        <span className="text-emerald-700 font-semibold">Gemini Flash</span>
                      )}
                      {kpm.source === "DETERMINISTIC_FALLBACK" && (
                        <span className="text-amber-800 font-semibold">Fallback Engine</span>
                      )}
                      {kpm.status === "IN_PROGRESS" && (
                        <span className="text-sky-700 font-semibold animate-pulse">Memproses...</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column: Active XAI Inspection & Gap Analysis (8 cols) */}
          <div className="lg:col-span-8 space-y-5">
            {/* Zero-PII Payload Monitor Box */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border-subtle pb-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-bold text-on-surface">
                      Inspeksi Payload: {activePayload.applicant_code}
                    </span>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                      Sumber: Deterministic Fallback
                    </span>
                  </div>
                  <span className="text-xs text-secondary">
                    Data anonim 100% tanpa identitas warga (Kepatuhan UU PDP No. 27/2022)
                  </span>
                </div>
              </div>

              {/* 4 Criteria Chips: Explicitly includes C4: Kepemilikan Aset */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="p-3 bg-surface rounded-lg border border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between font-mono">
                    <span className="font-bold text-on-surface">C1: Pendapatan Keluarga</span>
                    <span className="text-rose-700 font-semibold">Cost (0.30)</span>
                  </div>
                  <div className="text-secondary font-mono text-[11px]">
                    Nilai Normalisasi: {activePayload.criteria_data[0].normalized_score.toFixed(2)} (Rata-rata: {activePayload.criteria_data[0].passing_avg.toFixed(2)})
                  </div>
                </div>

                <div className="p-3 bg-surface rounded-lg border border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between font-mono">
                    <span className="font-bold text-on-surface">C2: Jumlah Tanggungan</span>
                    <span className="text-emerald-700 font-semibold">Benefit (0.25)</span>
                  </div>
                  <div className="text-secondary font-mono text-[11px]">
                    Nilai Normalisasi: {activePayload.criteria_data[1].normalized_score.toFixed(2)} (Rata-rata: {activePayload.criteria_data[1].passing_avg.toFixed(2)})
                  </div>
                </div>

                <div className="p-3 bg-surface rounded-lg border border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between font-mono">
                    <span className="font-bold text-on-surface">C3: Kondisi Tempat Tinggal</span>
                    <span className="text-rose-700 font-semibold">Cost (0.25)</span>
                  </div>
                  <div className="text-secondary font-mono text-[11px]">
                    Nilai Normalisasi: {activePayload.criteria_data[2].normalized_score.toFixed(2)} (Rata-rata: {activePayload.criteria_data[2].passing_avg.toFixed(2)})
                  </div>
                </div>

                {/* Explicitly C4: Kepemilikan Aset */}
                <div className="p-3 bg-surface rounded-lg border border-slate-100 text-xs space-y-1">
                  <div className="flex justify-between font-mono">
                    <span className="font-bold text-on-surface">C4: Kepemilikan Aset</span>
                    <span className="text-rose-700 font-semibold">Cost (0.20)</span>
                  </div>
                  <div className="text-secondary font-mono text-[11px]">
                    Nilai Normalisasi: {activePayload.criteria_data[3].normalized_score.toFixed(2)} (Rata-rata: {activePayload.criteria_data[3].passing_avg.toFixed(2)})
                  </div>
                </div>
              </div>

              {/* Generated AI Explanation Narrative Box */}
              <div className="p-4 bg-emerald-950 text-white rounded-xl shadow-xs space-y-2">
                <div className="flex items-center gap-2 text-emerald-300">
                  <Sparkles className="w-4 h-4" />
                  <span className="text-xs font-mono uppercase tracking-wider font-semibold">
                    Hasil Narasi Penjelasan Transparan (Bahasa Indonesia)
                  </span>
                </div>
                <p className="text-xs sm:text-sm text-emerald-50 leading-relaxed font-sans">
                  "{activePayload.ai_narrative}"
                </p>
              </div>

              {/* Criteria Gap Bar Chart */}
              <div className="pt-2">
                <CriteriaGapChart items={chartData} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default XaiGeneratorPage;
