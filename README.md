# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m5-pdf-reporting` (Fase 5 / Task 5 — PDF Berita Acara Generator with QR & TMS Appendix & Thesis Evaluation Metrics)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 5 merealisasikan lapisan pelaporan resmi (*Official Reporting Layer*) dan instrumen pengujian skripsi (*Academic Evaluation Instruments*) sesuai **PRD Bagian 1, 10, dan 11**, **[ADR-002](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md)**, dan **[ADR-006](./docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md)**:

1. **Pelaporan Hukum Administrasi Pemerintahan (Berita Acara Resmi):**
   - Penetapan bantuan sosial membutuhkan berkas fisik berkekuatan hukum yang ditandatangani oleh **Lurah Jurangmangu Barat** dan **Kasi Kesejahteraan Sosial**.
   - Berkas ini memuat Kop Surat resmi Pemerintah Kota Tangerang Selatan, tabel penetapan penerima yang lolos kuota, tanda tangan basah/stempel kelurahan, lampiran terpisah warga yang berstatus Tidak Memenuhi Syarat (TMS / `DISQUALIFIED`), serta **QR Code** untuk validasi integritas dan keaslian dokumen secara daring.
2. **Dekripsi NIK Terkontrol Ketat (Kepatuhan UU PDP No. 27/2022):**
   - Penyaluran bantuan sosial secara administratif mewajibkan 16-digit NIK asli pada lembar Berita Acara resmi kelurahan.
   - Sistem menetapkan aturan ketat: **dekripsi `nik_encrypted` (AES-256-GCM) HANYA dan HANYA diizinkan pada saat pencetakan Berita Acara PDF ini**.
   - Setiap operasi dekripsi dicatat secara permanen ke tabel `AuditLog` (`action=NIK_DECRYPT`) tanpa pernah membocorkan NIK plaintext ke dalam catatan audit.
3. **Pemberitahuan Transparansi Warga (Zero-PII Public Document):**
   - Warga yang memeriksa status bantuan di portal publik (`/cek-bansos`) dapat mengunduh surat pemberitahuan hasil seleksi mandiri.
   - Dokumen publik ini menerapkan **penyamaran visual 100% (`nik_masked` dan `full_name_masked`)**, memuat penjelasan transparansi XAI Gemini, matriks perbandingan nilai terhadap rata-rata lolos, serta dilindungi token unduhan kriptografis yang hanya aktif jika batch telah berstatus resmi `Published`.
4. **Instrumen Pengujian Skripsi Otomatis (Bab 4 & Bab 5):**
   - **Fidelity Score (PRD Bagian 11.2):** Mengukur kesetiaan narasi LLM terhadap kriteria penentu dengan kesenjangan terbobot terbesar $\operatorname{argmax}_j (\Delta_{i,j} \cdot w_j)$ berbasis snapshot bobot beku `BatchCriteria.frozen_weight`. Sistem menangani kondisi batas $|K_{\text{TL}}| == 0$ (seluruh peserta lolos) dengan nilai `100.0%` secara aman tanpa `ZeroDivisionError`.
   - **Hallucination Rate (PRD Bagian 11.2):** Mendeteksi kriteria fiktif (seperti `C99` atau `Daya Listrik 900 VA`) dan angka desimal palsu, dengan normalisasi cerdas terhadap format desimal koma Bahasa Indonesia (`0,684` $\rightarrow$ `0.684`) dan persentase (`60%` $\rightarrow$ `0.60`).
   - **Instrumen Kuesioner SUS & Ekspor Dataset:** Menyediakan template 10 butir pertanyaan *System Usability Scale* (SUS) standar berbahasa Indonesia serta fungsi ekspor multi-sheet dataset pengujian ke lembar kerja Excel (`.xlsx`).

---

### Changelog Fase 5 (Task 5)

