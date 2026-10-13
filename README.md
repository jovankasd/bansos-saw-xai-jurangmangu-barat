# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m4c-dashboard-screens` (Fase 8 / Task 8 — Admin & Surveyor Core Operational Screens: Executive Dashboard, Criteria Management, Surveyor RT Input & TMS Gate, SAW Ranking 11-Kolom Sticky, & XAI Monitor - Milestone 4C)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 8 merealisasikan 5 layar operasional inti bagi staf tata kelola adjudikasi (Kasi Kesos / Super Admin dan Surveyor Ketua RT) sesuai mandat **PRD Final v3.0**, **ADR-003**, **ADR-004**, **ADR-005**, serta protokol wajib peninjauan desain **`AGENTS.md` Bagian 2 (Review Desain #3)**:

1. **Dashboard Eksekutif Bebas Pelanggaran Regulasi (`ExecutiveDashboardPage.tsx`):**
   - **Kepatuhan Batasan "Not Doing" (PRD Bagian 12.3):** Menghapus total tombol terlarang *"Sinkronisasi DTKS"* dari desain mentah `.stitch` (baris 269), karena integrasi langsung ke API SIKS-NG/DTKS Kemensos berada di luar kewenangan operasional kelurahan dan dilindungi regulasi nasional. Digantikan tombol resmi **"Ekspor Usulan (.xlsx)"** dan **"Refresh Data"**.
   - **Bento Grid Kartu Metrik:** Menyajikan ringkasan eksekutif 4 pilar: Total Calon KPM (Eligible vs Disqualified TMS), Kuota Penerima Manfaat, Pipeline State Machine (Tahap 1–6), dan status mesin AI/Zero-PII.
   - **Rekapitulasi Sebaran per RT (RT 01 s/d RT 10):** Memetakan proporsi usulan warga dan estimasi kelolosan kuota per wilayah RT.

2. **Validasi Keras Matematis & Snapshot Snapshot Kriteria (`CriteriaManagementPage.tsx`):**
   - **Validasi Interaktif $\sum w_j = 1.00$ (FR-01):** Menolak secara reaktif apabila akumulasi bobot $\sum w_j \neq 1.000$. Jika tidak seimbang, bilah visual berubah menjadi merah (`bg-rose-50`), muncul peringatan interaktif, dan tombol *"Simpan & Validasi Bobot"* otomatis di-*disable*.
   - **Indikator Frozen Snapshot Kriteria:** Menampilkan badge gembok emas dan banner status beku jika batch seleksi aktif telah melewati tahap kalkulasi, memastikan perubahan bobot di masa mendatang tidak merusak histori batch lama (`BATCH_CRITERIA`).
   - **Koreksi Tipe $C_3$ & $C_4$:** Mengoreksi kekeliruan `.stitch` di mana $C_3$ dilabeli *Benefit* menjadi kriteria resmi **COST (0.25)** (*Kondisi Tempat Tinggal*) dan $C_4$ menjadi **COST (0.20)** (*Kepemilikan Aset*).

3. **Gerbang Usulan RT, Dependents Riil, & Filter TMS Pintu Masuk (`SurveyorInputPage.tsx`):**
   - **Pendataan Lapangan Mandiri & Massal:** Menyediakan formulir masukan cepat keluarga rentan serta modul unggah massal Excel (`POST /api/citizens/import-excel/`) dengan tautan unduh berkas template resmi.
   - **Input Khusus `real_dependents_count` (Tie-Breaker Level 3):** Menyimpan jumlah jiwa tanggungan riil sebenarnya (misal: 4 jiwa) langsung ke tabel `EVALUATION` untuk keperluan resolusi skor kembar deterministik di ambang kuota.
   - **Gerbang Diskualifikasi TMS (FR-02):** Sakelar status kelayakan administratif (`ELIGIBLE` vs `DISQUALIFIED`) dengan dropdown alasan wajib (`ASN/TNI/POLRI`, `PKH Ganda`, `Pindah Domisili`, `Meninggal Dunia`). Warga TMS langsung dipisahkan agar tidak mendistorsi matriks SAW namun tetap tercatat untuk lampiran resmi Berita Acara.

