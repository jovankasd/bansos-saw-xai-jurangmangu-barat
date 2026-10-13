# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m4b-public-portal` (Fase 7 / Task 7 — Public Citizen Portal `/cek-bansos`, Masking PII, CriteriaGapChart C1..C4, & Staff Login `/admin/login` - Milestone 4B)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 7 mengimplementasikan portal transparansi publik bagi warga pemohon bansos (`/cek-bansos`) serta gerbang masuk staf adjudikasi (`/admin/login`) dengan mematuhi prinsip akuntabilitas terbuka, keamanan data kependudukan (**UU PDP No. 27/2022**), dan arahan rancangan **Civic Precision**:

1. **Akses Mandiri Passwordless untuk Warga (PRD Bagian 12.1):**
   - Warga tidak dibebani akun pendaftaran, kata sandi, atau verifikasi email yang berpotensi menyulitkan warga lansia. Verifikasi dilakukan secara mandiri menggunakan kombinasi 16 digit NIK + 4 digit terakhir nomor KK + CAPTCHA Cloudflare Turnstile.
2. **Perlindungan Privasi Berlapis & Zero-PII Display:**
   - Seluruh identitas warga yang ditampilkan di layar publik wajib disamarkan secara visual: NIK disamarkan menjadi `367403******0002` dan nama kepala keluarga menjadi `Ahmad S******`.
   - Hanya batch seleksi yang telah disahkan Lurah dan berstatus `Published` yang dapat diakses oleh publik. Permintaan status terhadap batch sebelum publikasi menghasilkan respons `404 Not Found` guna mencegah kebocoran ranking prematur.
