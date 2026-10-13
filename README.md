# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m4a-frontend-appshell` (Fase 6 / Task 6 — Frontend Scaffolding, Civic Precision Theme, & 3-Tier Responsive AppShell - Milestone 4A)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 6 merealisasikan fondasi antarmuka pengguna web (*User Interface Scaffolding & Responsive Shell*) sesuai amanat **[AGENTS.md Bagian 2](./AGENTS.md)**, **[ADR-005](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md)**, dan **PRD Bagian 3 & Bagian 12**:

1. **Penerapan Desain *Civic Precision*:**
   - Membangun fondasi frontend modern menggunakan **React 18**, **Vite 6**, dan **Tailwind CSS v3.4** dengan palet resmi *Emerald Civic* (`#003426` Primary, `#0f4c3a` Primary Container, `#f8f9ff` Surface Canvas).
   - Menerapkan tipografi dua pilar (*Dual-Typeface Rigor*): font **`Hanken Grotesk`** untuk teks naratif, judul otoritas institusional, dan navigasi; serta font monospace **`JetBrains Mono`** untuk data presisi teknis (NIK masked, ID KPM, skor desimal SAW, bobot kriteria beku, dan status kuota).
2. **Kepatuhan Protokol Wajib Review Desain & Eliminasi Bug `.stitch`:**
   - Mematuhi aturan ketat *Mandatory Design Review Gate*: prototipe mentah di `.stitch/designs/*.html` tidak disalin mentah-mentah (*no blind copy-paste*).
   - Memperbaiki bug *clipping* pada Topbar: tombol aksi dan profil yang sebelumnya terpotong keluar layar pada prototipe `.stitch` diperbaiki menggunakan tata letak responsif bebas overflow.
   - Menghapus fitur ilegal yang dilarang pada PRD Bagian 12, seperti tombol *"Sinkronisasi DTKS"* (sistem Bansos JUBAR beroperasi mandiri di tingkat kelurahan tanpa integrasi langsung API Kemensos).
3. **Arsitektur Responsif 3-Tier (Mobile, Tablet, Desktop):**
   - Menghadirkan komponen shell terpadu `<AppShell />` yang menjamin antarmuka dapat digunakan dengan nyaman oleh Ketua RT di lapangan menggunakan Handphone (`< 768px`) atau Tablet (`768px – 1023px`), maupun Kasi Kesos dan Lurah di kantor kelurahan menggunakan Desktop (`>= 1024px`).
4. **Penegakan Role-Based Access Control (RBAC) pada Navigasi:**
   - Mengintegrasikan navigasi berbasis hak akses staf:
     - **`SUPER_ADMIN` (Kasi Kesejahteraan Sosial):** Memiliki akses penuh termasuk tombol mutasi *"Eksekusi Batch SAW"* dan menu *"Konfigurasi Bobot SAW"*.
     - **`SURVEYOR` (Ketua RT):** Dibatasi hanya pada menu pendataan dan usulan warga di wilayah RT-nya, dilarang mengakses tombol mutasi SAW dan konfigurasi bobot.
     - **`VIEWER` (Lurah Jurangmangu Barat):** Berperan sebagai peninjau dan pengesah Berita Acara, dilarang keras melihat tombol mutasi *"Eksekusi Batch SAW"* maupun menu konfigurasi bobot.

---

### Changelog Fase 6 (Task 6)

#### Added
- **Frontend Scaffolding & Configuration:**
  - [`frontend/package.json`](./frontend/package.json): Dependensi inti React 18, React Router v6, Tailwind CSS, Lucide React, Axios, Vitest, dan React Testing Library.
  - [`frontend/vite.config.ts`](./frontend/vite.config.ts): Konfigurasi build Vite, path alias `@/`, proxy backend `/api` ke `localhost:8000`, dan konfigurasi test runner Vitest jsdom.
  - [`frontend/tailwind.config.js`](./frontend/tailwind.config.js): Konfigurasi palet warna *Civic Precision*, ekstensi font `Hanken Grotesk` dan `JetBrains Mono`, serta radius sudut terkalibrasi.
  - [`frontend/src/index.css`](./frontend/src/index.css): Import font Google Fonts, utilitas scrollbar kustom, dan reset CSS kanvas.
- **State Management & Klien API:**
  - [`frontend/src/types/auth.ts`](./frontend/src/types/auth.ts): Definisi kontrak tipe TypeScript untuk `UserRole` (`SUPER_ADMIN`, `SURVEYOR`, `VIEWER`), objek `User`, dan token sesi.
  - [`frontend/src/context/AuthContext.tsx`](./frontend/src/context/AuthContext.tsx): Context Provider untuk autentikasi staf, penyimpanan JWT token di localStorage, auto-login, dan mutasi logout.
  - [`frontend/src/lib/api.ts`](./frontend/src/lib/api.ts): Klien Axios singleton dengan interceptor penyisipan otomatis header `Authorization: Bearer <token>` dan mekanisme refresh token.
