# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m4-api-responsive-ui` (Fase 4 / Task 4 — REST API Endpoints, RBAC Guards, Excel Ingest/Export, & Public Portal Shield)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Setelah Fase 1 (Kriptografi & Model), Fase 2 (Engine SAW & Tie-Breaker), dan Fase 3 (Sanitasi Zero-PII & Explainer XAI Gemini), Fase 4 menghubungkan seluruh inti komputasi dengan antarmuka web melalui **lapisan REST API standar Django REST Framework (DRF)** sesuai **PRD Bagian 10**, **[ADR-004](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md)**, dan **[ADR-005](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md)**:

1. **Role-Based Access Control (RBAC) Ketat & Scoping Wilayah (OWASP A01):**
   - **Super Admin (Kasi Kesos):** Akses penuh untuk pembaruan kriteria, pembuatan batch, eksekusi kalkulasi SAW, penjadwalan narasi XAI, dan publikasi batch ke publik.
   - **Surveyor (Ketua RT):** Akses dibatasi ketat (*hard-scoped*) hanya pada nomor RT wilayahnya sendiri (`request.user.rt_number`). Dilarang keras membaca, menambah, atau mengimpor data warga RT lain, serta dilarang mengakses mutasi alur seleksi.
   - **Viewer (Lurah):** Akses *read-only* terhadap seluruh metrik, peringkat, dan narasi, dengan hak mutasi eksklusif hanya untuk menyetujui (*Approve*) batch yang telah berstatus `Narrated`.
2. **Ingest Massal & Ekspor Rekapitulasi Excel Berstandar UU PDP:**
   - Menyediakan endpoint import berkas `.xlsx` dengan pelaporan error baris granular, penolakan baris RT silang, deduplikasi instan via `nik_hash` $O(1)$, pembatasan ukuran berkas (maksimal 5 MB / 1.000 baris), serta penjagaan status batch (`Draft` atau `Collecting`).
   - Menyediakan endpoint ekspor rekapitulasi hasil seleksi dalam format `.xlsx` resmi kelurahan.
3. **Perisai Anti-Bot & Anti-Enumerasi Portal Publik (`/api/public/check-status/`):**
   - Mengimplementasikan alur verifikasi berlapis tanpa login (passwordless) menggunakan 16 digit NIK + 4 digit terakhir No KK + Cloudflare Turnstile CAPTCHA.
   - Mengatur urutan evaluasi pertahanan (*defense ordering*) presisi: verifikasi CAPTCHA terlebih dahulu sebelum menaikkan penghitung kegagalan NIK guna mencegah serangan DoS/Lockout massal oleh bot.
   - Pembatasan laju IP (5 permintaan/menit/IP) dan *lockout* 15 menit setelah 5 kali salah input KK berturut-turut pada NIK yang sama (bahkan jika penyerang berganti-ganti alamat IP).
   - Mengembalikan HTTP 404 generik jika data tidak cocok atau batch belum berstatus `Published` demi mencegah kebocoran informasi (*zero-enumeration*).

---

### Changelog Fase 4 (Task 4)

#### Added
- **RBAC & RT-Scoping Permissions ([`backend/core/permissions.py`](./backend/core/permissions.py)):**
  - `IsSuperAdmin`, `IsSurveyor`, `IsViewer`, `IsSuperAdminOrViewer`, `IsSuperAdminOrSurveyor`, `IsStaff`.
  - Helper validasi dan normalisasi RT: `normalize_rt()` dan `check_surveyor_rt_scope(request, rt_number)`.
- **Layanan Ingest & Ekspor Excel ([`backend/core/services/excel_ingest.py`](./backend/core/services/excel_ingest.py)):**
  - `import_citizens_from_excel(batch_id, file_obj, user)`: Parsing `.xlsx` aman dengan openpyxl, validasi header kanonik, pelaporan baris error, pencegahan duplikasi NIK via `nik_hash`, kepatuhan enkripsi AES-256-GCM, guard batas status batch (`Draft`/`Collecting`), batas file 5 MB / 1.000 baris, dan penegakan RT surveyor.
  - `export_batch_results_xlsx(batch_id)`: Ekspor ringkasan hasil kalkulasi dan pemeringkatan SAW ke lembar kerja Excel berformat rapi.
