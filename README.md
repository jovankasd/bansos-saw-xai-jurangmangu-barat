# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m2-saw-tiebreaker` (Fase 2 / Task 2 — SAW Engine, Criteria Snapshot Freeze, TMS Filter, & 4-Level Tie-Breaker)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Fase 1 meletakkan pondasi kriptografi dan skema basis data. Fase 2 mengimplementasikan **inti algoritma keputusan** sesuai **PRD FR-01 hingga FR-03** dan **[ADR-003](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md)**:

1. **Pembekuan bobot kriteria (`BatchCriteria`)** secara idempoten agar perubahan `Criteria.weight` pasca-kalkulasi tidak merusak histori batch yang sudah dihitung.
2. **Filter TMS (Tidak Memenuhi Syarat)** sebelum menghitung $\min/\max$ normalisasi SAW, sehingga warga `DISQUALIFIED` (ASN/TNI/Polri, PKH Ganda, Pindah, Meninggal) tidak mendistorsi matriks normalisasi.
3. **Algoritma SAW** dengan presisi `Decimal`, rumus normalisasi Benefit/Cost, skor preferensi $V_i$, dan tie-breaker deterministik 4-level yang menjamin hasil seleksi dapat direproduksi secara konsisten.

---

### Changelog Fase 2 (Task 2)

#### Added
- **SAW Engine ([`backend/core/services/saw_engine.py`](./backend/core/services/saw_engine.py)):**
  - `validate_criteria_weights()`: Menolak kalkulasi jika $\sum w_j \neq \text{Decimal}("1.00")$ dengan `ValidationError` bertanda `invalid_weight_sum`.
  - `freeze_batch_criteria(batch)`: Snapshot idempoten (`update_or_create`) ke tabel `BatchCriteria`; mutasi `Criteria.weight` pasca-kalkulasi tidak mengubah `frozen_weight` batch lama.
  - `calculate_batch_saw(batch_id, performed_by)`: Pipeline atomik (`transaction.atomic`) mencakup validasi → freeze → filter TMS → normalisasi → tie-breaker → tulis `SelectionResult` → transisi status → `AuditLog`.
- **4-Level Tie-Breaker ([`backend/core/services/tie_breaker.py`](./backend/core/services/tie_breaker.py)):**
  - `resolve_rankings_with_tie_breaker(candidates, quota)`: Pengurutan deterministik dengan kunci `(-V_i, -r_{C1}, -r_{C2}, -real\_dependents\_count, created\_at, id)` — tanpa `IndexError` pada `quota=0` atau `quota≥len(eligible)`.
- **Suite Pengujian TDD + Edge-Case ([`backend/tests/test_saw_and_tiebreaker.py`](./backend/tests/test_saw_and_tiebreaker.py)):**
  - 27 pengujian otomatis mencakup seluruh aturan bisnis FR-01–FR-03 beserta kasus batas (termasuk pengujian eksplisit Level 1 $C_1$, Level 2 $C_2$, Level 3 Tanggungan Riil, Level 4 Timestamp + `id` ASC, kuota $\le 0$, batch kosong tanpa evaluasi `empty_batch_evaluations`, `raw_crips_value <= 0`, batch ID tidak ditemukan, kandidat kosong, dan penanganan nilai `None`/tipe non-desimal).

#### Security
- **Snapshot Freeze Immutability:** `BatchCriteria.frozen_weight` tidak dapat berubah setelah kalkulasi meski `Criteria.weight` diubah oleh admin — terbukti oleh `test_post_calculation_weight_mutation_does_not_alter_frozen_snapshot`.
- **State Machine Guard:** Kalkulasi ulang pada batch `Approved` atau `Published` langsung ditolak (`ValidationError`) — terbukti oleh `test_approved_batch_rejects_recalculation`.

#### Changed
- Dibangun di atas `feat/m1-crypto-models` — seluruh 20 pengujian Fase 1 & Security tetap lulus tanpa modifikasi.

---

### Rumus Normalisasi SAW & 4-Level Tie-Breaker