- **Komponen Tata Letak 3-Tier (<AppShell />):**
  - [`frontend/src/components/layout/Sidebar.tsx`](./frontend/src/components/layout/Sidebar.tsx): Sidebar persisten (Desktop) dan slide-over drawer (Mobile/Tablet) dengan transisi mulus, penutup backdrop gelap, shortcut tombol keyboard Escape, kartu identitas staf, dan penyaringan menu RBAC otomatis.
  - [`frontend/src/components/layout/Topbar.tsx`](./frontend/src/components/layout/Topbar.tsx): Topbar navigasi atas dengan tombol Hamburger ramah sentuhan (`min-h-[44px]`), breadcrumb hierarkis, indikator denyut Celery worker, badge peran staf, dan bebas clipping.
  - [`frontend/src/components/layout/AppShell.tsx`](./frontend/src/components/layout/AppShell.tsx): Komponen pembungkus master layout yang mengintegrasikan Sidebar, Topbar, dan area kanvas konten utama dengan penyesuaian margin dinamis (`lg:pl-64`).
- **Suite Pengujian TDD:**
  - [`frontend/src/test-utils.tsx`](./frontend/src/test-utils.tsx): Helper `renderWithProviders` untuk membungkus pengujian komponen dalam `BrowserRouter` dan `AuthContext` dengan mocking peran pengguna dinamis.
  - [`frontend/src/__tests__/AppShell.responsive.test.tsx`](./frontend/src/__tests__/AppShell.responsive.test.tsx): 4 skenario uji komprehensif menguji interaksi buka-tutup drawer mobile, penutupan via backdrop/tombol silang, penegakan isolasi aksi mutasi pada peran `VIEWER` (Lurah), ketersediaan modul lengkap untuk `SUPER_ADMIN`, dan pembatasan wilayah RT untuk peran `SURVEYOR`.

#### Changed
- **Topbar Action Grouping:** Menghilangkan potensi teks dan tombol terpotong pada layar tablet/kecil dengan pengelompokan fleksibel dan penghapusan tombol ilegal *"Sinkronisasi DTKS"*.
- **Penyatuan Menu Navigasi:** Menyelaraskan seluruh label navigasi yang tidak konsisten pada file prototipe `.stitch` ke dalam skema terpadu yang mematuhi PRD.

---

### Arsitektur Responsif 3-Tier `<AppShell />`

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           TAMPILAN DESKTOP (>= 1024px)                 │
  │  ┌───────────────┬──────────────────────────────────────────────────┐  │
  │  │ SIDEBAR FIXED │ TOPBAR (Breadcrumbs, Batch Selector, Celery Pulse)│  │
  │  │ (lg:w-64)     ├──────────────────────────────────────────────────┤  │
  │  │               │                                                  │  │
  │  │ - Logo & Brand│ MAIN WORKBENCH CANVAS (lg:pl-64)                 │  │
  │  │ - Action SAW  │                                                  │  │
  │  │ - Menu Navigasi│ - Bento Metric Cards (xl:grid-cols-4)            │  │
  │  │ - Profil Staf │ - Master-Detail Tables & XAI Panel               │  │
  │  │               │                                                  │  │
  │  └───────────────┴──────────────────────────────────────────────────┘  │
  └────────────────────────────────────────────────────────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────┐
  │                           TAMPILAN MOBILE (< 768px)                    │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │ TOPBAR: [≡ Hamburger (44px)] EDSS JUBAR ... [Worker Ready] [Role]│  │
  │  ├──────────────────────────────────────────────────────────────────┤  │
  │  │ KONTEN UTAMA:                                                    │  │
  │  │ - Reflow Vertikal: Grid 1 Kolom (grid-cols-1)                    │  │
  │  │ - Tabel dengan Scroll Container Halus (Zero Horizontal Leak)     │  │
  │  └──────────────────────────────────────────────────────────────────┘  │
  │                                                                        │
  │  Saat Hamburger ditekan:                                               │
  │  [ BACKDROP GELAP (bg-black/60) ]                                      │
  │    ┌────────────────────────┐                                          │
  │    │ DRAWER SLIDE-OVER      │ ◄── Animasi slide dari kiri              │
  │    │ [X Tutup] Logo EDSS    │                                          │
  │    │ Navigasi Menu & Profil │                                          │
  │    └────────────────────────┘                                          │
  └────────────────────────────────────────────────────────────────────────┘