- **Perisai Portal Publik & Rate Limiter ([`backend/core/services/rate_limiter.py`](./backend/core/services/rate_limiter.py)):**
  - `verify_turnstile_captcha(token, remote_ip)`: Verifikasi Cloudflare Turnstile CAPTCHA dengan mode fail-closed di produksi dan bypass aman saat testing/debug.
  - `check_ip_rate_limit(ip_address)`: Throttle 5 req/menit per IP via Django Cache.
  - `check_nik_lockout(nik_hash)`: Cek status lockout 15 menit per `nik_hash`.
  - `record_nik_failed_attempt(nik_hash)` & `reset_nik_failed_attempts(nik_hash)`: Penghitung kegagalan berturut-turut lintas IP.
- **REST API Serializers ([`backend/core/serializers.py`](./backend/core/serializers.py)):**
  - `LoginSerializer`, `StaffUserSerializer`, `CriteriaSerializer`, `CriteriaBatchUpdateSerializer` (dengan validasi jumlah bobot tepat 1.0000 dan rentang 0.0001–1.0000), `PeriodSerializer`, `SelectionBatchSerializer`, `CitizenCreateSerializer`, `SelectionResultItemSerializer`, `PublicCheckStatusRequestSerializer`.
- **REST API Views ([`backend/core/views.py`](./backend/core/views.py)):**
  - `StaffLoginRateThrottle` & `StaffLoginView`: Login staf dengan JWT token, informasi role, dan scoping RT.
  - `CriteriaListView` & `CriteriaBatchUpdateView`: Pengelolaan master kriteria dan pembaharuan bobot.
  - `BatchListCreateView`: Daftar periode/batch dan pembuatan batch baru.
  - `CitizenCreateView` & `CitizenImportExcelView`: Registrasi pemohon bansos individual dan impor massal Excel.
  - `SelectionMarkRtSubmittedView`: Penguncian pengumpulan data tingkat RT (`is_rt_submitted = True`).
  - `SelectionCalculateView`: Pemicu engine SAW dan pembekuan bobot kriteria.
  - `SelectionResultsListView`: Pengambilan hasil perangkingan, skor preferensi, dan status kuota.
  - `SelectionGenerateXaiView` & `SelectionXaiProgressView`: Pemicu antrean tugas asinkron XAI dan pemantauan progres narasi.
  - `SelectionApproveView`: Persetujuan batch eksklusif oleh Lurah (`VIEWER`).
  - `SelectionPublishView`: Publikasi batch ke publik eksklusif oleh Super Admin (`SUPER_ADMIN`).
  - `SelectionExportExcelView`: Pengunduhan rekapitulasi Excel.
  - `PublicCheckStatusView`: Pemeriksaan status bantuan sosial transparan oleh masyarakat dengan perlindungan anti-bot berlapis.
- **Routing URL ([`backend/core/urls.py`](./backend/core/urls.py) & [`backend/config/urls.py`](./backend/config/urls.py)):**
  - Pendaftaran prefix `/api/` terpadu untuk seluruh rute internal dan publik.
- **Suite Pengujian TDD & Audit RBAC/Security ([`backend/tests/test_api_endpoints.py`](./backend/tests/test_api_endpoints.py)):**
  - 15 pengujian integrasi end-to-end yang menguji autentikasi JWT, hak akses RBAC, isolasi RT, alur state machine seleksi, impor/ekspor Excel, dan ketahanan pertahanan portal publik.

#### Security
- **OWASP A01 (Broken Access Control) & IDOR Mitigation:** Surveyor terisolasi pada wilayah RT miliknya sendiri; Lurah tidak dapat mengubah kriteria atau mengeksekusi kalkulasi SAW; Super Admin adalah satu-satunya peran yang berhak memublikasikan hasil seleksi.
- **Pertahanan Berlapis Anti-Bot & Anti-Enumerasi NIK:**
  1. *Turnstile CAPTCHA Guard*: Gagalkan bot secara instan tanpa membebani penghitung NIK (mencegah DoS lockout terhadap warga sah).
  2. *IP Rate Limiting*: Maksimal 5 permintaan per menit per alamat IP.
  3. *Per-NIK Distributed Lockout*: 15 menit penguncian setelah 5 kegagalan validasi No KK pada NIK yang sama.
  4. *Generic 404 Response*: Merespons dengan pesan seragam tanpa membocorkan apakah NIK terdaftar pada sistem jika batch belum `Published` atau data tidak cocok.