4. **Tabel SAW 11-Kolom Sticky & Transparansi Dekomposisi (`SawRankingPage.tsx`):**
   - **Solusi Responsivitas Tabel 11-Kolom:** Mengatasi masalah tabel terjepit di `.stitch` dengan membungkus tabel dalam kontainer `overflow-x-auto custom-scroll` dan menerapkan **kolom identitas sticky** (`sticky left-0` untuk `#` dan `sticky left-10` untuk Nama/NIK KPM berlatar putih dengan bayangan z-index). Identitas warga tetap terbaca saat operator menggulir nilai kriteria ke kanan di tablet/ponsel.
   - **Pembatas Visual Batas Kuota (*Quota Cutoff Divider*):** Menampilkan pemisah visual tegas berlatar emerald gelap antara peringkat lolos kuota (Rank $\le 30$) dan baris cadangan (Rank $\ge 31$).
   - **Panel Inspeksi Dekomposisi Matriks ($R_{ij}$):** Menghitung dan menampilkan perkalian terbobot $w_j \cdot r_{ij}$ per kriteria untuk setiap kandidat yang diklik.

5. **Monitor Pekerja Asinkron & Koreksi Total $C_4$ Aset (`XaiGeneratorPage.tsx`):**
   - **Koreksi Kritis Kriteria $C_4$:** Mengeliminasi seluruh teks palsu `.stitch` ("C4: Daya Listrik PLN" dan "daya listrik 900 VA") menjadi kriteria resmi **"C4: Kepemilikan Aset"** (Cost, 0.20) pada chip kriteria, narasi AI, dan grafik kesenjangan kriteria.
   - **Chip Metrik Tidak Terpotong (*Unclipped Metric Chips*):** Menata 4 metrik status (Gemini Success, Deterministic Fallback, In Progress, Pending) dalam grid adaptif (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`) sehingga tidak ada teks yang terpotong di layar tablet/mobile.
   - **Transparansi Payload Zero-PII:** Memverifikasi di antarmuka bahwa data yang dialirkan ke cloud AI hanya berupa kode anonim (`KPM-035`) dan skor kriteria tanpa nama atau NIK warga (kepatuhan UU PDP No. 27/2022).

---

### Changelog Fase 8 (Task 8)

#### Added
- **5 Komponen Halaman Operasional Dashboard:**
  - [`frontend/src/pages/dashboard/ExecutiveDashboardPage.tsx`](./frontend/src/pages/dashboard/ExecutiveDashboardPage.tsx): Dashboard ikhtisar eksekutif Kasi Kesos dengan bento grid metrik, sebaran usulan RT 01–10, log audit aktivitas sistem, dan penghapusan tombol ilegal sinkronisasi DTKS.
  - [`frontend/src/pages/dashboard/CriteriaManagementPage.tsx`](./frontend/src/pages/dashboard/CriteriaManagementPage.tsx): Antarmuka konfigurasi bobot preferensi dengan validasi interaktif $\sum w_j = 1.00$, bilah proporsi adaptif, indikator gembok *Frozen Criteria Snapshot*, dan kartu pemetaan Crips $C_1 - C_4$.
  - [`frontend/src/pages/dashboard/SurveyorInputPage.tsx`](./frontend/src/pages/dashboard/SurveyorInputPage.tsx): Layar operasional Surveyor RT dengan input angka riil `real_dependents_count`, sakelar gerbang TMS administratif (FR-02), dropzone import spreadsheet massal (`.xlsx`), dan riwayat pengajuan KPM wilayah.
  - [`frontend/src/pages/dashboard/SawRankingPage.tsx`](./frontend/src/pages/dashboard/SawRankingPage.tsx): Antarmuka peringkat hasil komputasi SAW dengan tabel 11-kolom berfitur *sticky identity column*, pembatas visual batas kuota (*cutoff divider*), penanda tie-breaker bertingkat, dan panel detail dekomposisi matriks $r_{ij}$.
  - [`frontend/src/pages/dashboard/XaiGeneratorPage.tsx`](./frontend/src/pages/dashboard/XaiGeneratorPage.tsx): Layar pemantauan antrean pekerja asinkron Celery/Django-Q, bilah progres adjudikasi XAI, kartu metrik unclipped, pelindung Zero-PII, inspeksi narasi dwibahasa, dan koreksi kriteria $C_4$ Kepemilikan Aset.
- **Suite Pengujian Vitest TDD:**
  - [`frontend/src/__tests__/DashboardScreens.test.tsx`](./frontend/src/__tests__/DashboardScreens.test.tsx): 11 skenario pengujian komprehensif menguji ketiadaan tombol DTKS, validasi dinamis $\sum w_j = 1.00$, deteksi snapshot kriteria, input tanggungan riil, rendering tabel matriks SAW sticky, dan eksklusi label daya listrik pada modul XAI.

#### Changed
- **Pembaruan Routing Aplikasi ([`frontend/src/App.tsx`](./frontend/src/App.tsx)):**
  - Menghubungkan rute operasional internal `/admin/dashboard`, `/admin/criteria`, `/admin/citizens`, `/admin/selection`, dan `/admin/xai` langsung ke ke-5 komponen operasional di atas menggantikan placeholder statis.

#### Security & Compliance
- **Penegakan Aturan Batasan "Not Doing" (PRD Bagian 12.3):**
  - Mencegah fitur fiktif atau berbahaya seperti koneksi API langsung ke server Kemensos tanpa payung regulasi.
- **Zero-PII Verification:**
  - Memastikan modul inspeksi payload XAI hanya mengekspos `applicant_code`, peringkat, dan metrik kriteria anonim.
- **Hierarchical Tie-Breaker Resolution:**
  - Menyediakan penampung data `real_dependents_count` pada form input RT untuk mendukung resolusi skor kembar di Level 3 tie-breaker PRD.

---

### Perbandingan Desain Prototipe `.stitch` vs Implementasi Resmi

```
┌───────────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Desain Mentah .stitch (Deviasi)       │ Implementasi Resmi Fase 8 (Civic Precision & PRD)      │
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Tombol "Sinkronisasi DTKS" di header  │ DIHAPUS TOTAL (PRD 12.3 Not-Doing); diganti Ekspor     │
│ dashboard eksekutif.                  │ Excel (.xlsx) resmi kelurahan & Refresh Data Batch.   │
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Validasi bobot pasif tanpa proteksi   │ Validasi INTERAKTIF: button simpan disabled jika       │
│ interaktif bila sum != 1.00.          │ sum != 1.00, alert visual merah/hijau & snapshot lock. │
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ C4 dilabeli "Daya Listrik PLN" dan   │ KOREKSI 100% MENJADI "Kepemilikan Aset" (Cost, 0.20)   │
│ narasi hardcoded "daya listrik 900 VA"│ di seluruh chips, narasi XAI, dan chart gap kriteria.  │
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ C3 di manajemen bobot dilabeli Benefit│ KOREKSI MENJADI "COST (0.25)" (Kondisi Tempat Tinggal).│
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Tabel 11 kolom SAW terjepit di laptop │ Wrapper overflow-x-auto + KOLOM IDENTITAS STICKY       │
│ sempit dan terpotong di tablet/HP.    │ (Nomor & Nama KPM tetap terkunci saat scroll kriteria).│
├───────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Kartu metrik worker XAI terpotong     │ Grid responsif proporsional (1 col mobile, 2 tablet,   │
│ pada teks "Deterministic Fallback".   │ 4 desktop) dengan padding bernapas (unclipped).        │
└───────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

---

### Daftar File Fase 8

| File | Tanggung Jawab |
| :--- | :--- |
| [`./frontend/src/pages/dashboard/ExecutiveDashboardPage.tsx`](./frontend/src/pages/dashboard/ExecutiveDashboardPage.tsx) | Dashboard ikhtisar eksekutif Kasi Kesos (Bento grid, agregat RT, audit log, tanpa tombol DTKS) |
| [`./frontend/src/pages/dashboard/CriteriaManagementPage.tsx`](./frontend/src/pages/dashboard/CriteriaManagementPage.tsx) | Konfigurasi bobot kriteria SAW dengan validasi $\sum w_j = 1.00$ dan status *Frozen Criteria Snapshot* |
| [`./frontend/src/pages/dashboard/SurveyorInputPage.tsx`](./frontend/src/pages/dashboard/SurveyorInputPage.tsx) | Formulir pendataan lapangan KPM RT, input `real_dependents_count`, sakelar gerbang TMS, dan impor Excel |
| [`./frontend/src/pages/dashboard/SawRankingPage.tsx`](./frontend/src/pages/dashboard/SawRankingPage.tsx) | Tabel ranking komputasi SAW 11-kolom dengan kolom identitas sticky, garis batas kuota, dan drawer matriks |
| [`./frontend/src/pages/dashboard/XaiGeneratorPage.tsx`](./frontend/src/pages/dashboard/XaiGeneratorPage.tsx) | Pemantauan worker asinkron XAI, progres narasi, Zero-PII sanitasi, dan koreksi kriteria $C_4$ Aset |
| [`./frontend/src/App.tsx`](./frontend/src/App.tsx) | Konfigurasi rute React Router untuk 5 halaman operasional internal staf kelurahan |
| [`./frontend/src/__tests__/DashboardScreens.test.tsx`](./frontend/src/__tests__/DashboardScreens.test.tsx) | Suite pengujian TDD Vitest untuk 5 layar operasional Admin dan Surveyor |

---

### Hasil Verifikasi Test

```text
$ npm --prefix frontend test -- --run

 RUN  v2.1.9 D:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/frontend

 ✓ src/__tests__/AppShell.responsive.test.tsx (4 tests) 328ms
   ✓ toggles mobile drawer via hamburger button and closes via backdrop
   ✓ enforces RBAC: hides mutation actions from Viewer (Lurah) and displays approval menu
   ✓ enforces RBAC: allows Super Admin to see all governance modules including SAW execution and weight config
   ✓ enforces RBAC: scopes Surveyor (Ketua RT) strictly to RT operations

 ✓ src/__tests__/PublicPortalPage.test.tsx (6 tests) 407ms
   ✓ renders NIK + 4-digit KK + CAPTCHA verification form and excludes prohibited two-way appeal form
   ✓ submits verification and renders full dossier with masked PII, 4-part XAI narrative, and C1..C4 gap chart
   ✓ renders LOLOS status correctly with approval badge
   ✓ handles lockout and error scenarios (403, 429, 404)
   ✓ renders login form and authenticates staff successfully
   ✓ displays error banner on authentication failure

 ✓ src/__tests__/DashboardScreens.test.tsx (11 tests) 584ms
   ✓ excludes Sinkronisasi DTKS button on ExecutiveDashboardPage per PRD Not-Doing
   ✓ renders KPI cards and active batch metrics
   ✓ disables weight save button when sum of weights != 1.00 on CriteriaManagementPage
   ✓ enables weight save button when sum of weights == 1.00
   ✓ renders Frozen Criteria Snapshot indicator when batch is locked
   ✓ renders real dependents count and TMS reason selector on SurveyorInputPage
   ✓ shows TMS disqualification reason select when status is DISQUALIFIED
   ✓ renders SAW ranking table and matrix detail drawer on SawRankingPage
   ✓ displays sticky table and C3 as COST and C4 as Kepemilikan Aset
   ✓ displays C4 as Kepemilikan Aset in XAI payload monitor
   ✓ shows Zero-PII sanitation badge and worker progress

 Test Files  3 passed (3)
      Tests  21 passed (21)
   Start at  18:11:10
   Duration  4.71s

# Verifikasi Kompilasi TypeScript & Build Produksi Vite:
$ npm --prefix frontend run build

vite v6.4.4 building for production...
transforming...
✓ 1649 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.99 kB │ gzip:   0.55 kB
dist/assets/index-Dk8B41x0.css   33.12 kB │ gzip:   6.26 kB
dist/assets/index-B-ilBthb.js   358.73 kB │ gzip: 101.38 kB
✓ built in 4.53s
```

---

## Dokumentasi Branch Sebelumnya

<details>
<summary><strong>Fase 7: feat/m4b-public-portal (Public Citizen Portal /cek-bansos, Masking PII, CriteriaGapChart C1..C4, & Staff Login /admin/login - Milestone 4B)</strong></summary>

### Mengapa Fase Ini Dibutuhkan
Fase 7 mengimplementasikan portal transparansi publik bagi warga pemohon bansos (`/cek-bansos`) serta gerbang masuk staf adjudikasi (`/admin/login`) dengan mematuhi prinsip akuntabilitas terbuka, keamanan data kependudukan (**UU PDP No. 27/2022**), dan arahan rancangan **Civic Precision**:
- Akses mandiri passwordless untuk warga dengan verifikasi NIK 16 digit + 4 digit terakhir nomor KK + Cloudflare CAPTCHA Turnstile.
- Perlindungan privasi berlapis dan penyamaran visual 100% (`367403******0002` & `Ahmad S******`).
- Penghapusan form sanggahan dua arah (PRD 12.2) diganti dengan kartu edukasi advokasi offline ke Ketua RT.
- Grafik komparasi kesenjangan kriteria terbobot horizontal (`CriteriaGapChart.tsx`).
- Autentikasi staf SimpleJWT dengan pembagian peran terstruktur (`LoginPage.tsx`).

</details>

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
