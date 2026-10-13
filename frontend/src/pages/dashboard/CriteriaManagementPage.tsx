import React, { useState, useMemo } from "react";
import {
  Lock,
  Unlock,
  CheckCircle2,
  AlertTriangle,
  Save,
  RotateCcw,
  Scale,
  Sparkles,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";

interface CriteriaManagementPageProps {
  isSnapshotLocked?: boolean;
}

export const CriteriaManagementPage: React.FC<CriteriaManagementPageProps> = ({
  isSnapshotLocked = false,
}) => {
  // Weights state: default 0.30, 0.25, 0.25, 0.20
  const [weights, setWeights] = useState({
    c1: 0.30,
    c2: 0.25,
    c3: 0.25,
    c4: 0.20,
  });

  const isLocked = isSnapshotLocked;
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Calculate sum of weights
  const totalWeight = useMemo(() => {
    const sum = weights.c1 + weights.c2 + weights.c3 + weights.c4;
    return Math.round(sum * 1000) / 1000;
  }, [weights]);

  const isValidSum = Math.abs(totalWeight - 1.00) < 0.0001;

  const handleWeightChange = (key: keyof typeof weights, value: string) => {
    if (isLocked) return;
    const num = parseFloat(value);
    setWeights((prev) => ({
      ...prev,
      [key]: isNaN(num) ? 0 : num,
    }));
    setSaveSuccess(false);
  };

  const handleReset = () => {
    if (isLocked) return;
    setWeights({
      c1: 0.30,
      c2: 0.25,
      c3: 0.25,
      c4: 0.20,
    });
    setSaveSuccess(false);
  };

  const handleSave = () => {
    if (!isValidSum || isLocked) return;
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  return (
    <AppShell
      title="Manajemen Kriteria & Bobot Preferensi SAW"
      breadcrumb={["Tata Kelola", "Kriteria SAW", "Konfigurasi Bobot"]}
    >
      <div className="space-y-6">
        {/* Header & Status Banner */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                FR-01 Modul Kriteria
              </span>
              {isLocked ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200">
                  <Lock className="w-3.5 h-3.5" />
                  Frozen Snapshot Aktif
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  <Unlock className="w-3.5 h-3.5" />
                  Mode Konfigurasi Terbuka
                </span>
              )}
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Konfigurasi Bobot Preferensi & Klasifikasi Crips
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Tentukan bobot kriteria matematis Simple Additive Weighting. Syarat mutlak SAW: total bobot seluruh kriteria wajib tepat 1.00 (100%).
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={handleReset}
              disabled={isLocked}
              className="flex items-center gap-1.5 px-3 py-2 text-xs sm:text-sm font-medium bg-white hover:bg-surface border border-border-subtle rounded-lg text-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset Default</span>
            </button>

            <button
              onClick={handleSave}
              disabled={!isValidSum || isLocked}
              className={`flex items-center gap-1.5 px-4 py-2 text-xs sm:text-sm font-semibold rounded-lg transition-all shadow-xs ${
                isValidSum && !isLocked
                  ? "bg-primary hover:bg-primary-container text-white cursor-pointer"
                  : "bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300"
              }`}
            >
              <Save className="w-4 h-4" />
              <span>Simpan & Validasi Bobot</span>
            </button>
          </div>
        </div>

        {/* Snapshot Notification Alert if Locked */}
        {isLocked && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 text-amber-900">
            <Lock className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
            <div className="text-xs sm:text-sm space-y-1">
              <span className="font-bold">Kunci Kriteria: Snapshot Batch BNS-JUBAR-2026-T1</span>
              <p className="text-amber-800 leading-relaxed">
                Kriteria dan bobot ini telah dibekukan ke tabel <code className="font-mono bg-amber-100 px-1 py-0.5 rounded">BATCH_CRITERIA</code> saat eksekusi kalkulasi dilakukan. Perubahan bobot di masa depan tidak akan merusak histori batch yang sedang berjalan.
              </p>
            </div>
          </div>
        )}

        {/* Interactive Weight Balance Visualizer Bar */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-primary" />
              <span className="text-sm font-bold text-on-surface">
                Keseimbangan Akumulasi Bobot (Σ w_j)
              </span>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary">Total Terkini:</span>
              <span
                className={`font-mono text-base font-bold px-2 py-0.5 rounded ${
                  isValidSum
                    ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    : "bg-rose-50 text-rose-800 border border-rose-200 animate-pulse"
                }`}
              >
                {totalWeight.toFixed(2)} / 1.00
              </span>
            </div>
          </div>

          {/* Stacked Proportional Bar */}
          <div className="w-full bg-slate-100 h-4 rounded-lg overflow-hidden flex border border-slate-200">
            <div
              className="bg-emerald-900 h-full transition-all duration-300"
              style={{ width: `${Math.max(0, weights.c1 * 100)}%` }}
              title={`C1: ${Math.round(weights.c1 * 100)}%`}
            />
            <div
              className="bg-sky-600 h-full transition-all duration-300"
              style={{ width: `${Math.max(0, weights.c2 * 100)}%` }}
              title={`C2: ${Math.round(weights.c2 * 100)}%`}
            />
            <div
              className="bg-teal-600 h-full transition-all duration-300"
              style={{ width: `${Math.max(0, weights.c3 * 100)}%` }}
              title={`C3: ${Math.round(weights.c3 * 100)}%`}
            />
            <div
              className="bg-slate-700 h-full transition-all duration-300"
              style={{ width: `${Math.max(0, weights.c4 * 100)}%` }}
              title={`C4: ${Math.round(weights.c4 * 100)}%`}
            />
          </div>

          {/* Validation Feedback Message */}
          {!isValidSum ? (
            <div className="flex items-center gap-2 text-rose-700 text-xs font-medium bg-rose-50 p-2.5 rounded-lg border border-rose-200">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>
                Total bobot harus persis bernilai 1.00 (saat ini {totalWeight.toFixed(2)}). Kalkulasi SAW tidak dapat diproses jika total bobot belum seimbang.
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-emerald-700 text-xs font-medium bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>
                Valid & Seimbang (100%). Seluruh bobot preferensi memenuhi kaidah normalisasi Simple Additive Weighting.
              </span>
            </div>
          )}

          {saveSuccess && (
            <div className="text-xs font-medium text-emerald-800 bg-emerald-100 p-2 rounded">
              Konfigurasi bobot berhasil disimpan ke database!
            </div>
          )}
        </div>

        {/* Master Detail Grid: Criteria Cards (8 Cols) vs Formula & Snapshot Guide (4 Cols) */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* Left Column: 4 Criteria Cards (8 Cols) */}
          <div className="xl:col-span-8 space-y-4">
            {/* Card C1: Pendapatan Keluarga (COST) */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-emerald-900 text-white font-mono font-bold flex items-center justify-center text-sm">
                    C1
                  </span>
                  <div>
                    <h3 className="font-bold text-on-surface text-sm sm:text-base">
                      Pendapatan Keluarga
                    </h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                        Tipe: COST
                      </span>
                      <span className="text-secondary">Makin rendah pendapatan, skor kelayakan makin tinggi</span>
                    </div>
                  </div>
                </div>

                {/* Weight Input & Slider */}
                <div className="flex items-center gap-2">
                  <label htmlFor="c1-weight" className="text-xs text-secondary font-medium">
                    Bobot C1:
                  </label>
                  <input
                    id="c1-weight"
                    aria-label="Bobot C1 (Pendapatan)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    disabled={isLocked}
                    value={weights.c1}
                    onChange={(e) => handleWeightChange("c1", e.target.value)}
                    className="w-20 px-2 py-1 text-right font-mono text-sm font-bold bg-surface border border-border-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
                  />
                  <span className="text-xs font-mono text-secondary">
                    ({Math.round(weights.c1 * 100)}%)
                  </span>
                </div>
              </div>

              {/* Crips Mapping */}
              <div className="space-y-1.5">
                <span className="text-xs font-mono uppercase text-secondary tracking-wider font-semibold">
                  Klasifikasi Nilai Crips (v_i1):
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">&gt; Rp 3.500.000</span>
                    <span className="font-bold text-on-surface">Crips: 1</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Rp 2.500.000 - 3.500.000</span>
                    <span className="font-bold text-on-surface">Crips: 2</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Rp 1.500.000 - 2.500.000</span>
                    <span className="font-bold text-on-surface">Crips: 3</span>
                  </div>
                  <div className="p-2 bg-emerald-50 rounded border border-emerald-200">
                    <span className="text-emerald-800 font-mono text-[11px] block">&lt; Rp 1.500.000</span>
                    <span className="font-bold text-emerald-900">Crips: 4</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Card C2: Jumlah Tanggungan (BENEFIT) */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-sky-600 text-white font-mono font-bold flex items-center justify-center text-sm">
                    C2
                  </span>
                  <div>
                    <h3 className="font-bold text-on-surface text-sm sm:text-base">
                      Jumlah Tanggungan Keluarga
                    </h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-semibold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100">
                        Tipe: BENEFIT
                      </span>
                      <span className="text-secondary">Makin banyak tanggungan jiwa, prioritas makin tinggi</span>
                    </div>
                  </div>
                </div>

                {/* Weight Input & Slider */}
                <div className="flex items-center gap-2">
                  <label htmlFor="c2-weight" className="text-xs text-secondary font-medium">
                    Bobot C2:
                  </label>
                  <input
                    id="c2-weight"
                    aria-label="Bobot C2 (Tanggungan)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    disabled={isLocked}
                    value={weights.c2}
                    onChange={(e) => handleWeightChange("c2", e.target.value)}
                    className="w-20 px-2 py-1 text-right font-mono text-sm font-bold bg-surface border border-border-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
                  />
                  <span className="text-xs font-mono text-secondary">
                    ({Math.round(weights.c2 * 100)}%)
                  </span>
                </div>
              </div>

              {/* Crips Mapping */}
              <div className="space-y-1.5">
                <span className="text-xs font-mono uppercase text-secondary tracking-wider font-semibold">
                  Klasifikasi Nilai Crips (v_i2):
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">1 Orang</span>
                    <span className="font-bold text-on-surface">Crips: 1</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">2 Orang</span>
                    <span className="font-bold text-on-surface">Crips: 2</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">3-4 Orang</span>
                    <span className="font-bold text-on-surface">Crips: 3</span>
                  </div>
                  <div className="p-2 bg-sky-50 rounded border border-sky-200">
                    <span className="text-sky-800 font-mono text-[11px] block">≥ 5 Orang</span>
                    <span className="font-bold text-sky-900">Crips: 4</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Card C3: Kondisi Tempat Tinggal (COST) - Corrected from .stitch */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-teal-600 text-white font-mono font-bold flex items-center justify-center text-sm">
                    C3
                  </span>
                  <div>
                    <h3 className="font-bold text-on-surface text-sm sm:text-base">
                      Kondisi Tempat Tinggal
                    </h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                        Tipe: COST
                      </span>
                      <span className="text-secondary">Kelayakan dinding, lantai, atap hunian</span>
                    </div>
                  </div>
                </div>

                {/* Weight Input & Slider */}
                <div className="flex items-center gap-2">
                  <label htmlFor="c3-weight" className="text-xs text-secondary font-medium">
                    Bobot C3:
                  </label>
                  <input
                    id="c3-weight"
                    aria-label="Bobot C3 (Tempat Tinggal)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    disabled={isLocked}
                    value={weights.c3}
                    onChange={(e) => handleWeightChange("c3", e.target.value)}
                    className="w-20 px-2 py-1 text-right font-mono text-sm font-bold bg-surface border border-border-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
                  />
                  <span className="text-xs font-mono text-secondary">
                    ({Math.round(weights.c3 * 100)}%)
                  </span>
                </div>
              </div>

              {/* Crips Mapping */}
              <div className="space-y-1.5">
                <span className="text-xs font-mono uppercase text-secondary tracking-wider font-semibold">
                  Klasifikasi Nilai Crips (v_i3):
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Rumah Permanen</span>
                    <span className="font-bold text-on-surface">Crips: 1</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Rumah Semi Permanen</span>
                    <span className="font-bold text-on-surface">Crips: 2</span>
                  </div>
                  <div className="p-2 bg-teal-50 rounded border border-teal-200">
                    <span className="text-teal-800 font-mono text-[11px] block">Rumah Tidak Layak Huni (RTLH)</span>
                    <span className="font-bold text-teal-900">Crips: 3</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Card C4: Kepemilikan Aset (COST) - Corrected from Daya Listrik in .stitch */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                <div className="flex items-center gap-2.5">
                  <span className="w-8 h-8 rounded-lg bg-slate-700 text-white font-mono font-bold flex items-center justify-center text-sm">
                    C4
                  </span>
                  <div>
                    <h3 className="font-bold text-on-surface text-sm sm:text-base">
                      Kepemilikan Aset
                    </h3>
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono font-semibold text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-100">
                        Tipe: COST
                      </span>
                      <span className="text-secondary">Kendaraan bermotor dan kepemilikan modal</span>
                    </div>
                  </div>
                </div>

                {/* Weight Input & Slider */}
                <div className="flex items-center gap-2">
                  <label htmlFor="c4-weight" className="text-xs text-secondary font-medium">
                    Bobot C4:
                  </label>
                  <input
                    id="c4-weight"
                    aria-label="Bobot C4 (Kepemilikan Aset)"
                    type="number"
                    step="0.01"
                    min="0"
                    max="1"
                    disabled={isLocked}
                    value={weights.c4}
                    onChange={(e) => handleWeightChange("c4", e.target.value)}
                    className="w-20 px-2 py-1 text-right font-mono text-sm font-bold bg-surface border border-border-subtle rounded-lg focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-60"
                  />
                  <span className="text-xs font-mono text-secondary">
                    ({Math.round(weights.c4 * 100)}%)
                  </span>
                </div>
              </div>

              {/* Crips Mapping */}
              <div className="space-y-1.5">
                <span className="text-xs font-mono uppercase text-secondary tracking-wider font-semibold">
                  Klasifikasi Nilai Crips (v_i4):
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Mobil Pribadi</span>
                    <span className="font-bold text-on-surface">Crips: 1</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Motor &gt; 1 Unit</span>
                    <span className="font-bold text-on-surface">Crips: 2</span>
                  </div>
                  <div className="p-2 bg-surface rounded border border-slate-100">
                    <span className="text-secondary font-mono text-[11px] block">Motor 1 Unit</span>
                    <span className="font-bold text-on-surface">Crips: 3</span>
                  </div>
                  <div className="p-2 bg-slate-100 rounded border border-slate-300">
                    <span className="text-slate-800 font-mono text-[11px] block">Sepeda / Tanpa Kendaraan</span>
                    <span className="font-bold text-slate-900">Crips: 4</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Formula & Snapshot Integrity Panel (4 Cols) */}
          <div className="xl:col-span-4 space-y-4">
            {/* Mathematical Formula Card */}
            <div className="bg-primary text-white rounded-xl p-5 shadow-xs space-y-3">
              <div className="flex items-center justify-between border-b border-primary-container pb-2">
                <span className="text-xs font-mono uppercase tracking-wider text-emerald-200 font-semibold">
                  Rumus Normalisasi SAW
                </span>
                <Sparkles className="w-4 h-4 text-emerald-200" />
              </div>

              <div className="space-y-2 text-xs text-emerald-100 font-mono">
                <div>
                  <span className="text-white font-bold block">1. Atribut Benefit:</span>
                  <code>r_ij = x_ij / max(x_j)</code>
                </div>
                <div>
                  <span className="text-white font-bold block">2. Atribut Cost:</span>
                  <code>r_ij = min(x_j) / x_ij</code>
                </div>
                <div>
                  <span className="text-white font-bold block">3. Preferensi Final:</span>
                  <code>V_i = Σ (w_j * r_ij)</code>
                </div>
              </div>
            </div>

            {/* Tie-Breaker Protocol Card */}
            <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-2 text-xs">
              <h4 className="font-bold text-on-surface text-sm">
                Protokol Hierarchical Tie-Breaker
              </h4>
              <p className="text-secondary leading-relaxed">
                Apabila terdapat nilai preferensi kembar di batas kuota alokasi, sistem mengeksekusi penyelesaian bertingkat secara deterministik:
              </p>
              <ol className="list-decimal pl-4 space-y-1 text-on-surface font-medium">
                <li>Nilai normalisasi r_i,C1 terbesar (Pendapatan)</li>
                <li>Nilai normalisasi r_i,C2 terbesar (Tanggungan)</li>
                <li>Jumlah tanggungan riil jiwa (real_dependents_count)</li>
                <li>Waktu pengusulan berkas paling awal (timestamp)</li>
              </ol>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default CriteriaManagementPage;