- **UU PDP No. 27/2022 Kepatuhan At-Rest & Transit:** NIK selalu disimpan dalam bentuk terenkripsi (`nik_encrypted`) dan ter-hash (`nik_hash`); respons publik portal hanya menampilkan penyamaran visual (`367403******0002` dan `Ahmad S******`).
- **Hardening Hasil Audit `security-auditor`:** Pembatasan ukuran unggah Excel 5 MB, batas 1.000 baris, pemblokiran token CAPTCHA dummy di lingkungan produksi (fail-closed jika `TURNSTILE_SECRET_KEY` tidak dikonfigurasi), serta pencegahan penimpaan data warga RT lain.

#### Changed
- [`backend/core/models.py`](./backend/core/models.py): Menambahkan properti alias ORM (`batch_number` pada `SelectionBatch`, `crips_value` pada `EvaluationDetail`, `actor`/`notes` pada `AuditLog`) untuk keseragaman pemanggilan API.
- [`backend/config/settings.py`](./backend/config/settings.py): Mengonfigurasi throttling default `auth_login` menjadi `10/min` dengan dukungan fallback parser cerdas `StaffLoginRateThrottle` untuk durasi interval format kustom (`10/15m`).

---

### Direktori REST API Endpoints (PRD Bagian 10)

| Endpoint | Method | Role Akses | Deskripsi & Guard |
| :--- | :--- | :--- | :--- |
| `/api/auth/login/` | `POST` | Public / All | Otentikasi staf, pengembalian token JWT, role, & RT scope |
| `/api/criteria/` | `GET` | `IsStaff` | Melihat daftar kriteria aktif & bobot master |
| `/api/criteria/batch-update/` | `PUT` | `SUPER_ADMIN` | Pembaharuan bobot kriteria ($\sum w_j = 1.0000$) |
| `/api/batches/` | `GET`, `POST` | `GET`: `IsStaff`<br>`POST`: `SUPER_ADMIN` | Melihat daftar batch atau membuat batch seleksi baru |
| `/api/citizens/` | `POST` | `SUPER_ADMIN`, `SURVEYOR` | Menambahkan data warga (Surveyor dibatasi pada RT-nya) |
| `/api/citizens/import-excel/` | `POST` | `SUPER_ADMIN`, `SURVEYOR` | Impor massal berkas `.xlsx` pemohon bansos (max 5 MB, 1.000 baris) |
| `/api/selection/{id}/mark-rt-submitted/` | `POST` | `SUPER_ADMIN`, `SURVEYOR` | Mengunci status submit pengumpulan data RT |
| `/api/selection/{id}/calculate/` | `POST` | `SUPER_ADMIN` | Eksekusi engine SAW, pembekuan bobot, & status `Calculated` |
| `/api/selection/{id}/results/` | `GET` | `IsStaff` | Mengambil hasil ranking, nilai preferensi, & status kuota |
| `/api/selection/{id}/generate-xai/` | `POST` | `SUPER_ADMIN` | Memicu worker asinkron penjelasan XAI Gemini & fallback |
| `/api/selection/{id}/xai-progress/` | `GET` | `IsStaff` | Memantau progres narasi XAI & status transisi `Narrated` |
| `/api/selection/{id}/approve/` | `PATCH` | `VIEWER` (Lurah) | Pengesahan/persetujuan batch oleh Lurah (status `Narrated` $\rightarrow$ `Approved`) |
| `/api/selection/{id}/publish/` | `PATCH` | `SUPER_ADMIN` | Publikasi batch ke portal publik (status `Approved` $\rightarrow$ `Published`) |
| `/api/selection/{id}/export-excel/` | `GET` | `IsStaff` | Mengunduh lembar rekapitulasi hasil seleksi dalam format `.xlsx` |
| `/api/public/check-status/` | `POST` | Public | Pengecekan mandiri status bansos warga dengan perisai anti-bot |