#### Normalisasi Matriks $R_{ij}$

| Tipe Kriteria | Rumus Normalisasi |
| :--- | :--- |
| **Benefit** (C2: semakin tinggi semakin baik) | $r_{ij} = \dfrac{x_{ij}}{\max_i x_{ij}}$ |
| **Cost** (C1, C3, C4: semakin rendah semakin baik) | $r_{ij} = \dfrac{\min_i x_{ij}}{x_{ij}}$ |

#### Skor Preferensi $V_i$

$$V_i = \sum_{j=1}^{4} w_j \cdot r_{ij}$$

dimana $w_j$ adalah bobot beku dari `BatchCriteria.frozen_weight` (bukan `Criteria.weight` yang bisa berubah).

#### 4-Level Tie-Breaker (FR-03)

Ketika dua kandidat memiliki $V_i$ yang identik di batas kuota, urutan pemenang ditentukan secara deterministik bertingkat:

| Level | Kriteria Tie-Break | Arah |
| :---: | :--- | :--- |
| **1** | Nilai normalisasi $r_{i, C1}$ (Pendapatan Keluarga) | ↑ Terbesar menang |
| **2** | Nilai normalisasi $r_{i, C2}$ (Jumlah Tanggungan) | ↑ Terbesar menang |
| **3** | `Evaluation.real_dependents_count` (Jumlah Tanggungan Riil) | ↑ Terbesar menang |
| **4** | `Evaluation.created_at` (Timestamp pengusulan) + `id` ASC | ↓ Terlama menang |

---

### Daftar File Fase 2

| File | Tanggung Jawab |
| :--- | :--- |
| [`./backend/core/services/__init__.py`](./backend/core/services/__init__.py) | Package marker untuk modul layanan |
| [`./backend/core/services/saw_engine.py`](./backend/core/services/saw_engine.py) | Pipeline SAW atomik (validasi → freeze → guard batch kosong → filter TMS → normalisasi R_ij/V_i → tie-breaker → tulis hasil) |
| [`./backend/core/services/tie_breaker.py`](./backend/core/services/tie_breaker.py) | Tie-breaker deterministik 4-level defensif terhadap None dengan penanganan `quota<=0` dan `quota>=eligible` |
| [`./backend/tests/test_saw_and_tiebreaker.py`](./backend/tests/test_saw_and_tiebreaker.py) | 27 pengujian TDD mencakup semua aturan bisnis FR-01–FR-03 dan kasus batas |

---

### Hasil Verifikasi Fase 2

```text
$ cd backend ; .\.venv\Scripts\python.exe -m pytest tests/test_saw_and_tiebreaker.py -v

tests/test_saw_and_tiebreaker.py::test_saw_rejects_invalid_weight_sum PASSED
tests/test_saw_and_tiebreaker.py::test_saw_accepts_valid_weight_sum PASSED
tests/test_saw_and_tiebreaker.py::test_freeze_batch_criteria_is_idempotent PASSED
tests/test_saw_and_tiebreaker.py::test_freeze_batch_criteria_captures_current_weights PASSED
tests/test_saw_and_tiebreaker.py::test_post_calculation_weight_mutation_does_not_alter_frozen_snapshot PASSED
tests/test_saw_and_tiebreaker.py::test_tms_disqualified_excluded_from_normalization PASSED
tests/test_saw_and_tiebreaker.py::test_all_tms_batch_raises_validation_error PASSED
tests/test_saw_and_tiebreaker.py::test_incomplete_criteria_raises_validation_error PASSED
tests/test_saw_and_tiebreaker.py::test_saw_normalization_benefit_and_cost_formulas PASSED
tests/test_saw_and_tiebreaker.py::test_saw_excludes_tms_freezes_weights_and_resolves_tie_breaks PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_uses_real_dependents_count_at_level_3 PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_uses_created_at_at_level_4 PASSED
tests/test_saw_and_tiebreaker.py::test_quota_zero_no_index_error PASSED
tests/test_saw_and_tiebreaker.py::test_quota_exceeds_eligible_all_pass PASSED
tests/test_saw_and_tiebreaker.py::test_approved_batch_rejects_recalculation PASSED
tests/test_saw_and_tiebreaker.py::test_published_batch_rejects_recalculation PASSED
tests/test_saw_and_tiebreaker.py::test_calculate_batch_saw_transitions_status_to_calculated PASSED
tests/test_saw_and_tiebreaker.py::test_calculate_batch_saw_creates_audit_log PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_uses_c1_at_level_1 PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_uses_c2_at_level_2 PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_uses_evaluation_id_as_final_tie_breaker PASSED
tests/test_saw_and_tiebreaker.py::test_quota_negative_no_index_error PASSED
tests/test_saw_and_tiebreaker.py::test_empty_batch_evaluations_raises_validation_error PASSED
tests/test_saw_and_tiebreaker.py::test_nonexistent_batch_id_raises_does_not_exist PASSED
tests/test_saw_and_tiebreaker.py::test_invalid_crips_value_nonpositive_raises_validation_error PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_empty_candidates_returns_empty PASSED
tests/test_saw_and_tiebreaker.py::test_tie_breaker_none_and_missing_keys_handled_robustly PASSED

27 passed in 15.42s

# Full suite (Fase 1 + Fase 2 + Security Guardrails):
$ .\.venv\Scripts\python.exe -m pytest tests/ -v
47 passed in 15.27s
```