#### Added
- **Generator Dokumen PDF Resmi ([`backend/core/services/pdf_generator.py`](./backend/core/services/pdf_generator.py)):**
  - `generate_berita_acara_pdf(batch_id, performed_by)`: Menghasilkan Berita Acara legal format A4 menggunakan ReportLab v5.0.1, lengkap dengan Kop Surat Kelurahan Jurangmangu Barat, garis ganda pembatas, tabel perangkingan KPM lolos kuota, pencatatan otomatis `AuditLog` dekripsi NIK, blok tanda tangan formal Kasi Kesos & Lurah, lampiran khusus warga TMS (`DISQUALIFIED`), dan QR Code verifikasi dokumen.
  - `generate_individual_result_pdf(evaluation_id)`: Menghasilkan lembar bukti pengumuman kelayakan mandiri untuk warga via portal publik dengan penegakan masking visual PII 100%, status keputusan, skor cutoff, narasi XAI, matriks kriteria terbobot, dan QR Code verifikasi.
- **Layanan Metrik Evaluasi Skripsi ([`backend/core/services/evaluation_metrics.py`](./backend/core/services/evaluation_metrics.py)):**
  - `compute_batch_evaluation_metrics(batch_id)`: Perhitungan kuantitatif otomatis untuk *Fidelity Score*, *Hallucination Rate*, rincian kandidat lolos/tidak lolos/TMS, serta penjagaan pembagian nol saat $|K_{\text{TL}}| == 0$.
  - `detect_narrative_hallucinations(...)`: Filter deteksi halusinasi kode kriteria asing, istilah kriteria terlarang, rekayasa angka peringkat/kuota, dan angka desimal di luar payload input dengan normalisasi koma desimal Indonesia.
  - `get_sus_questionnaire_template()`: Template kuesioner baku 10 pertanyaan System Usability Scale (Brooke, 1996) berbahasa Indonesia dengan polaritas bergantian (+ / -) dan skala Likert 1–5.
  - `export_thesis_evaluation_dataset(batch_id)` & `export_thesis_evaluation_dataset_xlsx(batch_id)`: Ekspor dataset evaluasi akademik lengkap ke lembar kerja Excel multi-sheet (Sheet 1: Data Uji & Evaluasi, Sheet 2: Ringkasan Metrik, Sheet 3: Instrumen SUS).
- **REST API Endpoints ([`backend/core/views.py`](./backend/core/views.py) & [`backend/core/urls.py`](./backend/core/urls.py)):**
  - `GET /api/selection/{batch_id}/berita-acara-pdf/`: Unduh PDF Berita Acara resmi (hak akses `SUPER_ADMIN` dan `VIEWER` / Lurah).
  - `GET /api/public/result-pdf/?token=<signed_token>`: Unduh surat bukti seleksi warga portal publik dengan verifikasi token berstempel waktu (TTL 15 menit) pada batch berstatus `Published`.
  - `GET /api/selection/{batch_id}/evaluation-metrics/`: Ringkasan metrik evaluasi skripsi dalam format JSON atau format workbook Excel (`?format=xlsx`).
- **Suite Pengujian TDD ([`backend/tests/test_pdf_and_evaluation.py`](./backend/tests/test_pdf_and_evaluation.py)):**
  - 9 pengujian komprehensif menguji formula Fidelity, normalisasi desimal Hallucination, penanganan $|K_{\text{TL}}| == 0$, Berita Acara PDF, masking PII dokumen publik warga, perizinan RBAC, dan validasi token kedaluwarsa.
- **Architecture Decision Record ([`docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md`](./docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md)):**
  - Dokumentasi keputusan arsitektur dekripsi terkontrol Berita Acara PDF, perlindungan zero-PII publik, dan metrik skripsi.