---

### Matriks Role-Based Access Control (RBAC)

```
+------------------------------------+-------------+--------------------+----------------+--------+
| Operasi / Endpoint                 | Super Admin | Surveyor (Ketua RT)| Viewer (Lurah) | Publik |
+------------------------------------+-------------+--------------------+----------------+--------+
| Login & Dapatkan Token JWT         |      V      |         V          |       V        |   -    |
| Kelola & Edit Bobot Kriteria       |      V      |         -          |       -        |   -    |
| Buat Periode / Batch Baru          |      V      |         -          |       -        |   -    |
| Entri & Impor Warga (.xlsx)        |      V      |  V (Scoped RT-nya) |       -        |   -    |
| Kunci Pengumpulan Data RT          |      V      |  V (Scoped RT-nya) |       -        |   -    |
| Eksekusi Kalkulasi SAW             |      V      |         -          |       -        |   -    |
| Lihat Hasil Ranking & Matriks      |      V      |         V          |       V        |   -    |
| Generate Narasi XAI Gemini         |      V      |         -          |       -        |   -    |
| Approve Batch Seleksi              |      -      |         -          |       V        |   -    |
| Publish Batch ke Publik            |      V      |         -          |       -        |   -    |
| Ekspor Rekapitulasi Excel          |      V      |         V          |       V        |   -    |
| Cek Status Mandiri (/cek-bansos)   |      -      |         -          |       -        |   V    |
+------------------------------------+-------------+--------------------+----------------+--------+
```

---

### Arsitektur Perisai Portal Publik (`/api/public/check-status/`)

```
   Permintaan Publik (NIK, No KK 4-digit, CAPTCHA Token)
                         │
                         ▼
        [ 1. Verifikasi Turnstile CAPTCHA ]
       Gagal ──► HTTP 403 Forbidden (Counter NIK TIDAK naik)
                         │ Lolos
                         ▼
        [ 2. Throttle IP (5 req/menit/IP) ]
       Batas Tercapai ──► HTTP 429 Too Many Requests
                         │ Lolos
                         ▼
        [ 3. Cek Lockout NIK (15 Menit) ]
       Sedang Lockout ──► HTTP 429 Too Many Requests
                         │ Lolos
                         ▼
        [ 4. Validasi Format NIK (16-Digit) ]
       Tidak Valid ──► HTTP 400 Bad Request
                         │ Lolos
                         ▼
     [ 5. Hash NIK (HMAC-SHA256) & Pencarian DB ]
       Tidak Ditemukan / KK Salah ──► Catat Gagal (+1) ──► HTTP 404 Not Found
                         │                                 (Jika 5x ──► Lockout 15m)
                         ▼
     [ 6. Periksa Status Batch Seleksi ]
       Batch Belum "Published" ──► HTTP 404 Not Found (Zero-Enumeration)
                         │
                         ▼
     [ 7. Kembalikan Payload Publik Zero-PII ]
       (Masked NIK/Nama, Status, Skor, Narasi XAI, & Download Token PDF)
```

---

### Daftar File Fase 4

| File | Tanggung Jawab |
| :--- | :--- |
| [`./backend/core/permissions.py`](./backend/core/permissions.py) | Definisi perizinan RBAC DRF dan validasi lingkup nomor RT surveyor |
| [`./backend/core/services/excel_ingest.py`](./backend/core/services/excel_ingest.py) | Ingest berkas Excel pemohon bansos, deduplikasi `nik_hash`, dan ekspor rekapitulasi |
| [`./backend/core/services/rate_limiter.py`](./backend/core/services/rate_limiter.py) | Verifikasi Cloudflare Turnstile, throttle IP, dan penguncian NIK 15 menit |
| [`./backend/core/serializers.py`](./backend/core/serializers.py) | Serializer DRF untuk autentikasi, kriteria, batch, warga, hasil, dan portal publik |
| [`./backend/core/views.py`](./backend/core/views.py) | Kontroller endpoint REST API lengkap PRD Bagian 10 |
| [`./backend/core/urls.py`](./backend/core/urls.py) | Pemetaan rute URL API internal dan publik |
| [`./backend/config/urls.py`](./backend/config/urls.py) | Integrasi rute `/api/` pada konfigurasi utama Django |
| [`./backend/config/settings.py`](./backend/config/settings.py) | Konfigurasi throttling DRF dan integrasi SimpleJWT |
| [`./backend/core/models.py`](./backend/core/models.py) | Penambahan properti alias model ORM |
| [`./backend/tests/test_api_endpoints.py`](./backend/tests/test_api_endpoints.py) | 15 unit dan integration test REST API, RBAC, Excel, dan perisai publik |

