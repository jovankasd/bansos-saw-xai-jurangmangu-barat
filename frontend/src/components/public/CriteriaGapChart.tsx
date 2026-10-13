import React from "react";
import { CriterionGapItem } from "../../types/public";

interface CriteriaGapChartProps {
  items: CriterionGapItem[];
}

export const CriteriaGapChart: React.FC<CriteriaGapChartProps> = ({ items }) => {
  return (
    <div className="bg-surface-container-lowest rounded-xl shadow-sm p-4 sm:p-6 space-y-4 border border-border-subtle">
      <div className="flex items-center justify-between pb-2 border-b border-border-subtle">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-on-surface">
            Komparasi Gap Kriteria Terbobot
          </h3>
          <p className="text-xs text-secondary mt-0.5">
            Nilai normalisasi pemohon vs rerata penerima kuota (skala 0 - 100)
          </p>
        </div>
        <span className="font-mono text-xs px-2 py-0.5 bg-surface-subtle rounded text-primary font-semibold border border-border-subtle">
          C1 - C4
        </span>
      </div>

      <div className="space-y-4 pt-1">
        {items.map((item, idx) => {
          const pemohonVal = Math.round(item.skor_pemohon * 100);
          const rataRataVal = Math.round(item.rata_rata_lolos * 100);
          const delta = pemohonVal - rataRataVal;
          const isHigherOrEqual = delta >= 0;

          return (
            <div key={idx} className="space-y-1.5" data-testid={`gap-item-${idx}`}>
              <div className="flex justify-between items-center text-xs sm:text-sm">
                <span className="font-semibold text-on-surface">
                  {idx + 1}. {item.kriteria}
                </span>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded ${
                    isHigherOrEqual
                      ? "text-status-approved-fg bg-status-approved-bg"
                      : "text-status-review-fg bg-status-review-bg"
                  }`}
                >
                  {isHigherOrEqual
                    ? delta === 0
                      ? "Setara (+0 pt)"
                      : `Unggul (+${delta} pt)`
                    : `Selisih: ${delta} pt`}
                </span>
              </div>

              {/* Comparative Progress Bar */}
              <div className="w-full bg-surface-subtle h-4 rounded overflow-hidden flex relative">
                {/* User bar */}
                <div
                  className={`h-full flex items-center justify-end pr-1.5 text-[10px] text-white font-mono font-bold transition-all duration-500 ${
                    isHigherOrEqual ? "bg-emerald-600" : "bg-amber-500"
                  }`}
                  style={{ width: `${Math.max(pemohonVal, 6)}%` }}
                >
                  {pemohonVal}
                </div>

                {/* Benchmark Tick Indicator */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-primary z-10 shadow-sm"
                  style={{ left: `${Math.min(Math.max(rataRataVal, 0), 99)}%` }}
                  title={`Rerata Lolos: ${rataRataVal}`}
                />
              </div>

              <div className="flex justify-between font-mono text-[11px] text-secondary">
                <span>Skor Anda: {pemohonVal}</span>
                <span className="text-primary font-bold">Rerata Lolos: {rataRataVal}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Legend Guidance */}
      <div className="pt-2 border-t border-border-subtle flex flex-wrap items-center justify-between gap-2 text-xs text-secondary font-mono">
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 bg-amber-500 rounded-sm inline-block" />
          <span>Skor Pemohon</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-3 bg-primary rounded-sm inline-block" />
          <span>Garis Rerata Lolos</span>
        </div>
      </div>
    </div>
  );
};
