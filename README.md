# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `feat/m3-xai-fallback` (Fase 3 / Task 3 — Zero-PII Sanitizer, Gemini Flash XAI Explainer, Deterministic Fallback, & Async Worker)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)

Setelah Fase 1 meletakkan fondasi kriptografi NIK dan Fase 2 mengimplementasikan engine deterministik Simple Additive Weighting (SAW), Fase 3 menghadirkan **lapisan penjelasan (Explainer Layer)** sesuai **PRD Bagian 8**, **[ADR-001](./docs/decisions/ADR-001-hybrid-saw-xai-with-deterministic-fallback.md)**, **[ADR-002](./docs/decisions/ADR-002-dual-layer-nik-crypto-and-zero-pii-xai.md)**, dan **[ADR-004](./docs/decisions/ADR-004-async-xai-queue-and-passwordless-public-portal.md)**:

1. **Zero-PII Sanitization (UU PDP No. 27/2022 & OWASP LLM02):**
   Wajib menjamin tidak ada satupun Data Pribadi (nama asli, NIK, No KK, alamat, RT/RW) yang dikirim ke Google Gemini API. Pemohon diidentifikasi hanya dengan kode anonim (`KPM-042`).
2. **Kepatuhan Terhadap Snapshot Bobot Beku (`BatchCriteria.frozen_weight`):**
   Seluruh kalkulasi kesenjangan dan pembentukan prompt XAI wajib membaca bobot beku batch (`frozen_weight`), bukan master `Criteria.weight` yang dinamis, menjaga integritas historis batch.
3. **Penjelasan Kontrafaktual & Transparansi Algoritmik:**
   Memberikan narasi bahasa alami yang menjelaskan faktor pembeda utama dan saran edukatif bagi warga yang tidak lolos kuota, serta konfirmasi verifikasi bagi warga yang lolos.
4. **Resiliensi Tinggi & Fallback Deterministik Bebas HTTP 500:**
   Jika kuota API habis (HTTP 429), jaringan terputus, atau output LLM mengalami halusinasi kriteria setelah 2 kali *retry* dengan *exponential backoff*, sistem secara otomatis beralih ke generator deterministik berbasis penalti kesenjangan terbobot $\Delta_j \cdot w_j$ tanpa menghentikan batch.
5. **State Machine Asinkron:**
   Batch hanya dapat berpindah dari status `Calculated` ke `Narrated` apabila 100% kandidat `ELIGIBLE` telah memiliki narasi penjelasan yang tersimpan di basis data.

---

### Changelog Fase 3 (Task 3)

#### Added
- **Sanitizer Zero-PII ([`backend/core/services/sanitizer.py`](./backend/core/services/sanitizer.py)):**
  - `build_anonymous_payload(evaluation_id)`: Membangun payload anonim sesuai PRD Bagian 8.1 (`applicant_code`, `rank`, `quota`, `status`, `final_score`, `cutoff_score`, `criteria_data`).
  - Isolasi PII 100%: Menyaring nama, NIK (hash/masked/encrypted), No KK, dan alamat.
  - Snapshot Enforced: Membaca `BatchCriteria.frozen_weight` per batch secara eksklusif.
  - Menghitung rata-rata skor normalisasi penerima lolos ($\bar{r}_j^{\text{lolos}}$) dengan penanganan aman untuk kasus ekstrem (`quota = 0` dan `quota >= eligible`).
  - Menolak kandidat `DISQUALIFIED` (TMS) karena warga TMS diarahkan ke `INELIGIBLE_NOTICE` administratif, bukan modul XAI.
- **Generator Fallback Deterministik ([`backend/core/services/deterministic_fallback.py`](./backend/core/services/deterministic_fallback.py)):**
  - `generate_deterministic_fallback(payload)`: Menghitung penalti kesenjangan terbobot $\Delta_j \cdot w_j = (\bar{r}_j^{\text{lolos}} - r_{ij}) \cdot w_j$.
  - Menerapkan resolusi kriteria kembar kanonik: $C_1 \rightarrow C_2 \rightarrow C_3 \rightarrow C_4$.
  - Penanganan khusus kandidat batas kuota (*borderline*): Jika seluruh $\Delta_j \le 0$ tetapi tidak lolos kuota karena *tie-breaker*, menghasilkan narasi spesifik mengenai kompetisi batas ambang kuota (*cutoff*).
  - Menyusun narasi resmi terstandarisasi untuk status `LOLOS` dan `TIDAK_LOLOS`.