```

#### Matriks Hak Akses Menu & Aksi Navigasi (RBAC)

| Menu / Komponen | Rute Halaman | `SUPER_ADMIN` (Kasi Kesos) | `SURVEYOR` (Ketua RT) | `VIEWER` (Lurah) |
| :--- | :--- | :---: | :---: | :---: |
| **Tombol Eksekusi Batch SAW** | Action Mutasi | **Tampil** | **Disembunyikan** | **Disembunyikan** |
| **Dashboard Adjudikasi** | `/admin/dashboard` | **Tampil** | Dashboard RT | **Tampil** |
| **Data Warga & Import Excel** | `/admin/citizens` | **Tampil** (Semua RT) | **Tampil** (Khusus RT-nya) | **Disembunyikan** |
| **Dossier & Seleksi SAW** | `/admin/selection` | **Tampil** (Edit & Hitung) | Status Usulan RT | **Tampil** (Mode Baca) |
| **XAI Model Explainability** | `/admin/xai` | **Tampil** | **Disembunyikan** | **Tampil** |
| **Pengesahan Berita Acara** | `/admin/berita-acara` | **Tampil** | **Disembunyikan** | **Tampil** (Unduh PDF) |
| **Konfigurasi Bobot SAW** | `/admin/criteria` | **Tampil** | **Disembunyikan** | **Disembunyikan** |
| **Evaluasi Skripsi** | `/admin/evaluation` | **Tampil** | **Disembunyikan** | **Disembunyikan** |
| **Audit Log & Integritas** | `/admin/audit` | **Tampil** | **Disembunyikan** | **Tampil** |

---

### Daftar File Fase 6

| File | Tanggung Jawab |
| :--- | :--- |
| [`./frontend/package.json`](./frontend/package.json) | Konfigurasi dependensi npm dan script eksekusi Vite/Vitest |
| [`./frontend/vite.config.ts`](./frontend/vite.config.ts) | Konfigurasi build Vite, reverse proxy backend, dan setup Vitest jsdom |
| [`./frontend/tailwind.config.js`](./frontend/tailwind.config.js) | Registrasi token desain *Civic Precision*, warna, font, dan radius |
| [`./frontend/src/index.css`](./frontend/src/index.css) | Global stylesheet, import font Hanken Grotesk & JetBrains Mono |
| [`./frontend/src/types/auth.ts`](./frontend/src/types/auth.ts) | Definisi tipe TypeScript peran pengguna (`SUPER_ADMIN`, `SURVEYOR`, `VIEWER`) |
| [`./frontend/src/lib/api.ts`](./frontend/src/lib/api.ts) | Client HTTP Axios dengan interceptor JWT Bearer Token |
| [`./frontend/src/context/AuthContext.tsx`](./frontend/src/context/AuthContext.tsx) | Provider context autentikasi staf, role switcher, dan mutasi logout |
| [`./frontend/src/components/layout/Sidebar.tsx`](./frontend/src/components/layout/Sidebar.tsx) | Navigasi sidebar terpadu (Desktop) dan slide-over drawer (Mobile) dengan filter RBAC |
| [`./frontend/src/components/layout/Topbar.tsx`](./frontend/src/components/layout/Topbar.tsx) | Navigasi atas dengan tombol hamburger, breadcrumb dinamis, dan role badge |
| [`./frontend/src/components/layout/AppShell.tsx`](./frontend/src/components/layout/AppShell.tsx) | Shell pembungkus halaman dashboard dengan tata letak responsif 3-Tier |
| [`./frontend/src/test-utils.tsx`](./frontend/src/test-utils.tsx) | Helper pengujian Vitest + RTL dengan pembungkus router dan context auth |
| [`./frontend/src/__tests__/AppShell.responsive.test.tsx`](./frontend/src/__tests__/AppShell.responsive.test.tsx) | Suite pengujian TDD interaksi buka-tutup drawer mobile dan pengujian RBAC |

---

### Hasil Verifikasi Test

```text
$ npm --prefix frontend test -- --run src/__tests__/AppShell.responsive.test.tsx

 RUN  v2.1.9 D:/Kuliah/SKRIPSI/BANSOS_SAW+LLM/frontend

 ✓ src/__tests__/AppShell.responsive.test.tsx (4 tests) 268ms
   ✓ toggles mobile drawer via hamburger button and closes via backdrop
   ✓ enforces RBAC: hides mutation actions from Viewer (Lurah) and displays approval menu
   ✓ enforces RBAC: allows Super Admin to see all governance modules including SAW execution and weight config
   ✓ enforces RBAC: scopes Surveyor (Ketua RT) strictly to RT operations

 Test Files  1 passed (1)
      Tests  4 passed (4)
   Start at  17:35:46
   Duration  1.86s

# Verifikasi Kompilasi TypeScript & Build Produksi Vite:
$ npm --prefix frontend run build

vite v6.4.4 building for production...
transforming...
✓ 1585 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.99 kB │ gzip:  0.55 kB
dist/assets/index-BuKRZx9V.css   16.09 kB │ gzip:  3.87 kB
dist/assets/index-6PmxP5Vj.js   184.65 kB │ gzip: 59.21 kB
✓ built in 2.43s
```

---

## Dokumentasi Branch Sebelumnya

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
