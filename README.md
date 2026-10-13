# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `test/fase-9-e2e-browser` (Fase 9 — End-to-End Browser Verification & 3-Tier Responsive Audit via Real Browser Engine)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 9 merupakan tahap verifikasi pamungkas (*pre-launch validation*) yang menguji sistem secara holistik dari kacamata peramban web nyata (*real browser engine*). Jika fase-fase sebelumnya menguji logika backend secara terisolasi (Pytest) dan komponen UI dalam mock jsdom (Vitest), Fase 9 menjamin:
1. **Kohesi Penuh Antar-Layar (End-to-End Lifecycle Integrity):** Memverifikasi bahwa transisi status batch dari usulan awal hingga penerbitan publik (`Collecting` $\rightarrow$ `Calculated` $\rightarrow$ `Narrated` $\rightarrow$ `Approved` $\rightarrow$ `Published` $\rightarrow$ `/cek-bansos`) berjalan tanpa patahan data, authorization leak, atau kegagalan asinkron.
2. **Kepatuhan Protokol Responsivitas 3 Ukuran Layar (AGENTS.md Bagian 2):** Menjamin aplikasi berfungsi sempurna pada **Mobile (375px)**, **Tablet (768px)**, dan **Desktop (1440px)** tanpa elemen terpotong (*clipped*), overflow tak terkontrol, atau menu yang menutupi layar.
3. **Kenyamanan Warga & Zero Console Error:** Memastikan transparansi hasil seleksi bansos bagi warga tanpa error JavaScript runtime, serta validasi visual terhadap grafik gap kriteria $C_1 - C_4$, narasi XAI dwibahasa, dan dokumen PDF resmi.

---

### Changelog: Verified & Fixed

#### Verified (Uji Fungsional & E2E Lifecycle)
- **Role 1 — Kasi Kesos (`SUPER_ADMIN`):**
  - Autentikasi staf via JWT SimpleJWT dan pengalihan dinamis ke Executive Dashboard.
  - Halaman Manajemen Kriteria ([`/admin/criteria`](./frontend/src/pages/dashboard/CriteriaManagementPage.tsx)) memvalidasi rumus mutlak SAW $\sum w_j = 1.00$ (C1=0.30, C2=0.25, C3=0.25, C4=0.20) dengan indikator snapshot aktif.
  - Kalkulasi SAW ([`/admin/selection`](./frontend/src/pages/dashboard/SawRankingPage.tsx)) memproses 8 kandidat (7 Eligible, 1 TMS) dengan peringkat objektif dan ambang batas kuota cutoff ($V_i = 0.5625$).
  - Monitoring XAI ([`/admin/xai`](./frontend/src/pages/dashboard/XaiGeneratorPage.tsx)) memantau status worker Zero-PII secara transparan.
- **Role 2 — Surveyor RT 003 (`SURVEYOR`):**
  - Pembatasan wilayah operasional (*RT scoping*) otomatis terkunci pada RT 003.
  - Formulir pendataan warga ([`/admin/citizens`](./frontend/src/pages/dashboard/SurveyorInputPage.tsx)) memuat input tanggungan riil (`real_dependents_count`), skor Crips 1–5, dan gerbang filter TMS (ASN/TNI/Polri).
