# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

Sistem ini menggabungkan perhitungan matematis deterministik **Simple Additive Weighting (SAW)** + **Hierarchical Tie-Breaker** dengan **Google Gemini Flash API** sebagai *Explainer Layer* berbahasa Indonesia, serta pelindungan kriptografi **AES-256-GCM & HMAC-SHA256** sesuai **UU PDP No. 27 Tahun 2022**.

---

## Ringkasan Kapabilitas Utama

| Modul | Kebutuhan Bisnis & Alasan Desain (*Why*) | Referensi |
| :--- | :--- | :--- |
| **Manajemen Kriteria & Snapshot (`FR-01`)** | Mengunci bobot kriteria `C1–C4` (`total = 1.00`) ke tabel `BATCH_CRITERIA` saat kalkulasi dimulai agar perubahan bobot di periode berikutnya tidak merusak histori seleksi lama. | [ADR-003](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md) |
| **Filter Pra-Normalisasi TMS (`FR-02`)** | Mengecualikan warga Tidak Memenuhi Syarat (`ASN/TNI/Polri`, `PKH Ganda`, `Pindah`, `Meninggal`) sebelum mencari nilai `min/max` agar data ekstrem tidak mendistorsi matriks normalisasi SAW. | [ADR-003](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md) |
| **Engine SAW & Tie-Breaker (`FR-03`)** | Menghitung normalisasi `R_ij` dan skor preferensi `V_i` secara deterministik dengan resolusi skor kembar 4 tingkat (`C1 -> C2 -> Tanggungan Riil -> Timestamp`). | [ADR-001](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md) |
| **Zero-PII Async XAI & Fallback (`FR-04`, `FR-05`)** | Membangkitkan narasi penjelasan *counterfactual* via worker latar belakang tanpa mengirim identitas warga ke API eksternal, dilengkapi *fallback* berbasis aturan saat kuota API habis. | [ADR-001](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md), [ADR-004](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md) |
| **Portal Publik Anti-Bot (`FR-06`)** | Memungkinkan warga mengecek hasil seleksi tanpa registrasi akun menggunakan `16 digit NIK + 4 digit KK + CAPTCHA` dengan *rate-limit* 5 req/menit/IP dan *lockout* 15 menit per NIK. | [ADR-002](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md), [ADR-004](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md) |
| **Pelaporan Resmi & Evaluasi (`FR-07`, `FR-08`)** | Mencetak PDF Berita Acara berkode QR + lampiran warga TMS, serta menguji metrik ilmiah (*SAW Accuracy*, *Fidelity Score* `>= 95%`, *Hallucination Rate* `0%`, dan kuesioner SUS). | [PRD v3.0](./PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md) |
| **Antarmuka *Civic Precision* Responsif** | Mendukung tata letak adaptif pada **Mobile (`< 768px`)**, **Tablet (`768px–1023px`)**, dan **Desktop (`>= 1024px`)**. | [ADR-005](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md) |

---

## Quick Start

### Prasyarat
- Python 3.11+
- Node.js 20+ & npm
- Kunci API Google Gemini (`GEMINI_API_KEY` — opsional pada pengembangan lokal karena sistem menyediakan `deterministic_fallback.py`)

### 1. Menjalankan Backend (`Django 5 + DRF`)
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Salin konfigurasi environment lokal
Copy-Item .env.example .env

# Jalankan migrasi dan pengisian data awal
python manage.py migrate
python manage.py seed_initial_data

# Jalankan server REST API
python manage.py runserver
```

### 2. Menjalankan Frontend (`React + Vite + Tailwind CSS`)
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
| `pytest -v` | `backend/` | Menjalankan *unit & integration test* backend |
| `python manage.py qcluster` | `backend/` | Menjalankan *asynchronous worker* untuk pemrosesan *batch* XAI Gemini |
| `npm run dev` | `frontend/` | Menjalankan server pengembangan Vite di `http://localhost:5173` |
| `npm test -- --run` | `frontend/` | Menjalankan pengujian komponen & responsivitas UI dengan Vitest |
| `npm run build` | `frontend/` | Membangun *bundle* produksi frontend |

---

## Arsitektur & Architecture Decision Records (ADRs)

- **Spesifikasi Utama (PRD Final v3.0):** [`PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md`](./PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md)
- **Aturan Konteks Agen & Protokol UI (`.stitch`):** [`AGENTS.md`](./AGENTS.md)
- **Rencana Implementasi Bertahap:** [`docs/superpowers/plans/2026-10-13-sistem-bansos-saw-xai-implementation.md`](./docs/superpowers/plans/2026-10-13-sistem-bansos-saw-xai-implementation.md)

### Keputusan Arsitektur (`docs/decisions/`)
1. **[ADR-001](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md):** Arsitektur EDSS Hibrida — Komputasi Deterministik SAW dengan Layer XAI Gemini Flash Terkendali dan Fallback Berbasis Aturan.
2. **[ADR-002](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md):** Proteksi Kriptografi Dua Lapis untuk NIK (`AES-256-GCM` + `HMAC-SHA256`) dan Sanitasi Zero-PII ke API Eksternal.
3. **[ADR-003](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md):** Pembekuan Bobot Kriteria (`BATCH_CRITERIA`), Gerbang Pra-Normalisasi TMS, dan *Hierarchical Tie-Breaker*.
4. **[ADR-004](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md):** Antrean Worker Asinkron untuk Batch XAI dan Portal Publik Tanpa Akun dengan Proteksi Anti-Bot Dua Lapis.
5. **[ADR-005](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md):** Arsitektur UI Responsif 3-Tier (Mobile, Tablet, Desktop) dan Gerbang Review Desain `.stitch`.

---

## Catatan Penting (Known Gotchas)

- **Enkripsi NIK Wajib di Seluruh Jalur Simpan:** Selalu gunakan `Citizen.objects.create_or_update_with_nik(raw_nik=..., ...)` yang otomatis mengenkripsi `nik_encrypted`, menghitung `nik_hash`, dan membentuk `nik_masked`.
- **Gunakan Bobot Beku Setelah Kalkulasi:** Setelah batch mencapai status `Calculated`, seluruh modul hilir wajib membaca `BatchCriteria.frozen_weight`, bukan `Criteria.weight`.
- **Protokol Desain `.stitch`:** Setiap layar harus direview terlebih dahulu dan menggunakan `<AppShell />` responsif (Off-Canvas Drawer pada Mobile/Tablet, Fixed Sidebar pada Desktop).