#### Security
- **UU PDP No. 27/2022 (Dekripsi NIK Terkontrol):** Dekripsi ciphertext `nik_encrypted` menggunakan AES-256-GCM hanya terjadi pada saat eksekusi `generate_berita_acara_pdf()`. Setiap dekripsi memicu pembuatan entri `AuditLog` dengan aksi `action=AuditLog.Action.NIK_DECRYPT`. Kolom `detail` dan `performed_by` divalidasi tidak boleh memuat NIK plaintext 16 digit.
- **Zero-PII Public Download:** Endpoint `/api/public/result-pdf/` tidak pernah mendekripsi NIK. Dokumen yang dihasilkan selalu menggunakan `nik_masked` (`367403******0002`) dan `full_name_masked` (`Ahmad S******`).
- **Cryptographic Token Verification:** Endpoint publik mewajibkan query parameter `token` yang divalidasi melalui `verify_pdf_download_token(token)` (Django TimestampSigner dengan salt `bansos.pdf_download` dan TTL 15 menit). Unduhan ditolak dengan HTTP 403 jika token tidak sah, kedaluwarsa, atau batch belum berstatus `Published`.

#### Changed
- [`backend/core/views.py`](./backend/core/views.py): Mengintegrasikan penanganan token unduhan PDF, layanan pembuatan PDF, dan ekspor metrik evaluasi.
- [`backend/core/urls.py`](./backend/core/urls.py): Menambahkan rute `/api/selection/{batch_id}/berita-acara-pdf/`, `/api/selection/{batch_id}/evaluation-metrics/`, dan `/api/public/result-pdf/`.

---

### Mekanisme Dekripsi Terkontrol Berita Acara PDF & QR Code & Lampiran TMS

```
  Staf Berwenang (Lurah / Kasi Kesos)
                 │
                 ▼
 [ GET /api/selection/{id}/berita-acara-pdf/ ]
                 │
                 ├─► [ 1. Verifikasi RBAC: SUPER_ADMIN / VIEWER ]
                 │
                 ▼
 [ 2. Query Batch, KPM Lolos, & Warga TMS ]
                 │
                 ▼
 [ 3. Dekripsi Terkontrol NIK (AES-256-GCM) ]
      citizen.decrypt_nik() khusus untuk baris Berita Acara
                 │
                 ▼
 [ 4. Catat AuditLog Mutasi Legal ]
      action: NIK_DECRYPT, actor: username, detail: zero-PII
                 │
                 ▼
 [ 5. Render ReportLab PDF Engine (In-Memory io.BytesIO) ]
      ├─ Kop Surat Pemkot Tangerang Selatan & Kelurahan Jurangmangu Barat
      ├─ Tabel Penetapan KPM Lolos Kuota (Peringkat, NIK, Nama, Skor V)
      ├─ Tanda Tangan Resmi Kasi Kesos & Lurah Jurangmangu Barat
      ├─ QR Code Verifikasi Keaslian Dokumen
      └─ [ PageBreak ] ──► Lampiran I: Warga TMS (DISQUALIFIED & Alasan)
                 │
                 ▼
 [ 6. Response Stream: application/pdf ]
      Content-Disposition: attachment; filename="Berita_Acara_Seleksi_Batch_...pdf"
```

---

### Formula Evaluasi Skripsi (PRD Bagian 11.2)

1. **Fidelity Score ($F_{\text{score}}$):**
   $$\text{Fidelity Score} = \frac{1}{|K_{\text{TL}}|} \sum_{i \in K_{\text{TL}}} \mathbb{I}\left( C_{\text{AI\_primary}}(i) == \operatorname{argmax}_j (\Delta_{i,j} \cdot w_j) \right)$$
   - $K_{\text{TL}}$: Himpunan calon KPM berstatus Tidak Lolos.
   - $\Delta_{i,j} = \bar{r}_j^{\text{lolos}} - r_{ij}$: Kesenjangan nilai normalisasi terhadap rata-rata penerima lolos pada kriteria $j$.
   - $w_j$: Bobot kriteria beku dari `BatchCriteria.frozen_weight`.
   - *Zero-Division Guard*: Jika $|K_{\text{TL}}| == 0$ (seluruh peserta lolos), sistem mengembalikan `100.0%` secara deterministik.
   - **Target PRD:** $F_{\text{score}} \ge 95.0\%$.