---

## Dokumentasi Branch: `feat/m1-crypto-models` (Fase 1 / Milestone 1 — Database Schema & UU PDP Cryptographic Layer)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)
Sesuai **UU PDP No. 27 Tahun 2022** dan **[ADR-002](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md)**, Nomor Induk Kependudukan (NIK) adalah data pribadi spesifik yang dilarang disimpan dalam bentuk *plaintext* di basis data maupun dikirim ke API eksternal. Namun, sistem tetap membutuhkan:
1. **Pencarian warga instan ($O(1)$)** saat verifikasi di Portal Publik dan deduplikasi import Excel tanpa mendekripsi seluruh baris tabel (`HMAC-SHA256` di kolom `nik_hash`).
2. **Dekripsi terkontrol** khusus saat pencetakan PDF Berita Acara resmi kelurahan (`AES-256-GCM` di kolom `nik_encrypted`).
3. **Pembekuan bobot kriteria per batch** ([ADR-003](./docs/decisions/ADR-003-immutable-criteria-snapshot-tms-gate-and-tie-breaker.md)) pada tabel `BATCH_CRITERIA` agar perubahan bobot di masa depan tidak merusak histori seleksi lama.

---

### Changelog Fase 1 (Milestone 1)

#### Added
- **Layanan Kriptografi UU PDP ([`backend/core/crypto.py`](./backend/core/crypto.py)):**
  - `encrypt_nik()` & `decrypt_nik()`: Enkripsi *at-rest* `AES-256-GCM` dengan *assertion* ketat kunci 32-byte, *nonce* CSPRNG 12-byte (`os.urandom(12)`), dan validasi *canonical base64url* 60 karakter (44 byte: `12B nonce + 16B NIK + 16B GCM tag`).
  - `hash_nik()`: Indeks pencarian deterministik 64 karakter hex berbasis `HMAC-SHA256` dengan *server-side pepper* (`NIK_HMAC_PEPPER`).
  - `mask_nik()` & `mask_name()`: Masking visual identitas (`367403******0002`, `"Ahmad S******"` untuk nama multi-kata, `"Su*****"` untuk mononim).
  - `sign_pdf_download_token()` & `verify_pdf_download_token()`: Token unduhan PDF individual bertanda tangan `TimestampSigner` dengan masa berlaku 15 menit (`max_age=900`).
- **Model Basis Data 9 Tabel PRD + `StaffUser` ([`backend/core/models.py`](./backend/core/models.py)):**
  - Implementasi penuh skema relasional PRD Bagian 9 beserta `UniqueConstraint` dan `AliasQuerySet` untuk kompatibilitas nama kolom PRD.