- **Role 3 — Lurah (`VIEWER`):**
  - Layar Pengesahan Berita Acara ([`/admin/berita-acara`](./frontend/src/pages/dashboard/LurahApprovalPage.tsx)) menyajikan lembar A4 resmi ber-Kop Surat Pemkot Tangsel dan QR Code digest SHA-256.
  - Fitur **Uji Petik Narasi XAI (*Spot-Check Tabs*)** berfungsi mulus pada 3 studi kasus kritis (*Peringkat #1*, *Ambang Cutoff*, dan *Cadangan Prioritas*).
  - Pengesahan batch berhasil mengubah status menjadi `Approved`, dilanjutkan penerbitan publik (`Published`) oleh Super Admin.
- **Role 4 — Portal Warga Publik ([`/cek-bansos`](./frontend/src/pages/PublicPortalPage.tsx)):**
  - Pencarian warga menggunakan 16 digit NIK (`3674031505850002`) + 4 digit terakhir No KK (`2222`) + CAPTCHA Turnstile.
  - Hasil penelusuran menampilkan status kelulusan **LOLOS (Peringkat #1)** dengan nama tersamarkan (`Ahmad S******`) dan NIK tersamarkan (`367403******0002`) sesuai amanat UU PDP No. 27/2022.
  - Narasi XAI transparan dan grafik radar kesenjangan kriteria $C_1 - C_4$ ([`CriteriaGapChart`](./frontend/src/components/public/CriteriaGapChart.tsx)) termuat tanpa distorsi.
  - Tombol unduh dokumen hasil seleksi menghasilkan tautan bertanda tangan kriptografis (`download_token`).

#### Fixed & Hardened (Sistem & Infrastruktur)
- **CORS Allowed Origins:** Menambahkan `http://localhost:3000` dan `http://127.0.0.1:3000` ke `CORS_ALLOWED_ORIGINS` di backend `.env` untuk mendukung integrasi penuh Vite dev server dan Django REST API.
- **Rate Limit Login (Test Optimization):** Mengonfigurasi `AUTH_LOGIN_RATE_LIMIT=60/min` pada lingkungan pengembangan untuk mencegah False-Positive HTTP 429 saat audit login multi-peran dijalankan secara beruntun.
- **Gemini Model Migration & Network Timeout Hardening:**
  - Memperbarui model AI dari `gemini-2.5-flash` ke `gemini-3.8-flash`.
  - Menambahkan konfigurasi batas waktu klien `http_options={"timeout": 10.0}` pada `genai.Client` di [`backend/core/services/xai_explainer.py`](./backend/core/services/xai_explainer.py). Hal ini mencegah proses worker gantung (*hang*) akibat lonjakan trafik server eksternal, sehingga fallback deterministik rule-based langsung mengambil alih dalam hitungan detik.
- **Automated Verification Harness:**
  - Membuat skrip otomatis [`frontend/run_e2e_verification.cjs`](./frontend/run_e2e_verification.cjs) berbasis Playwright yang menjalankan seluruh siklus E2E 8 langkah dan audit 3 viewport.
  - Membuat perintah seeder demo [`backend/core/management/commands/seed_demo_citizens.py`](./backend/core/management/commands/seed_demo_citizens.py) dengan 8 data uji realistis (1 TMS, 7 Eligible dengan variasi Crips C1–C4).

---

### Ringkasan Hasil Uji E2E Alur `Draft -> Published -> /cek-bansos`

```mermaid
flowchart LR
    A["1. Draft/Collecting\n(8 Warga: 1 TMS, 7 Eligible)"] --> B["2. Calculated\n(SAW Engine V_i, Cutoff=0.5625)"]
    B --> C["3. Narrated\n(Gemini 3.8 Flash + Fallback)"]
    C --> D["4. Approved\n(Uji Petik & Pengesahan Lurah)"]
    D --> E["5. Published\n(Diterbitkan ke Portal Publik)"]
    E --> F["6. /cek-bansos\n(Verifikasi Warga, Masking, Gap Chart)"]
```

| Tahap Lifecycle | Aktor / Peran | Endpoint REST API | Status Transisi | Status Uji |
| :--- | :--- | :--- | :--- | :--- |
| **1. Kriteria** | Kasi Kesos (`SUPER_ADMIN`) | `GET /api/criteria/` | $\sum w_j = 1.00$ Valid | **PASSED** |
| **2. Kalkulasi SAW** | Kasi Kesos (`SUPER_ADMIN`) | `POST /api/selection/1/calculate/` | `Collecting` $\rightarrow$ `Calculated` | **PASSED** |
| **3. Narasi XAI** | Background Worker | `POST /api/selection/1/generate-xai/` | `Calculated` $\rightarrow$ `Narrated` | **PASSED** |
| **4. Validasi RT** | Ketua RT (`SURVEYOR`) | `GET /api/citizens/` | Scoped RT 003, TMS Terfilter | **PASSED** |
| **5. Sidang Pleno** | Lurah (`VIEWER`) | `PATCH /api/selection/1/approve/` | `Narrated` $\rightarrow$ `Approved` | **PASSED** |
| **6. Publikasi** | Kasi Kesos (`SUPER_ADMIN`) | `PATCH /api/selection/1/publish/` | `Approved` $\rightarrow$ `Published` | **PASSED** |
| **7. Cek Warga** | Warga Publik | `POST /api/public/check-status/` | Masked PII + XAI + PDF Token | **PASSED** |

---

### Audit Responsivitas 3 Ukuran Layar (*3-Tier Responsive Audit*)

Pengujian visual dilakukan pada peramban Chrome asli dengan rendering piksel aktual untuk memverifikasi kepatuhan terhadap aturan antarmuka pada `AGENTS.md`:

1. **Mobile (`375px` width x `667px` height):**
   - **Sidebar Off-Canvas Drawer:** Sidebar tidak menutupi konten permanen. Tombol *Hamburger Menu* (`button[aria-label="Buka menu navigasi"]`) di Topbar berhasil membuka slide-over drawer dengan mulus.
   - **Layout Vertikal:** Form verifikasi NIK dan kartu pengumuman bansos mengalir vertikal (`grid-cols-1`) dengan padding proporsional tanpa ada teks atau tombol yang terpotong di tepi layar.
   - **Touch Target:** Seluruh tombol aksi memiliki tinggi minimum $\ge 40\text{px}$ yang nyaman disentuh.

2. **Tablet (`768px` width x `1024px` height):**
   - **Grid Proporsional 2 Kolom:** Halaman Manajemen Kriteria dan Dashboard membagi ruang kerja secara seimbang tanpa teks yang berhimpitan.
   - **Tabel SAW Scrollable:** Matriks normalisasi $R_{ij}$ dan ranking KPM dilengkapi wrapper `overflow-x-auto` yang dapat digeser secara horizontal dengan kolom nomor dan identitas tetap terbaca.

3. **Desktop (`1440px` width x `900px` height):**
   - **Sidebar Terkunci di Kiri:** Sidebar `lg:fixed lg:w-64` dengan offset konten `lg:pl-64`.
   - **Topbar Anti-Clipped:** Topbar menggunakan penataan fleksibel yang mencegah profil pengguna, status batch, dan badge peran terpotong di sudut kanan atas layar.

#### Daftar Artefak Tangkapan Layar (Screenshots)
Seluruh 15 file tangkapan layar tersimpan pada folder [`frontend/e2e_screenshots/`](./frontend/e2e_screenshots/):
- `01_login_page_desktop.png` — Form login staf kelurahan (Desktop 1440px)
- `02_executive_dashboard_desktop.png` — Dashboard eksekutif adjudikasi bansos (Desktop 1440px)
- `03_criteria_management_desktop.png` — Manajemen kriteria SAW $\sum w_j = 1.00$ (Desktop 1440px)
- `04_saw_ranking_desktop.png` — Matriks ranking SAW 11-kolom dan tie-breaker (Desktop 1440px)
- `05_xai_generator_desktop.png` — Monitoring worker Zero-PII XAI Gemini (Desktop 1440px)
- `06_surveyor_input_desktop.png` — Formulir pendataan warga RT 003 & gate TMS (Desktop 1440px)
- `07_lurah_approval_desktop.png` — Pengesahan Berita Acara A4 & uji petik narasi Lurah (Desktop 1440px)
- `08_public_portal_empty_desktop.png` — Halaman beranda pengecekan bansos warga (Desktop 1440px)
- `09_public_portal_result_desktop.png` — Hasil pengumuman status LOLOS, narasi XAI, & gap chart (Desktop 1440px)
- `10_mobile_375px_public_portal.png` — Tampilan portal publik pada layar HP (Mobile 375px)
- `11_mobile_375px_dashboard.png` — Tampilan dashboard operasional pada layar HP (Mobile 375px)
- `12_mobile_375px_drawer_opened.png` — Off-Canvas Navigation Drawer terbuka via Hamburger Menu (Mobile 375px)
- `13_tablet_768px_saw_table.png` — Tabel perankingan SAW pada layar Tablet (Tablet 768px)
- `14_tablet_768px_criteria.png` — Grid 2-kolom manajemen kriteria pada layar Tablet (Tablet 768px)
- `15_desktop_1440px_layout.png` — Tata letak desktop penuh tanpa clipping (Desktop 1440px)

---

### Hasil Verifikasi Console & Network

Hasil audit runtime menggunakan Chrome DevTools Protocol / Playwright:

```text
================================================================================
   AUDIT RUNTIME CONSOLE & NETWORK LOGS                                         
================================================================================
Jumlah Console Error: 0
  [PASSED] 0 Runtime Console Error across all pages and viewports!
Jumlah Console Warnings: 28 (Vendor chart sizing warnings, non-critical)
Status Eksekusi E2E: SUCCESS (Exit Code 0)
================================================================================
```

---

## Dokumentasi Branch Sebelumnya

<details>
<summary><strong>Fase 8 / Task 9: feat/m6-thesis-eval (Lurah Approval Screen & Thesis Evaluation Metrics [Fidelity, Hallucination, SUS, White-Box SAW] - Milestone 5 & 6 UI)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 8 melengkapi seluruh spektrum antarmuka pengguna pada sistem pendukung keputusan hibrida dengan merealisasikan dua modul krusial di puncak hierarki tata kelola pemerintahan dan pengujian ilmiah skripsi:
1. **Layar Pengesahan & Penerbitan Berita Acara Lurah (`LurahApprovalPage.tsx`):** Puncak Siklus State Machine Seleksi (`Narrated` $\rightarrow$ `Approved` $\rightarrow$ `Published`), pratinjau kertas A4 ber-QR Code, panel uji petik narasi XAI, dan penegakan RBAC.
2. **Modul Akademik Evaluasi Empiris Skripsi Bab 4 & 5 (`ThesisEvaluationPage.tsx`):** Verifikasi Akurasi White-Box SAW (100.0% vs Excel), Fidelity Score $\ge 95.0\%$ (Capaian 100.0%), Hallucination Rate $= 0.0\%$, uji stress test asinkron, System Usability Scale (SUS = 84.25 / Grade A), dan ekspor dataset multi-sheet.

</details>

<details>
<summary><strong>Fase 8 / Task 8: feat/m4c-dashboard-screens (Admin & Surveyor Core Operational Screens: Executive Dashboard, Criteria Management, Surveyor RT Input & TMS Gate, SAW Ranking 11-Kolom Sticky, & XAI Monitor - Milestone 4C)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 8 merealisasikan 5 layar operasional inti bagi staf tata kelola adjudikasi (Kasi Kesos / Super Admin dan Surveyor Ketua RT) sesuai mandat PRD Final v3.0, ADR-003, ADR-004, ADR-005, serta protokol wajib peninjauan desain AGENTS.md Bagian 2 (Review Desain #3):
- Dashboard Eksekutif bebas pelanggaran regulasi: menghapus total tombol terlarang *"Sinkronisasi DTKS"*.
- Validasi keras matematis $\sum w_j = 1.00$ dan indikator *Frozen Criteria Snapshot*.
- Formulir pendataan RT, input `real_dependents_count`, dan gerbang filter TMS (FR-02).
- Tabel perankingan SAW 11-kolom dengan kolom identitas sticky (`#` dan NIK/Nama KPM terkunci saat scroll horizontal).
- Pemantauan worker asinkron XAI dengan koreksi total kriteria $C_4$ Kepemilikan Aset (menghapus label daya listrik fiktif).

</details>

<details>
<summary><strong>Fase 7 / Task 7: feat/m4b-public-portal (Public Citizen Portal /cek-bansos, Masking PII, CriteriaGapChart C1..C4, & Staff Login /admin/login - Milestone 4B)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 7 mengimplementasikan portal publik bagi warga Kelurahan Jurangmangu Barat untuk memeriksa kelulusan bansos secara mandiri, transparan, dan aman dari perayapan bot massal (*scraping*) sesuai amanat UU Pelindungan Data Pribadi No. 27/2022.

</details>