3. **Koreksi Deviasi Prototipe `.stitch` (Review Desain #2 & AGENTS.md Bagian 2):**
   - **Penghapusan Form Sanggahan Dua Arah (PRD Bagian 12.2):** Prototipe mentah `.stitch` memuat form sanggahan dan pengaduan anonim interaktif di portal publik. Sesuai batasan sistem resmi (*Not Doing*), form tersebut dihapus total dan digantikan oleh *Kartu Edukasi Prosedur Advokasi Offline ke Ketua RT* untuk pemutakhiran data pada periode DTKS berikutnya.
   - **Penyeragaman Kriteria $C_1$–$C_4$:** Mengoreksi teks kriteria ke-4 pada prototipe mentah ("Daya Listrik 900 VA") menjadi kriteria resmi **"Kepemilikan Aset"** ($C_4$, `COST`, Bobot 20%).
   - **Tautan Unduh PDF Resmi Ber-Token:** Tombol unduh lembar hasil transparansi dihubungkan langsung ke endpoint bertanda tangan kriptografis (`/api/public/result-pdf/?token=${download_token}`) dengan QR Code verifikasi keabsahan.
4. **Visualisasi Kesenjangan Kriteria Terbobot (`CriteriaGapChart.tsx`):**
   - Menghadirkan bilah perbandingan horizontal yang intuitif bagi warga awam: membandingkan capaian nilai normalisasi pemohon ($r_{ij} \times 100$) terhadap rata-rata capaian keluarga yang berhasil lolos kuota ($\bar{r}_j^{\text{lolos}} \times 100$) lengkap dengan selisih poin ($\Delta$).
5. **Autentikasi Staf Berbasis Peran (`LoginPage.tsx`):**
   - Gerbang masuk staf kelurahan (Kasi Kesos / Super Admin, Surveyor RT, dan Lurah / Viewer) menggunakan SimpleJWT, penyimpanan token aman di context dan localStorage, serta pengalihan rute otomatis sesuai hak akses.

---

### Changelog Fase 7 (Task 7)

#### Added
- **Komponen Visualisasi Publik:**
  - [`frontend/src/components/public/CriteriaGapChart.tsx`](./frontend/src/components/public/CriteriaGapChart.tsx): Modul grafik perbandingan kesenjangan kriteria $C_1$ s/d $C_4$ dengan progress bar komparatif (skor pemohon vs garis batas benchmark rata-rata penerima lolos), indikator selisih poin ($\Delta$), serta legenda terkalibrasi.
- **Halaman Portal Publik Warga:**
  - [`frontend/src/pages/PublicPortalPage.tsx`](./frontend/src/pages/PublicPortalPage.tsx): Antarmuka pencarian mandiri status KPM dengan formulir verifikasi 16 digit NIK + 4 digit KK, simulasi widget CAPTCHA, kartu dossier keputusan (LOLOS, TIDAK_LOLOS, DISKUALIFIKASI_TMS), 4 bagian narasi transparansi XAI (Ringkasan, Counterfactual, Pernyataan Sikap, Rekomendasi), jadwal zonasi resmi penyaluran per RW, dan kartu advokasi offline RT.
- **Halaman Login Staf Kelurahan:**
  - [`frontend/src/pages/LoginPage.tsx`](./frontend/src/pages/LoginPage.tsx): Antarmuka masuk staf bernuansa *Civic Card Shield*, input username dan password dengan fitur show/hide, penanganan error 401/403/429, serta integrasi role-based redirect ke `/admin/dashboard`, `/admin/surveyor`, atau `/admin/approval`.
- **Tipe Data Kontrak Publik:**
  - [`frontend/src/types/public.ts`](./frontend/src/types/public.ts): Definisi antarmuka TypeScript untuk `CriterionGapItem`, `ExplanationData`, `ApplicantMasked`, `SelectionResultPublic`, dan `PublicCheckStatusResponse`.
- **Suite Pengujian TDD:**
  - [`frontend/src/__tests__/PublicPortalPage.test.tsx`](./frontend/src/__tests__/PublicPortalPage.test.tsx): 6 skenario pengujian komprehensif memvalidasi formulir verifikasi, kepatuhan batas "Not Doing" (ketiadaan form sanggahan dua arah), rendering dossier hasil dengan penyamaran PII, penanganan ragam status (LOLOS vs TIDAK_LOLOS), penanganan error keamanan (403, 429 lockout, 404), serta alur login staf.

#### Security
- **Perlindungan Anti-Enumerasi & PII Masking:**
  - Nama dan NIK selalu ditampilkan dalam format masking (`Ahmad S******` & `367403******0002`).
  - Respons 404 generik mencegah penyerang memetakan keberadaan NIK warga jika batch belum dipublikasikan atau nomor KK tidak cocok.
- **Penanganan Lockout & Rate Limit:**
  - Notifikasi antarmuka terstandarisasi saat IP melampaui 5 permintaan/menit atau NIK dikunci selama 15 menit akibat 5 kali kegagalan verifikasi nomor KK beruntun.
- **Signed Download Token:**
  - Tombol unduh lembar ketetapan PDF menggunakan token bertanda tangan `TimestampSigner`, mencegah pengunduhan acak tanpa otorisasi.

#### Changed
- **Pembaruan Rute Aplikasi ([`frontend/src/App.tsx`](./frontend/src/App.tsx)):**
  - Mendaftarkan rute publik `/` dan `/cek-bansos` ke `<PublicPortalPage />`.
  - Mendaftarkan rute otentikasi `/admin/login` ke `<LoginPage />`.
- **Koreksi Deviasi Desain `.stitch`:**
  - Menghapus komponen textarea dan tombol "Kirim Sanggahan Resmi" dari portal warga.
  - Memperbarui label kriteria ke-4 menjadi "Kepemilikan Aset" ($C_4$).

---

### Arsitektur Alur Verifikasi Portal Publik & Proteksi Berlapis

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                   ALUR VERIFIKASI WARGA (/cek-bansos)                  │
  └────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
        Input: [ NIK 16 Digit ] + [ 4 Digit KK ] + [ CAPTCHA Turnstile ]
                                     │
                                     ▼
                 POST /api/public/check-status/
                                     │
           ┌─────────────────────────┴─────────────────────────┐
           │                                                   │
     [ HTTP 403 / 429 ]                                  [ HTTP 200 OK ]
           │                                                   │
  - Gagal CAPTCHA                                     - Batch Status: "Published"
  - Rate limit (5 req/menit)                          - NIK Digest Valid & KK Cocok
  - Lockout 15 menit (5x fail)                        - Reset Counter Kegagalan NIK
           │                                                   │
           ▼                                                   ▼
  [ Alert Merah Informatif ]                          [ DOSSIER TRANSPARANSI ]
                                                      - NIK Masked: 367403******0002
                                                      - Nama Masked: Ahmad S******
                                                      - Status: LOLOS / TIDAK_LOLOS / TMS
                                                      - Skor Vi vs Ambang Cutoff
                                                      - 4 Bagian Narasi XAI Gemini
                                                      - CriteriaGapChart (C1..C4)
                                                      - Unduh PDF Resmi (Signed Token)
                                                      - Prosedur Pelaporan Offline ke RT
```

---

### Daftar File Fase 7

| File | Tanggung Jawab |
| :--- | :--- |
| [`./frontend/src/types/public.ts`](./frontend/src/types/public.ts) | Definisi kontrak tipe TypeScript untuk respons status publik dan grafik komparasi |
| [`./frontend/src/components/public/CriteriaGapChart.tsx`](./frontend/src/components/public/CriteriaGapChart.tsx) | Komponen grafik gap horizontal kriteria $C_1$–$C_4$ dengan penanda benchmark rata-rata |
| [`./frontend/src/pages/PublicPortalPage.tsx`](./frontend/src/pages/PublicPortalPage.tsx) | Halaman portal transparansi bansos warga dengan formulir verifikasi dan dossier hasil |
| [`./frontend/src/pages/LoginPage.tsx`](./frontend/src/pages/LoginPage.tsx) | Halaman autentikasi staf kelurahan (SimpleJWT) dengan pengalihan peran |
| [`./frontend/src/App.tsx`](./frontend/src/App.tsx) | Konfigurasi rute aplikasi React Router untuk portal publik dan panel admin |
| [`./frontend/src/__tests__/PublicPortalPage.test.tsx`](./frontend/src/__tests__/PublicPortalPage.test.tsx) | Suite pengujian TDD Vitest untuk alur portal publik dan login staf |

---

### Hasil Verifikasi Test

```text
$ npm --prefix frontend test -- --run

 RUN  v2.1.9 D:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/frontend

 ✓ src/__tests__/AppShell.responsive.test.tsx (4 tests) 386ms
   ✓ toggles mobile drawer via hamburger button and closes via backdrop
   ✓ enforces RBAC: hides mutation actions from Viewer (Lurah) and displays approval menu
   ✓ enforces RBAC: allows Super Admin to see all governance modules including SAW execution and weight config
   ✓ enforces RBAC: scopes Surveyor (Ketua RT) strictly to RT operations

 ✓ src/__tests__/PublicPortalPage.test.tsx (6 tests) 436ms
   ✓ renders NIK + 4-digit KK + CAPTCHA verification form and excludes prohibited two-way appeal form
   ✓ submits verification and renders full dossier with masked PII, 4-part XAI narrative, and C1..C4 gap chart
   ✓ renders LOLOS status correctly with approval badge
   ✓ handles lockout and error scenarios (403, 429, 404)
   ✓ renders login form and authenticates staff successfully
   ✓ displays error banner on authentication failure

 Test Files  2 passed (2)
      Tests  10 passed (10)
   Start at  17:53:31
   Duration  2.12s

# Verifikasi Kompilasi TypeScript & Build Produksi Vite:
$ npm --prefix frontend run build

vite v6.4.4 building for production...
transforming...
✓ 1644 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.99 kB │ gzip:  0.55 kB
dist/assets/index-BLoSdA0E.css   25.48 kB │ gzip:  5.30 kB
dist/assets/index-DN_S2L_Z.js   276.13 kB │ gzip: 87.56 kB
✓ built in 2.38s
```

---

## Dokumentasi Branch Sebelumnya

<details>
<summary><strong>Fase 6: feat/m4a-frontend-appshell (Frontend Scaffolding, Civic Precision Theme, & 3-Tier Responsive AppShell - Milestone 4A)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 6 merealisasikan fondasi antarmuka pengguna web (*User Interface Scaffolding & Responsive Shell*) sesuai amanat PRD Bagian 3 & 12, AGENTS.md Bagian 2, dan ADR-005:
- Penerapan tema desain *Civic Precision* (React 18, Vite 6, Tailwind CSS, `#003426` Emerald Civic, font `Hanken Grotesk` & `JetBrains Mono`).
- Penegakan tata letak responsif 3-Tier (`<AppShell />`): Off-Canvas Drawer pada Handphone (`< 768px`) dan Tablet (`768px - 1023px`), serta Sidebar tetap (`lg:w-64`) pada Desktop (`>= 1024px`).
- Penegakan Role-Based Access Control (RBAC) pada menu navigasi: tombol mutasi SAW disembunyikan untuk Lurah (`VIEWER`) dan Surveyor RT.
- Perbaikan bug *clipping* pada header Topbar dan eliminasi tombol ilegal *"Sinkronisasi DTKS"*.

</details>

<details>
<summary><strong>Fase 5: feat/m5-pdf-reporting (PDF Berita Acara Generator with QR & TMS Appendix & Thesis Evaluation Metrics)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 5 merealisasikan lapisan pelaporan resmi (*Official Reporting Layer*) dan instrumen pengujian skripsi (*Academic Evaluation Instruments*) sesuai PRD Bagian 1, 10, dan 11, serta ADR-002 dan ADR-006:
- Berita Acara resmi berkekuatan hukum dengan Kop Surat Pemkot Tangerang Selatan, tabel penetapan penerima, tanda tangan Lurah & Kasi Kesos, lampiran terpisah warga TMS (`DISQUALIFIED`), dan QR Code validasi keaslian.
- Dekripsi terkontrol NIK (`nik_encrypted` AES-256-GCM) dengan pencatatan otomatis ke `AuditLog` (`action=NIK_DECRYPT`).
- Lembar pengumuman kelayakan mandiri publik zero-PII dengan penyamaran visual 100% dan token unduhan bertanda tangan kriptografis.
- Perhitungan metrik evaluasi skripsi otomatis: *Fidelity Score* ($\ge 95\%$), *Hallucination Rate* ($0\%$), kuesioner baku SUS Indonesia, dan ekspor dataset multi-sheet ke format Excel (`.xlsx`).

</details>

<details>
<summary><strong>Fase 4: feat/m4-api-responsive-ui (REST API Endpoints, RBAC Guards, Excel Ingest/Export, & Public Portal Shield)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 4 menghubungkan inti komputasi dengan antarmuka web melalui REST API standar Django REST Framework (DRF):
- Role-Based Access Control (RBAC) ketat: Super Admin (Kasi Kesos), Surveyor (Ketua RT dengan pembatasan wilayah RT), dan Viewer (Lurah).
- Ingest massal data warga via Excel `.xlsx` dengan deduplikasi instan $O(1)$ via `nik_hash`.
- Perisai anti-bot portal publik `/api/public/check-status/`: Cloudflare Turnstile CAPTCHA, throttle 5 req/menit/IP, penguncian 15 menit per NIK, dan zero-enumeration 404 response.

</details>

<details>
<summary><strong>Fase 3: feat/m3-xai-fallback (Zero-PII Sanitizer, Gemini Flash XAI Explainer, Deterministic Fallback, & Async Worker)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 3 menghadirkan lapisan penjelasan (Explainer Layer) sesuai PRD Bagian 8:
- Sanitizer Zero-PII (UU PDP No. 27/2022 & OWASP LLM02) menjamin ketiadaan identitas warga yang terkirim ke Gemini API.
- Snapshot bobot beku (`BatchCriteria.frozen_weight`) diisolasi dari perubahan bobot dinamis.
- Explainer Gemini Flash API dengan generator fallback deterministik berbasis kesenjangan terbobot $\Delta_j \cdot w_j$ bebas HTTP 500.
- Worker asinkron batch XAI dengan penguncian baris `select_for_update()` dan transisi status batch ke `Narrated`.

</details>

<details>
<summary><strong>Fase 2: feat/m2-saw-tiebreaker (SAW Engine & 4-Level Tie-Breaker)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 2 mengimplementasikan inti matematis Simple Additive Weighting (SAW) sesuai PRD FR-01–FR-03:
- Normalisasi Benefit ($r_{ij} = x_{ij}/\max x$) dan Cost ($r_{ij} = \min x/x_{ij}$)
- Pembekuan bobot ke `BatchCriteria.frozen_weight`
- Pengecualian warga TMS dari matriks normalisasi
- Tie-breaker deterministik 4-level ($C_1 \rightarrow C_2 \rightarrow \text{real\_dependents} \rightarrow \text{created\_at}$)

</details>

<details>
<summary><strong>Fase 1: feat/m1-crypto-models (Database Schema & UU PDP Cryptography)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 1 membangun fondasi kepatuhan UU PDP No. 27/2022:
- Enkripsi at-rest NIK dengan AES-256-GCM
- Indexing pencarian $O(1)$ dengan HMAC-SHA256
- Masking visual `367403******0002` dan `Ahmad S******`
- Skema 9 tabel PRD + StaffUser

</details>

---

## Arsitektur & Architecture Decision Records (ADRs)

- **Spesifikasi Utama (PRD Final v3.0):** [`PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md`](./PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md)
- **Aturan Konteks Agen & Protokol UI (`.stitch`):** [`AGENTS.md`](./AGENTS.md)
- **Rencana Implementasi:** [`docs/superpowers/plans/2026-10-13-sistem-bansos-saw-xai-implementation.md`](./docs/superpowers/plans/2026-10-13-sistem-bansos-saw-xai-implementation.md)
- **Daftar ADR Arsitektur:**
  - [`ADR-001: Hybrid SAW + XAI Gemini dengan Fallback Deterministik`](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md)
  - [`ADR-002: Dual-Layer Kriptografi NIK (UU PDP) & Sanitasi Zero-PII`](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md)
  - [`ADR-003: Pembekuan Bobot Kriteria, Gate TMS, & Tie-Breaker 4-Level`](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md)
  - [`ADR-004: Antrean Tugas Asinkron XAI & Portal Publik Passwordless`](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md)
  - [`ADR-005: Arsitektur UI Responsif 3-Tier & Gerbang Review .stitch`](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md)
  - [`ADR-006: Dekripsi Terkontrol NIK pada Berita Acara PDF, Zero-PII Publik, & Metrik Evaluasi Skripsi`](./docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md)