---

### Hasil Verifikasi Test

```text
$ backend/.venv/Scripts/python.exe -m pytest backend/tests/test_api_endpoints.py -v

backend\tests\test_api_endpoints.py::test_staff_login_success_and_jwt_payload PASSED [  6%]
backend\tests\test_api_endpoints.py::test_staff_login_invalid_credentials PASSED [ 13%]
backend\tests\test_api_endpoints.py::test_criteria_list_and_batch_update_rbac PASSED [ 20%]
backend\tests\test_api_endpoints.py::test_batches_list_and_create_rbac PASSED [ 26%]
backend\tests\test_api_endpoints.py::test_citizen_single_create_surveyor_rt_scope PASSED [ 33%]
backend\tests\test_api_endpoints.py::test_citizens_import_excel_deduplication_and_surveyor_scoping PASSED [ 40%]
backend\tests\test_api_endpoints.py::test_selection_calculate_and_results_rbac PASSED [ 46%]
backend\tests\test_api_endpoints.py::test_selection_generate_xai_and_progress PASSED [ 53%]
backend\tests\test_api_endpoints.py::test_selection_approval_and_publish_state_machine_rbac PASSED [ 60%]
backend\tests\test_api_endpoints.py::test_export_batch_results_excel PASSED [ 66%]
backend\tests\test_api_endpoints.py::test_public_check_status_blocks_unpublished_batch PASSED [ 73%]
backend\tests\test_api_endpoints.py::test_public_check_status_captcha_fail_does_not_increment_lockout PASSED [ 80%]
backend\tests\test_api_endpoints.py::test_public_check_status_ip_rate_limit PASSED [ 86%]
backend\tests\test_api_endpoints.py::test_public_check_status_nik_lockout_across_ips PASSED [ 93%]
backend\tests\test_api_endpoints.py::test_public_check_status_success_payload_structure PASSED [100%]

======================= 15 passed, 1 warning in 46.75s =======================

# Verifikasi Regresi Keseluruhan Seluruh Suite Pengujian Backend:
$ backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v
================== 89 passed, 1 warning in 67.57s (0:01:07) ==================
```

---

## Dokumentasi Branch Sebelumnya

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
- **Daftar ADR:**
  1. [ADR-001: Hybrid SAW + XAI & Deterministic Fallback](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md)
  2. [ADR-002: Dual-Layer NIK Crypto & Zero-PII XAI](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md)
  3. [ADR-003: Immutable Criteria Snapshot, TMS Gate, & Tie-Breaker](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md)
  4. [ADR-004: Async XAI Queue & Passwordless Public Portal](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md)
  5. [ADR-005: Responsive UI Architecture & Stitch Review Gate](./docs/decisions/ADR-005-responsive-ui-architecture-and-stitch-review-gate.md)

---

## Catatan Penting (Known Gotchas)

- **Isolasi Wilayah RT Surveyor:** Jangan mengizinkan pengguna ber-role `SURVEYOR` membaca atau memodifikasi data warga selain RT wilayahnya sendiri.
- **Urutan Perisai Portal Publik:** Selalu validasi CAPTCHA Turnstile sebelum menaikkan counter lockout NIK untuk mencegah serangan DoS terhadap warga sah.
- **Format Durasi Throttling DRF:** DRF throttle parser standar hanya memeriksa karakter pertama satuan waktu (`s`, `m`, `h`, `d`). Gunakan subclass `StaffLoginRateThrottle` untuk menangani string interval seperti `10/15m`.
- **Zero-Enumeration pada Portal Publik:** Batch yang belum berstatus `Published` wajib mengembalikan HTTP 404 generik persis sama seperti data warga yang tidak ditemukan.
