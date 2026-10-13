import React, { useState } from "react";
import {
  Table,
  Calculator,
  Eye,
  Brain,
  Scissors,
  Filter,
} from "lucide-react";
import { AppShell } from "../../components/layout/AppShell";
import { useAuth } from "../../context/AuthContext";

export const SawRankingPage: React.FC = () => {
  const { user } = useAuth();
  const [filterRt, setFilterRt] = useState("ALL");
  const [selectedKpmId, setSelectedKpmId] = useState("KPM-001");

  // Mock candidates data (calculated by SAW engine)
  const candidates = [
    {
      id: "KPM-001",
      rank: 1,
      name: "Budi Santoso",
      nik: "367403******0012",
      rt: "RT 03/RW 02",
      r1: 0.965,
      r2: 0.920,
      r3: 0.950,
      r4: 0.930,
      vi: 0.942,
      status: "LOLOS",
      tieBreak: "-",
    },
    {
      id: "KPM-002",
      rank: 2,
      name: "Ibu Warsini",
      nik: "367403******1198",
      rt: "RT 01/RW 04",
      r1: 0.950,
      r2: 0.910,
      r3: 0.930,
      r4: 0.940,
      vi: 0.9345,
      status: "LOLOS",
      tieBreak: "-",
    },
    {
      id: "KPM-003",
      rank: 3,
      name: "Supriatna Jaya",
      nik: "367403******2234",
      rt: "RT 06/RW 03",
      r1: 0.920,
      r2: 0.940,
      r3: 0.910,
      r4: 0.920,
      vi: 0.9225,
      status: "LOLOS",
      tieBreak: "-",
    },
    {
      id: "KPM-029",
      rank: 29,
      name: "Hj. Maisaroh",
      nik: "367403******8712",
      rt: "RT 02/RW 01",
      r1: 0.740,
      r2: 0.730,
      r3: 0.720,
      r4: 0.730,
      vi: 0.7305,
      status: "LOLOS",
      tieBreak: "-",
    },
    {
      id: "KPM-030",
      rank: 30,
      name: "Karno Supriyadi",
      nik: "367403******9901",
      rt: "RT 04/RW 01",
      r1: 0.730,
      r2: 0.720,
      r3: 0.715,
      r4: 0.735,
      vi: 0.725,
      status: "LOLOS",
      tieBreak: "Tie-Breaker L1 (r_C1)",
      isCutoffBorder: true,
    },
    // The cutoff candidate who tied but lost tie-breaker
    {
      id: "KPM-031",
      rank: 31,
      name: "M. Syahrul Hidayat",
      nik: "367403******1287",
      rt: "RT 07/RW 02",
      r1: 0.720,
      r2: 0.710,
      r3: 0.725,
      r4: 0.730,
      vi: 0.7212,
      status: "TIDAK_LOLOS",
      tieBreak: "Kandidat Cadangan",
    },
    {
      id: "KPM-032",
      rank: 32,
      name: "Wawan Hermawan",
      nik: "367403******4421",
      rt: "RT 09/RW 05",
      r1: 0.710,
      r2: 0.700,
      r3: 0.710,
      r4: 0.720,
      vi: 0.7100,
      status: "TIDAK_LOLOS",
      tieBreak: "-",
    },
  ];

  const selectedCandidate =
    candidates.find((c) => c.id === selectedKpmId) || candidates[0];

  const weights = { c1: 0.30, c2: 0.25, c3: 0.25, c4: 0.20 };

  return (
    <AppShell
      title="Dossier & Seleksi SAW Ranking KPM"
      breadcrumb={["Kalkulasi SAW", "Hasil Perankingan", "Batch Aktif"]}
    >
      <div className="space-y-6">
        {/* Top Operational Status Header */}
        <div className="bg-white rounded-xl p-5 border border-border-subtle shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-xs font-semibold px-2.5 py-0.5 rounded bg-primary-container text-white uppercase tracking-wider">
                FR-03 & FR-07 Engine
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                Hierarchical Tie-Breaker Aktif
              </span>
            </div>
            <h2 className="text-lg sm:text-xl font-bold text-on-surface">
              Hasil Komputasi Simple Additive Weighting & Peringkat Objektif
            </h2>
            <p className="text-xs sm:text-sm text-on-surface-variant">
              Matriks normalisasi $R_{`{ij}`} dikalikan bobot preferensi $W_{`j`} menghasilkan nilai preferensi final $V_i$. Skor kembar diselesaikan secara deterministik.
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            {/* Show calculate button only for ADMIN, hidden for Lurah / Viewer */}
            {user?.role !== "VIEWER" && (
              <button className="flex items-center gap-1.5 px-4 py-2 text-xs sm:text-sm font-semibold bg-primary hover:bg-primary-container text-white rounded-lg transition-colors shadow-xs">
                <Calculator className="w-4 h-4" />
                <span>Hitung Ulang SAW</span>
              </button>
            )}
          </div>
        </div>

        {/* Master Detail Grid: 11-Column Table (8 Cols on XL) vs Decomposed Matrix Inspector (4 Cols on XL) */}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* Left Column: SAW Ranking High-Density Compute Table (8 cols on XL, full width on Mobile/Tablet) */}
          <div className="xl:col-span-8 bg-white rounded-xl border border-border-subtle shadow-xs overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Table className="w-4 h-4 text-primary" />
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Matriks Perankingan KPM Terverifikasi
                </h3>
              </div>

              <div className="flex items-center gap-2">
                <Filter className="w-3.5 h-3.5 text-secondary" />
                <select
                  aria-label="Filter RT"
                  value={filterRt}
                  onChange={(e) => setFilterRt(e.target.value)}
                  className="px-2.5 py-1 text-xs bg-surface border border-border-subtle rounded-lg text-on-surface"
                >
                  <option value="ALL">Semua Wilayah RT</option>
                  <option value="RT 01">RT 01</option>
                  <option value="RT 02">RT 02</option>
                  <option value="RT 03">RT 03</option>
                  <option value="RT 04">RT 04</option>
                </select>
              </div>
            </div>

            {/* Responsive Table Wrapper with Horizontal Scroll and Sticky Identity Column */}
            <div className="overflow-x-auto custom-scroll">
              <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[780px]">
                <thead>
                  <tr className="bg-surface font-mono text-[11px] text-secondary uppercase tracking-wider border-b border-border-subtle">
                    <th className="py-2.5 px-3 text-center w-10 sticky left-0 bg-surface z-10 shadow-[2px_0_4px_rgba(0,0,0,0.04)]">
                      #
                    </th>
                    <th className="py-2.5 px-3 sticky left-10 bg-surface z-10 shadow-[2px_0_4px_rgba(0,0,0,0.04)] min-w-[150px]">
                      KPM / Identitas
                    </th>
                    <th className="py-2.5 px-2 text-center">RT/RW</th>
                    <th className="py-2.5 px-2 text-right" title="Cost: Bobot 30%">
                      C1 (Pendapatan)
                    </th>
                    <th className="py-2.5 px-2 text-right" title="Benefit: Bobot 25%">
                      C2 (Tanggungan)
                    </th>
                    <th className="py-2.5 px-2 text-right" title="Cost: Bobot 25%">
                      C3 (Rumah)
                    </th>
                    <th className="py-2.5 px-2 text-right" title="Cost: Bobot 20%">
                      C4 (Aset)
                    </th>
                    <th className="py-2.5 px-3 text-right font-bold text-on-surface">
                      Preferensi (V_i)
                    </th>
                    <th className="py-2.5 px-2 text-center">Status</th>
                    <th className="py-2.5 px-2 text-center">Tie-Breaker</th>
                    <th className="py-2.5 px-2 text-center w-16">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {candidates.map((kpm) => {
                    const isSelected = kpm.id === selectedKpmId;
                    const isCutoffPoint = kpm.isCutoffBorder;

                    return (
                      <React.Fragment key={kpm.id}>
                        <tr
                          onClick={() => setSelectedKpmId(kpm.id)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? "bg-emerald-50/70"
                              : "hover:bg-slate-50"
                          } ${kpm.status === "LOLOS" ? "" : "opacity-80"}`}
                        >
                          {/* Sticky Rank # */}
                          <td className={`py-2.5 px-3 text-center font-mono font-bold sticky left-0 z-10 shadow-[2px_0_4px_rgba(0,0,0,0.04)] ${
                            isSelected ? "bg-emerald-50 text-emerald-900" : "bg-white text-primary"
                          }`}>
                            {kpm.rank}
                          </td>

                          {/* Sticky Identity */}
                          <td className={`py-2.5 px-3 sticky left-10 z-10 shadow-[2px_0_4px_rgba(0,0,0,0.04)] ${
                            isSelected ? "bg-emerald-50" : "bg-white"
                          }`}>
                            <div className="flex flex-col">
                              <span className="font-bold text-on-surface text-xs sm:text-sm">
                                {kpm.name}
                              </span>
                              <span className="font-mono text-[10px] text-secondary">
                                {kpm.nik}
                              </span>
                            </div>
                          </td>

                          <td className="py-2.5 px-2 text-center font-mono text-[11px] text-secondary">
                            {kpm.rt}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs">
                            {kpm.r1.toFixed(4)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs">
                            {kpm.r2.toFixed(4)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs">
                            {kpm.r3.toFixed(4)}
                          </td>
                          <td className="py-2.5 px-2 text-right font-mono text-xs">
                            {kpm.r4.toFixed(4)}
                          </td>

                          <td className="py-2.5 px-3 text-right font-mono font-bold text-xs sm:text-sm text-emerald-800">
                            {kpm.vi.toFixed(4)}
                          </td>

                          <td className="py-2.5 px-2 text-center">
                            {kpm.status === "LOLOS" ? (
                              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 font-mono text-[10px] font-bold">
                                Lolos Kuota
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-mono text-[10px] font-semibold">
                                Cadangan
                              </span>
                            )}
                          </td>

                          <td className="py-2.5 px-2 text-center font-mono text-[10px] text-secondary">
                            {kpm.tieBreak}
                          </td>

                          <td className="py-2.5 px-2 text-center">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedKpmId(kpm.id);
                              }}
                              className="p-1 rounded text-secondary hover:text-primary hover:bg-slate-100"
                              title="Tinjau Dekomposisi Matriks"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>

                        {/* Visual Cutoff Divider between rank 30 and 31 */}
                        {isCutoffPoint && (
                          <tr>
                            <td colSpan={11} className="p-0 border-none">
                              <div className="bg-primary text-white px-4 py-2 flex items-center justify-between text-xs shadow-inner">
                                <div className="flex items-center gap-2">
                                  <Scissors className="w-4 h-4 text-emerald-300" />
                                  <span className="font-mono font-bold tracking-wider">
                                    Batas Kuota Seleksi: 30 Penerima (Ambang Batas V_i = 0.7250)
                                  </span>
                                </div>
                                <span className="text-[11px] text-emerald-200 hidden sm:inline">
                                  Kandidat di bawah garis batas masuk antrean Cadangan
                                </span>
                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="p-3 bg-surface border-t border-border-subtle flex items-center justify-between text-xs text-secondary font-mono">
              <span>Menampilkan kandidat teratas hingga ambang batas kuota.</span>
              <span>Total Alokasi: 30 KPM</span>
            </div>
          </div>

          {/* Right Column: Decomposed Matrix Transparency Inspector (4 cols on XL) */}
          <div className="xl:col-span-4 bg-white rounded-xl p-5 border border-border-subtle shadow-xs space-y-4">
            <div className="border-b border-border-subtle pb-3 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-on-surface text-sm sm:text-base">
                  Detail Matriks Normalisasi (R_ij)
                </h3>
                <span className="text-xs text-secondary font-mono">
                  Dekomposisi Skor KPM: {selectedCandidate.id}
                </span>
              </div>
              <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800">
                <Brain className="w-4 h-4" />
              </span>
            </div>

            <div className="space-y-1">
              <div className="text-base font-bold text-on-surface">
                {selectedCandidate.name}
              </div>
              <div className="text-xs font-mono text-secondary">
                NIK Terverifikasi: {selectedCandidate.nik} • {selectedCandidate.rt}
              </div>
              <div className="flex items-center gap-2 pt-1">
                <span className="text-xs text-secondary">Skor Akhir (V_i):</span>
                <span className="font-mono text-base font-bold text-emerald-800">
                  {selectedCandidate.vi.toFixed(4)}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 font-bold border border-emerald-200">
                  Peringkat #{selectedCandidate.rank}
                </span>
              </div>
            </div>

            {/* Decomposed Breakdown per Criteria */}
            <div className="space-y-3 pt-2">
              <span className="text-xs font-mono uppercase text-secondary font-semibold tracking-wider block">
                Dekomposisi Bobot Terkalkulasi:
              </span>

              {/* C1 */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between font-mono">
                  <span className="font-medium text-on-surface">C1: Pendapatan (w = 30%)</span>
                  <span className="font-bold text-emerald-800">
                    r_i1 = {selectedCandidate.r1.toFixed(4)} (w: {(selectedCandidate.r1 * weights.c1).toFixed(4)})
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-900 h-full rounded-full"
                    style={{ width: `${selectedCandidate.r1 * 100}%` }}
                  />
                </div>
              </div>

              {/* C2 */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between font-mono">
                  <span className="font-medium text-on-surface">C2: Tanggungan (w = 25%)</span>
                  <span className="font-bold text-sky-800">
                    r_i2 = {selectedCandidate.r2.toFixed(4)} (w: {(selectedCandidate.r2 * weights.c2).toFixed(4)})
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-sky-600 h-full rounded-full"
                    style={{ width: `${selectedCandidate.r2 * 100}%` }}
                  />
                </div>
              </div>

              {/* C3 */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between font-mono">
                  <span className="font-medium text-on-surface">C3: Rumah (w = 25%)</span>
                  <span className="font-bold text-teal-800">
                    r_i3 = {selectedCandidate.r3.toFixed(4)} (w: {(selectedCandidate.r3 * weights.c3).toFixed(4)})
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-teal-600 h-full rounded-full"
                    style={{ width: `${selectedCandidate.r3 * 100}%` }}
                  />
                </div>
              </div>

              {/* C4 */}
              <div className="space-y-1 text-xs">
                <div className="flex justify-between font-mono">
                  <span className="font-medium text-on-surface">C4: Aset (w = 20%)</span>
                  <span className="font-bold text-slate-800">
                    r_i4 = {selectedCandidate.r4.toFixed(4)} (w: {(selectedCandidate.r4 * weights.c4).toFixed(4)})
                  </span>
                </div>
                <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-slate-700 h-full rounded-full"
                    style={{ width: `${selectedCandidate.r4 * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="p-3 bg-surface rounded-lg border border-slate-100 text-xs text-secondary leading-relaxed">
              Nilai $V_i = \sum w_j \cdot r_{`{ij}`} merupakan dasar transparansi keputusan yang disajikan kepada warga di portal publik serta diuji petik oleh Lurah sebelum pengesahan.
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default SawRankingPage;