- **Management Command Seeder ([`backend/core/management/commands/seed_initial_data.py`](./backend/core/management/commands/seed_initial_data.py)):**
  - Pengisian idempoten kriteria `C1–C4`, sub-kriteria Crips `1–5`, akun staf demo (`SUPER_ADMIN`, `SURVEYOR`, `VIEWER`), dan periode awal.
- **Suite Pengujian TDD & Adversarial ([`backend/tests/test_crypto_and_models.py`](./backend/tests/test_crypto_and_models.py)):**
  - 15 pengujian otomatis yang mencakup roundtrip kriptografi, *tampered/malleable ciphertext*, digit Unicode non-ASCII, idempotensi upsert, dan proteksi ORM.

#### Security
- **Proteksi At-Rest Menyeluruh pada ORM (`Citizen.clean()` & `CitizenQuerySet`):** Menolak penyimpanan 16 digit NIK *plaintext* atau *ciphertext* tidak valid baik melalui `.save()`, `.bulk_create()`, maupun `QuerySet.update()`.
- **Audit Trail Zero-PII (`AuditLog.clean()`):** Mencegah pencatatan NIK *plaintext* ke tabel `audit_log`.
- **Audit Subagent `security-auditor`:** Lulus pemeriksaan kepatuhan UU PDP No. 27/2022 dengan **0 temuan Critical/High/Medium**.

#### Changed
- **Penyelarasan Atribut `C3` (Kondisi Tempat Tinggal):** Ditetapkan sebagai `COST` (bobot `0.25`) sesuai PRD Bagian 8.1, dengan urutan Crips `1` (*Tidak Layak/Darurat* $\rightarrow r = 1.00$) hingga Crips `5` (*Sangat Layak/Permanen* $\rightarrow r = 0.20$).

---

### Arsitektur Skema Basis Data (9 Tabel PRD + `StaffUser`)

| Model / Tabel | Tanggung Jawab Utama & Constraint |
| :--- | :--- |
| `StaffUser` (`staff_user`) | Akun internal kelurahan dengan RBAC (`SUPER_ADMIN`, `SURVEYOR` per RT, `VIEWER`). |
| `Criteria` (`criteria`) | Master kriteria `C1–C4` (`COST` / `BENEFIT`) dan bobot aktif (`weight`). |
| `SubCriteria` (`subcriteria`) | Definisi skala Crips `1..5` per kriteria (`uq_subcriteria_criteria_value`). |
| `BatchCriteria` (`batch_criteria`) | Snapshot bobot beku (`frozen_weight`) per batch seleksi (`uq_batch_criteria`). |
| `Citizen` (`citizen`) | Data warga terenkripsi (`nik_hash`, `nik_encrypted`, `nik_masked`, `kk_last4`, `full_name_masked`). |
| `Period` (`period`) | Periode pelaksanaan seleksi bansos (Semester/Tahun). |
| `SelectionBatch` (`selection_batch`) | *State machine* batch (`Draft -> Collecting -> Calculated -> Narrated -> Approved -> Published`). |
| `Evaluation` (`evaluation`) | Penilaian warga per batch (`uq_evaluation_batch_citizen`), status TMS, & `real_dependents_count` (Tie-Breaker Level 3). |
| `EvaluationDetail` (`evaluation_detail`) | Nilai mentah Crips (`1..5`) dan skor normalisasi `normalized_value` (`uq_evaluation_detail`). |
| `SelectionResult` (`selection_result`) | Skor akhir SAW (`final_score_v`), `ranking`, `tie_break_level`, dan narasi XAI (`ai_narrative`). |
| `AuditLog` (`audit_log`) | Jejak audit operasi sensitif (dekripsi PDF, kalkulasi SAW, pengesahan batch) bebas PII. |

### Konfigurasi Awal Kriteria (`seed_initial_data.py`)

