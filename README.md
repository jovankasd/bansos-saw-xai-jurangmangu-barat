# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

Sistem ini menggabungkan perhitungan matematis deterministik **Simple Additive Weighting (SAW)** + **Hierarchical Tie-Breaker** dengan **Google Gemini Flash API** sebagai *Explainer Layer* berbahasa Indonesia, dilengkapi pelindungan kriptografi **AES-256-GCM & HMAC-SHA256** sesuai **UU PDP No. 27 Tahun 2022**.

---

## Fitur Utama

1. **Manajemen Kriteria & Snapshot (`FR-01`):** Pengaturan bobot kriteria $C_1$–$C_4$ dengan validasi $\sum w_j = 1.00$ dan pembekuan bobot otomatis ke tabel `BATCH_CRITERIA` saat kalkulasi dimulai.
2. **Ingest Data RT & Gerbang Filter TMS (`FR-02`):** Input manual per individu dan *batch import* Excel (`.xlsx`) oleh Ketua RT, dilengkapi gerbang diskualifikasi administratif (Tidak Memenuhi Syarat / TMS: ASN/TNI/Polri, PKH Ganda, Pindah, Meninggal) agar tidak mendistorsi matriks normalisasi SAW.
3. **Engine SAW & Hierarchical Tie-Breaker (`FR-03`):** Perhitungan matriks normalisasi $R_{ij}$ dan preferensi $V_i$ yang 100% identik dengan hitungan manual Excel, disertai *tie-breaker* bertingkat ($C_1 \rightarrow C_2 \rightarrow \text{Tanggungan Riil} \rightarrow \text{Timestamp}$).
4. **Zero-PII Asynchronous XAI & Fallback Deterministik (`FR-04`, `FR-05`):** Pembangkitan narasi penjelasan *counterfactual* menggunakan Gemini Flash di latar belakang (*background worker*) tanpa mengirim data identitas warga (100% *PII-masked*), serta *fallback* otomatis berbasis aturan (`deterministic_fallback.py`) jika API mengalami *rate-limit* atau *offline*.
5. **Portal Publik Anti-Bot (`/cek-bansos` — `FR-06`):** Pengecekan mandiri oleh warga tanpa registrasi akun menggunakan 16 digit NIK + 4 digit terakhir No KK + CAPTCHA, dilindungi *rate limit* 5 req/menit/IP dan *lockout* 15 menit setelah 5 kegagalan per NIK.
6. **Pelaporan Resmi & Modul Evaluasi Skripsi (`FR-07`, `FR-08`):** Cetak PDF Berita Acara berkode QR + lampiran warga TMS, serta dasbor pengujian ilmiah (*SAW Accuracy*, *Fidelity Score* $\ge 95\%$, *Hallucination Rate* $0\%$, dan ekspor kuesioner SUS).
7. **Desain Responsif 3 Ukuran Layar (*Civic Precision*):** Fleksibel dibuka di **Handphone/Mobile (`< 768px`)**, **Tablet (`768px–1023px`)**, dan **Browser/Desktop (`>= 1024px`)**.

---

## Quick Start

### Prasyarat
- Python 3.11+
- Node.js 20+ & npm
- Kunci API Google Gemini (`GEMINI_API_KEY` — opsional saat pengembangan karena sistem memiliki `deterministic_fallback.py`)

### 1. Setup Backend (Django 5 + DRF)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Salin konfigurasi environment (.env)
Copy-Item .env.example .env

# Jalankan migrasi dan pengisian data awal (C1-C4, Crips 1-5, akun demo staf)
python manage.py migrate
python manage.py seed_initial_data

# Jalankan server pengembangan backend
python manage.py runserver
```

### 2. Setup Frontend (React + Vite + Tailwind CSS)
```powershell
cd frontend
npm install
npm run dev
```

---

## Daftar Perintah (Commands)

| Perintah | Direktori | Deskripsi |
| :--- | :--- | :--- |
| `python manage.py runserver` | `backend/` | Menjalankan server REST API Django di `http://localhost:8000` |
| `pytest -v` | `backend/` | Menjalankan seluruh *unit & integration test* backend (Kriptografi, SAW, Tie-Breaker, XAI, API) |
| `python manage.py qcluster` | `backend/` | Menjalankan *asynchronous task worker* untuk pemrosesan *batch* XAI Gemini |
| `npm run dev` | `frontend/` | Menjalankan server pengembangan Vite di `http://localhost:5173` |
| `npm test -- --run` | `frontend/` | Menjalankan pengujian komponen & responsivitas UI dengan Vitest |
| `npm run build` | `frontend/` | Membangun *bundle* produksi frontend |

---

## Arsitektur & Dokumen Keputusan Arsitektur (ADRs)

Dokumentasi spesifikasi dan alasan di balik keputusan teknis utama tersimpan di:
- **Spesifikasi Utama (PRD Final v3.0):** [PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md)
- **Aturan Konteks Agen & Protokol Desain (`.stitch`):** [AGENTS.md](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/AGENTS.md)
- **Rencana Implementasi Langkah demi Langkah:** [2026-10-13-sistem-bansos-saw-xai-implementation.md](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/superpowers/plans/2026-10-13-sistem-bansos-saw-xai-implementation.md)

### Daftar Architecture Decision Records (`docs/decisions/`)
1. **[ADR-001](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md):** Arsitektur EDSS Hibrida — Komputasi Deterministik SAW dengan Layer XAI Gemini Flash Terkendali dan Fallback Berbasis Aturan.
2. **[ADR-002](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md):** Proteksi Kriptografi Dua Lapis untuk NIK (`AES-256-GCM` + `HMAC-SHA256`) dan Sanitasi Zero-PII ke API Eksternal.
3. **[ADR-003](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md):** Pembekuan Bobot Kriteria (`BATCH_CRITERIA`), Gerbang Pra-Normalisasi TMS, dan *Hierarchical Tie-Breaker*.
4. **[ADR-004](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md):** Antrean Worker Asinkron untuk Batch XAI dan Portal Publik Tanpa Akun dengan Proteksi Anti-Bot Dua Lapis.
5. **[ADR-005](file:///d:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md):** Arsitektur UI Responsif 3-Tier (Mobile, Tablet, Desktop) dan Gerbang Review Desain `.stitch`.

---

## Catatan Penting (Known Gotchas)

- **Jangan Pernah Menyimpan NIK Plaintext:** Gunakan `Citizen.objects.create_with_nik(raw_nik=..., ...)` yang otomatis mengisi `nik_hash`, `nik_encrypted`, dan `nik_masked`.
- **Jangan Membaca `Criteria.weight` Setelah Batch Dihitung:** Setelah status batch mencapai `Calculated`, seluruh modul (termasuk XAI dan kalkulator *Fidelity Score*) **wajib** membaca `BatchCriteria.frozen_weight` milik batch tersebut.
- **Jangan Menyalin Mentah HTML `.stitch`:** Selalu lakukan review desain bersama pengguna dan gunakan `<AppShell />` responsif (Off-Canvas Drawer untuk Mobile/Tablet, Fixed Sidebar untuk Desktop).
