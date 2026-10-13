# ADR-003: Pembekuan Bobot Kriteria (`BATCH_CRITERIA`), Gerbang Pra-Normalisasi TMS, dan Hierarchical Tie-Breaker

## Status
Accepted

## Date
2026-10-13

## Context
Dalam operasional seleksi bantuan sosial lintas periode di kelurahan, terdapat tiga risiko integritas matematis:
1. **Perubahan Bobot Lintas Periode (Historical Drift):** Jika Kasi Kesos mengubah bobot master di tabel `CRITERIA` untuk periode baru, histori perhitungan dan metrik evaluasi (*Fidelity Score*) pada batch periode sebelumnya bisa ikut berubah atau menjadi tidak konsisten jika mengacu langsung ke tabel `CRITERIA`.
2. **Distorsi Nilai Ekstrem oleh Warga TMS:** Warga yang gugur secara administratif (Tidak Memenuhi Syarat / TMS: ASN/TNI/Polri, penerima PKH ganda, pindah domisili, atau meninggal dunia) sering memiliki nilai ekstrem (misalnya pendapatan sangat tinggi pada ASN). Jika warga TMS diikutsertakan dalam matriks normalisasi SAW, nilai $\min_i x_{ij}$ atau $\max_i x_{ij}$ akan terdistorsi dan merugikan kandidat yang memenuhi syarat.
3. **Skor Preferensi Kembar di Batas Kuota:** Karena input menggunakan skala diskrit Crips 1–5 pada 4 kriteria, peluang dua kandidat memperoleh nilai preferensi $V_i$ yang persis sama di perbatasan kuota (misal peringkat 30 dan 31 dari kuota 30) sangat tinggi.

## Decision
1. **Immutable Criteria Snapshot (`BATCH_CRITERIA`):**
   Saat `calculate_batch_saw(batch_id)` dijalankan (setelah validasi $\sum w_j = 1.00$), sistem menyalin (`upsert`) kode, nama, tipe atribut (`COST`/`BENEFIT`), dan bobot aktif ke tabel `BATCH_CRITERIA`. Seluruh perhitungan SAW, pembangkitan narasi XAI, dan evaluasi *Fidelity Score* untuk batch tersebut wajib membaca `BatchCriteria.frozen_weight`, bukan `Criteria.weight`.
2. **Pre-Normalization TMS Exclusion Gate:**
   Kandidat dengan `Evaluation.eligibility_status == "DISQUALIFIED"` dipisahkan sebelum pencarian $\min_i x_{ij}$ dan $\max_i x_{ij}$. Mereka diberi `SelectionResult(status="DISKUALIFIKASI_TMS", final_score_v=0.0000, ranking=None, explanation_source="INELIGIBLE_NOTICE")` sehingga tetap tercatat di lampiran Berita Acara tanpa memengaruhi normalisasi kandidat `ELIGIBLE`.
3. **4-Level Deterministic Hierarchical Tie-Breaker:**
   Kandidat `ELIGIBLE` diurutkan secara deterministik menggunakan *tuple key*:
   1. `final_score_v` terbesar ($V_i$),
   2. Nilai normalisasi $r_{i, C_1}$ (Pendapatan Keluarga) terbesar,
   3. Nilai normalisasi $r_{i, C_2}$ (Jumlah Tanggungan) terbesar,
   4. Nilai jumlah tanggungan riil (`Evaluation.real_dependents_count`) terbesar — membedakan keluarga di dalam kelas Crips 5 (`>= 5 orang`),
   5. Waktu pengusulan (`Evaluation.created_at`) paling awal (*first-in, first-served*), dilanjutkan `Evaluation.id` terkecil sebagai penentu mutlak terakhir.

## Alternatives Considered

### Alternatif 1: Menghapus Baris Warga TMS dari Database
- **Pros:** Tabel evaluasi hanya berisi warga yang dihitung SAW.
- **Cons:** Kelurahan kehilangan bukti audit mengapa warga tertentu tidak masuk daftar penerima, sehingga memicu sengketa warga.
- **Rejected:** PRD FR-02 dan FR-07 mewajibkan warga TMS tetap tercantum pada lampiran terpisah di Berita Acara resmi.

### Alternatif 2: Mengizinkan Semua Kandidat dengan Skor Kembar di Batas Kuota Lolos Bersama
- **Pros:** Tidak perlu aturan *tie-breaker*.
- **Cons:** Melanggar batas pagu anggaran kuota ($N$) kelurahan yang bersifat tetap.
- **Rejected:** Pagu kuota bansos bersifat mengikat; diperlukan *tie-breaker* transparan yang memprioritaskan kerentanan ekonomi ($C_1$) dan beban tanggungan ($C_2$).

## Consequences
- Hasil perhitungan SAW bersifat 100% *reproducible* dan kebal terhadap perubahan konfigurasi kriteria di masa mendatang.
- Setiap resolusi skor kembar tercatat secara eksplisit pada kolom `SelectionResult.tie_break_level` (`0=Normal, 1=C1, 2=C2, 3=Tanggungan, 4=Timestamp`) untuk ditampilkan pada Dashboard Staf dan Berita Acara.