- **Gemini Flash XAI Client & Validator ([`backend/core/services/xai_explainer.py`](./backend/core/services/xai_explainer.py)):**
  - `generate_xai_for_evaluation(evaluation_id, gemini_client, backoff_seconds)`: Mengintegrasikan SDK resmi `google-genai` (`genai.Client`, `GenerateContentConfig`, `temperature: 0.15`, `response_mime_type: "application/json"`), mendukung *duck-typed client* (baik `client.models.generate_content` maupun `client.generate`) serta penanganan *response object/string/dict*.
  - `validate_xai_output(data, allowed_criteria_codes, payload)`: Validasi ketat struktur JSON (`ringkasan_keputusan`, `faktor_penentu_utama`, `narasi_lengkap`, `rekomendasi_tindak_lanjut`), pembersihan otomatis blok kode markdown (` ```json `), pencegahan halusinasi kode kriteria non-aktif di seluruh 4 field, pencegahan halusinasi nilai numerik (*rank*, *quota*, dan angka skor desimal tak berdasar per PRD Bagian 11.2), serta ekstraksi otomatis `primary_criterion_code` untuk evaluasi *Fidelity Score*.
  - Mekanisme *retry* maksimal 2 kali dengan *exponential backoff*, berpindah otomatis ke `generate_deterministic_fallback()` jika gagal tanpa melempar pengecualian HTTP 500.
  - `map_explanation_to_public_schema(ai_payload)`: Memetakan kunci internal ke kontrak skema publik (`ringkasan`, `faktor_utama`, `narasi_lengkap`, `rekomendasi`) secara idempoten.
- **Asynchronous Task Worker ([`backend/core/tasks.py`](./backend/core/tasks.py)):**
  - `process_batch_xai_task(batch_id, gemini_client, evaluation_id, force)`: Memproses narasi seluruh kandidat `ELIGIBLE` dalam batch atau mode pemohon tunggal (`?evaluation_id=45`).
  - *Idempotent Resume*: Secara cerdas melewati kandidat yang sudah memiliki narasi (`force=False`) sehingga pemrosesan ulang hemat kuota API dan aman dari interupsi.
  - *Concurrency Protection*: Menggunakan row lock `select_for_update()` dalam transaksi database atomik untuk mencegah *race condition* antar worker paralel.
  - *State Transition Gate*: Memperbarui status batch ke `"Narrated"` dan mencatat `AuditLog` (`XAI_GENERATED`) **hanya jika 100%** kandidat berhak telah memiliki narasi lengkap.
  - Menolak eksekusi pada batch yang belum berstatus `Calculated`.
- **Suite Pengujian TDD & Security Audit ([`backend/tests/test_xai_and_fallback.py`](./backend/tests/test_xai_and_fallback.py)):**
  - 27 pengujian menyeluruh mencakup Zero-PII, isolasi bobot beku, resolusi $\Delta_j \cdot w_j$, kandidat batas kuota (*borderline*), retry/fallback, anti-halusinasi kriteria & angka, pembersihan blok markdown, *state machine*, mode evaluasi tunggal, resume idempoten, dan audit PII pada payload jaringan LLM.

#### Security
- **OWASP LLM02 Sensitive Information Disclosure & UU PDP Kepatuhan Penuh:** Tidak ada data identitas warga yang pernah disentuh atau dikirimkan ke model LLM. Terverifikasi secara otomatis oleh `test_security_audit_zero_pii_in_llm_prompt_and_network_payload`.
- **Anti-Hallucination Filtering (Criteria & Numbers):** Respons LLM diperiksa terhadap kriteria aktif serta konsistensi angka terhadap payload JSON (ranking, kuota, skor); manipulasi atau halusinasi angka/kriteria memicu penolakan dan fallback ke aturan deterministik kelurahan.
- **Fail-Safe Robustness:** Pemadaman API eksternal atau *rate limiting* tidak pernah mengakibatkan *crash* atau kesalahan sistem 500 ke pengguna.

#### Changed
- Modul layanan `core.services` diperluas dan diekspos melalui [`backend/core/services/__init__.py`](./backend/core/services/__init__.py).
- Seluruh 47 pengujian dari Fase 1 (Kriptografi & Model) dan Fase 2 (SAW & Tie-Breaker) tetap 100% lulus tanpa regresi.

---

### Skema Payload Zero-PII & Fallback Deterministik $\Delta_j \cdot w_j$

#### 1. Payload Anonim ke Gemini API (PRD Bagian 8.1)
```json
{
  "applicant_code": "KPM-042",
  "rank": 35,
  "quota": 30,
  "status": "TIDAK_LOLOS",
  "final_score": 0.684,
  "cutoff_score": 0.725,
  "criteria_data": [
    {
      "code": "C1",
      "name": "Pendapatan Keluarga",
      "type": "COST",
      "weight": 0.30,
      "raw_crips_label": "Rp 1.500.001 - Rp 2.500.000/bln",
      "normalized_score": 0.60,
      "avg_passed_score": 0.85
    },
    {
      "code": "C2",
      "name": "Jumlah Tanggungan",
      "type": "BENEFIT",
      "weight": 0.25,
      "raw_crips_label": "1-2 orang tanggungan",
      "normalized_score": 0.50,
      "avg_passed_score": 0.80
    },
    {
      "code": "C3",
      "name": "Kondisi Tempat Tinggal",
      "type": "COST",
      "weight": 0.25,
      "raw_crips_label": "Cukup (Semi-permanen, fasilitas terbatas)",
      "normalized_score": 0.75,
      "avg_passed_score": 0.75
    },
    {
      "code": "C4",
      "name": "Kepemilikan Aset",
      "type": "COST",
      "weight": 0.20,
      "raw_crips_label": "Memiliki aset menengah (motor/elektronik)",
      "normalized_score": 0.70,
      "avg_passed_score": 0.70
    }
  ]
}
```

#### 2. Formulasi Kesenjangan Terbobot Fallback Deterministik
Untuk setiap kriteria $j$:

$$\Delta_j = \bar{r}_j^{\text{lolos}} - r_{ij}$$

$$\text{Penalti Terbobot}_j = \Delta_j \cdot w_j$$

Kriteria penentu utama dipilih melalui:

$$j^* = \operatorname{argmax}_j (\Delta_j \cdot w_j)$$

Jika terdapat nilai penalti terbobot kembar, pemecahan dilakukan dengan prioritas kriteria kanonik $C_1 \succ C_2 \succ C_3 \succ C_4$.

---

### Daftar File Fase 3

| File | Tanggung Jawab |
| :--- | :--- |
| [`./backend/core/services/sanitizer.py`](./backend/core/services/sanitizer.py) | Membangun payload anonim Zero-PII, membaca `BatchCriteria.frozen_weight`, menghitung $\bar{r}_j^{\text{lolos}}$ |
| [`./backend/core/services/deterministic_fallback.py`](./backend/core/services/deterministic_fallback.py) | Generator narasi deterministik berbasis aturan ($\Delta_j \cdot w_j$, tie-breaker $C_1–C_4$, & kasus batas kuota) |
| [`./backend/core/services/xai_explainer.py`](./backend/core/services/xai_explainer.py) | Klien Gemini Flash API, validasi anti-halusinasi, *retry exponential backoff*, pemetaan skema publik |
| [`./backend/core/tasks.py`](./backend/core/tasks.py) | Worker asinkron batch XAI dengan *state transition guard* ke status `"Narrated"` |
| [`./backend/core/services/__init__.py`](./backend/core/services/__init__.py) | Ekspor publik modul layanan SAW & XAI |
| [`./backend/tests/test_xai_and_fallback.py`](./backend/tests/test_xai_and_fallback.py) | 15 pengujian TDD, kasus batas, simulasi kegagalan Gemini, dan audit keamanan Zero-PII |

---

### Hasil Verifikasi Test

```text
$ backend/.venv/Scripts/python.exe -m pytest backend/tests/test_xai_and_fallback.py -v

backend\tests\test_xai_and_fallback.py::test_anonymous_payload_contains_zero_pii_and_uses_frozen_weights PASSED
backend\tests\test_xai_and_fallback.py::test_anonymous_payload_criteria_data_fields_and_avg_passed_score PASSED
backend\tests\test_xai_and_fallback.py::test_anonymous_payload_zero_passed_or_all_passed PASSED
backend\tests\test_xai_and_fallback.py::test_anonymous_payload_rejects_disqualified_or_uncalculated PASSED
backend\tests\test_xai_and_fallback.py::test_fallback_selects_highest_weighted_gap_and_maps_public_keys PASSED
backend\tests\test_xai_and_fallback.py::test_fallback_canonical_tie_break_order_c1_to_c4 PASSED
backend\tests\test_xai_and_fallback.py::test_fallback_borderline_tie_break_when_all_gaps_non_positive PASSED
backend\tests\test_xai_and_fallback.py::test_fallback_for_status_lolos PASSED
backend\tests\test_xai_and_fallback.py::test_xai_explainer_with_mocked_gemini_success PASSED
backend\tests\test_xai_and_fallback.py::test_xai_explainer_retries_and_falls_back_on_error PASSED
backend\tests\test_xai_and_fallback.py::test_xai_explainer_rejects_hallucinated_criteria_and_falls_back PASSED
backend\tests\test_xai_and_fallback.py::test_xai_explainer_rejects_malformed_json_and_falls_back PASSED
backend\tests\test_xai_and_fallback.py::test_process_batch_xai_task_transitions_to_narrated PASSED
backend\tests\test_xai_and_fallback.py::test_process_batch_xai_task_rejects_invalid_batch_status PASSED
backend\tests\test_xai_and_fallback.py::test_security_audit_zero_pii_in_llm_prompt_and_network_payload PASSED
backend\tests\test_xai_and_fallback.py::test_validate_xai_output_strips_markdown_code_fences PASSED
backend\tests\test_xai_and_fallback.py::test_validate_xai_output_rejects_hallucinated_code_in_summary_or_recommendation PASSED
backend\tests\test_xai_and_fallback.py::test_validate_xai_output_rejects_hallucinated_numbers_rank_and_quota PASSED
backend\tests\test_xai_and_fallback.py::test_validate_xai_output_rejects_hallucinated_decimal_score PASSED
backend\tests\test_xai_and_fallback.py::test_validate_xai_output_extracts_primary_criterion_code_for_fidelity PASSED
backend\tests\test_xai_and_fallback.py::test_map_explanation_to_public_schema_handles_existing_public_keys_and_edge_cases PASSED
backend\tests\test_xai_and_fallback.py::test_sanitizer_rejects_incomplete_evaluation_details PASSED
backend\tests\test_xai_and_fallback.py::test_sanitizer_falls_back_to_batch_cutoff_score PASSED
backend\tests\test_xai_and_fallback.py::test_process_batch_xai_task_with_single_evaluation_id PASSED
backend\tests\test_xai_and_fallback.py::test_process_batch_xai_task_skips_already_narrated_candidates_idempotently PASSED
backend\tests\test_xai_and_fallback.py::test_process_batch_xai_task_blocks_narrated_status_when_generation_fails_partially PASSED
backend\tests\test_xai_and_fallback.py::test_generate_xai_for_evaluation_duck_typed_client_support PASSED

======================== 27 passed in 22.67s ========================

# Verifikasi Regresi Keseluruhan (Fase 1 + Fase 2 + Fase 3 + Security Guardrails):
$ backend/.venv/Scripts/python.exe -m pytest backend/tests/ -v
======================= 74 passed in 34.13s =======================
```

---

## Dokumentasi Branch Sebelumnya

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

- **Jangan Pernah Mengirim PII ke LLM:** Modul XAI hanya boleh menerima payload anonim yang telah disanitasi melalui `build_anonymous_payload()`.
- **Gunakan Bobot Beku Setelah Kalkulasi:** Setelah status batch mencapai `Calculated`, seluruh modul hilir wajib membaca `BatchCriteria.frozen_weight` milik batch tersebut, bukan `Criteria.weight`.
- **Fallback Otomatis Anti-500:** Modul penjelasan XAI tidak boleh melempar HTTP 500 jika API Gemini offline; sistem wajib selalu menyediakan narasi fallback deterministik.