2. **Hallucination Rate ($H_{\text{rate}}$):**
   $$H_{\text{rate}} = \frac{N_{\text{invalid}}}{N_{\text{total}}} \times 100\%$$
   - $N_{\text{invalid}}$: Jumlah narasi yang menyebutkan kriteria di luar $\{C_1, \dots, C_n\}$, istilah terlarang, atau angka desimal fiktif di luar payload input.
   - *Normalisasi Format Indonesia*: Desimal koma `0,684` dinormalisasi ke `0.684` dan persentase `60%` dinormalisasi ke `0.60` agar tidak memicu deteksi salah (false-positive).
   - **Target PRD:** $H_{\text{rate}} = 0.0\%$.

---

### Daftar File Fase 5

| File | Tanggung Jawab |
| :--- | :--- |
| [`./backend/core/services/pdf_generator.py`](./backend/core/services/pdf_generator.py) | Generator ReportLab untuk Berita Acara resmi (Kop, QR, TMS) dan dokumen publik warga |
| [`./backend/core/services/evaluation_metrics.py`](./backend/core/services/evaluation_metrics.py) | Perhitungan Fidelity Score, deteksi Hallucination, kuesioner SUS, & ekspor Excel |
| [`./backend/core/views.py`](./backend/core/views.py) | View controller untuk Berita Acara PDF, hasil publik PDF, dan metrik skripsi |
| [`./backend/core/urls.py`](./backend/core/urls.py) | Pendaftaran rute endpoint PDF pelaporan dan metrik skripsi |
| [`./backend/tests/test_pdf_and_evaluation.py`](./backend/tests/test_pdf_and_evaluation.py) | 9 unit & integration tests untuk PDF generator, token publik, dan metrik skripsi |
| [`./docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md`](./docs/decisions/ADR-006-controlled-nik-decryption-pdf-and-thesis-metrics.md) | Catatan keputusan arsitektur dekripsi Berita Acara dan evaluasi akademik |

---

### Hasil Verifikasi Test

```text
$ backend/.venv/Scripts/python.exe -m pytest backend/tests/test_pdf_and_evaluation.py -v

backend\tests\test_pdf_and_evaluation.py::test_fidelity_hallucination_metrics_and_signed_pdf_download PASSED [ 11%]
backend\tests\test_pdf_and_evaluation.py::test_fidelity_score_formula_and_zero_division_guard PASSED [ 22%]
backend\tests\test_pdf_and_evaluation.py::test_hallucination_rate_normalizes_indonesian_decimals_and_percentages PASSED [ 33%]
backend\tests\test_pdf_and_evaluation.py::test_sus_questionnaire_template_and_export_dataset PASSED [ 44%]
backend\tests\test_pdf_and_evaluation.py::test_berita_acara_pdf_generation_content_and_audit_log PASSED [ 55%]
backend\tests\test_pdf_and_evaluation.py::test_individual_result_pdf_generation_masks_pii PASSED [ 66%]
backend\tests\test_pdf_and_evaluation.py::test_berita_acara_pdf_api_endpoint_rbac PASSED [ 77%]
backend\tests\test_pdf_and_evaluation.py::test_public_individual_pdf_endpoint_guards PASSED [ 88%]
backend\tests\test_pdf_and_evaluation.py::test_evaluation_metrics_api_endpoint PASSED [100%]

============================= 9 passed in 12.44s ==============================

# Verifikasi Regresi Keseluruhan Seluruh Suite Pengujian Backend (Task 1 s/d Task 5):
$ backend/.venv/Scripts/python.exe -m pytest backend/ -v
================== 98 passed, 1 warning in 90.44s (0:01:30) ===================
```

---

## Dokumentasi Branch Sebelumnya

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