| Kode | Nama Kriteria | Tipe Atribut | Bobot (`w_j`) | Skala Crips `1` (Nilai Terendah) | Skala Crips `5` (Nilai Tertinggi) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`C1`** | Pendapatan Keluarga | `COST` | `0.30` | Sangat Rendah (`<= Rp 500.000/bln`) | Sangat Tinggi (`> Rp 4.000.000/bln`) |
| **`C2`** | Jumlah Tanggungan | `BENEFIT` | `0.25` | Tidak ada tanggungan | `>= 7` orang tanggungan |
| **`C3`** | Kondisi Tempat Tinggal | `COST` | `0.25` | Tidak Layak (Darurat / tanpa fasilitas) | Sangat Layak (Permanen, fasilitas lengkap) |
| **`C4`** | Kepemilikan Aset | `COST` | `0.20` | Tidak memiliki aset produktif | Memiliki aset besar (mobil/usaha/properti) |

---

### Hasil Verifikasi Fase 1

```text
$ backend\.venv\Scripts\pytest.exe backend/tests/test_crypto_and_models.py backend/tests/test_security_guardrails.py -v

backend/tests/test_crypto_and_models.py::test_nik_crypto_roundtrip_and_no_plaintext_at_rest PASSED
backend/tests/test_crypto_and_models.py::test_invalid_nik_rejected PASSED
backend/tests/test_crypto_and_models.py::test_citizen_upsert_idempotency PASSED
backend/tests/test_crypto_and_models.py::test_seed_initial_data_creates_criteria PASSED
backend/tests/test_crypto_and_models.py::test_citizen_blocks_plaintext_nik_at_rest_and_enforces_prd_schema_constraints PASSED
backend/tests/test_crypto_and_models.py::test_adversarial_crypto_base64_malleability_and_override_settings PASSED
backend/tests/test_crypto_and_models.py::test_adversarial_orm_queryset_aliases_and_null_tms_reason PASSED
backend/tests/test_crypto_and_models.py::test_adversarial_citizen_at_rest_guards_on_hash_mask_update_and_bulk_create PASSED
backend/tests/test_crypto_and_models.py::test_mask_nik_format PASSED
backend/tests/test_crypto_and_models.py::test_mask_name_single_word PASSED
backend/tests/test_crypto_and_models.py::test_mask_name_multi_word PASSED
backend/tests/test_crypto_and_models.py::test_encrypt_nik_32byte_key_enforcement PASSED
backend/tests/test_crypto_and_models.py::test_nik_hash_is_deterministic PASSED
backend/tests/test_crypto_and_models.py::test_pdf_token_expired_raises PASSED
backend/tests/test_crypto_and_models.py::test_security_audit_unicode_nik_and_tampered_ciphertext_rejected PASSED
backend/tests/test_security_guardrails.py::test_env_example_files_exist_and_contain_required_placeholders PASSED
backend/tests/test_security_guardrails.py::test_parse_aes_256_key_strictly_enforces_32_bytes PASSED
backend/tests/test_security_guardrails.py::test_secret_management_enforces_key_separation_and_blocks_wildcard_cors PASSED
backend/tests/test_security_guardrails.py::test_auth_guardrails_reject_allow_any_and_unbounded_jwt PASSED
backend/tests/test_security_guardrails.py::test_zero_pii_log_filter_redacts_16_digit_nik_and_bearer_jwt PASSED

20 passed in 1.56s
```

---

## Quick Start (Fase 1)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Jalankan migrasi skema 9 tabel PRD + StaffUser
python manage.py migrate

# Isi data awal kriteria C1-C4, sub-kriteria Crips 1-5, dan akun staf demo
python manage.py seed_initial_data

# Jalankan pengujian kriptografi & model
pytest tests/test_crypto_and_models.py -v
```

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

- **Jangan Pernah Menyimpan NIK Plaintext:** Gunakan `Citizen.objects.create_or_update_with_nik(raw_nik=..., ...)` yang otomatis mengisi `nik_hash`, `nik_encrypted`, dan `nik_masked`.
- **Gunakan Bobot Beku Setelah Kalkulasi:** Setelah status batch mencapai `Calculated`, seluruh modul hilir wajib membaca `BatchCriteria.frozen_weight` milik batch tersebut.
