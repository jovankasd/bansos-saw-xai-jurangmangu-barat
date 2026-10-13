# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Seleksi Bantuan Sosial

Platform **Explainable Decision Support System (EDSS)** berbasis web untuk seleksi Keluarga Penerima Manfaat (KPM) Bantuan Sosial di **Kelurahan Jurangmangu Barat, Kecamatan Pondok Aren, Kota Tangerang Selatan**.

---

## Dokumentasi Branch: `chore/fase-0-preflight` (Fase 0 — Pre-Flight Check & Environment Hardening)

### Mengapa Fase Ini Dibutuhkan (*Context & Why*)
Sebelum model basis data dan layanan kriptografi dibangun, aplikasi harus memiliki fondasi keamanan *fail-closed* agar kesalahan konfigurasi `.env` tidak pernah meloloskan kunci lemah ke produksi atau membocorkan 16 digit NIK ke log server (kepatuhan **UU PDP No. 27 Tahun 2022** dan **OWASP Top 10 A02/A05/A07**).

### Changelog Fase 0

#### Added
- **Konfigurasi Template Environment:** Menambahkan [`.env.example`](./.env.example), [`backend/.env.example`](./backend/.env.example), dan [`frontend/.env.example`](./frontend/.env.example) sebagai kontrak variabel lingkungan tanpa menyimpan rahasia di Git.
- **Pengaturan Inti Django 5.x:** Mengonfigurasi [`backend/config/settings.py`](./backend/config/settings.py) dengan `Argon2PasswordHasher`, SimpleJWT, Django-Q2 worker, dan pemuatan `.env` otomatis.
- **Suite Pengujian Guardrails:** Menambahkan 5 pengujian otomatis di [`backend/tests/test_security_guardrails.py`](./backend/tests/test_security_guardrails.py).

#### Security
- **Validasi Kunci Kriptografi & *Key Separation* ([`backend/config/security.py`](./backend/config/security.py)):**
  - `parse_aes_256_key()` memvalidasi `NIK_AES_KEY` wajib tepat 32 byte (256-bit).
  - `validate_secret_management()` menghentikan *startup* aplikasi jika `NIK_AES_KEY`, `NIK_HMAC_PEPPER`, dan `DJANGO_SECRET_KEY` menggunakan nilai yang sama, atau jika *wildcard* CORS (`*`) diaktifkan.
- **Guardrail Autentikasi (`validate_auth_guardrails()`):** Menolak izin global `AllowAny` pada DRF dan membatasi masa berlaku *access token* JWT maksimal 60 menit dengan rotasi *refresh token*.
- **Sanitasi Log Server (`ZeroPiiLogFilter`):** Menyensor otomatis 16 digit NIK (`[REDACTED_NIK_16]`) dan token `Bearer` JWT (`[REDACTED_JWT]`) sebelum ditulis ke konsol/log.
- **Audit Dependensi ([`backend/requirements.txt`](./backend/requirements.txt)):** Memastikan seluruh 70 paket di dalam `backend/.venv` terinstal dengan 0 kerentanan pada `pip-audit`.

### Daftar File Utama Fase 0

| File | Peran & Tanggung Jawab |
| :--- | :--- |
| [`backend/config/security.py`](./backend/config/security.py) | Validator *fail-closed* untuk kunci 32-byte AES, *Key Separation*, SimpleJWT, CORS, dan `ZeroPiiLogFilter`. |
| [`backend/config/settings.py`](./backend/config/settings.py) | Konfigurasi Django 5.x yang memanggil validator keamanan saat *startup*. |
| [`backend/.env.example`](./backend/.env.example) | Dokumentasi variabel lingkungan kriptografi, JWT, CORS, Gemini API, dan rate-limiter. |
| [`backend/requirements.txt`](./backend/requirements.txt) | Daftar dependensi terkunci (*pinned versions*) yang telah diaudit dengan `pip-audit`. |
| [`backend/tests/test_security_guardrails.py`](./backend/tests/test_security_guardrails.py) | Pengujian otomatis untuk memverifikasi seluruh guardrail keamanan Fase 0. |

### Hasil Verifikasi Fase 0

```text
$ backend\.venv\Scripts\python.exe -m pytest backend/tests/test_security_guardrails.py -v

backend/tests/test_security_guardrails.py::test_env_example_files_exist_and_contain_required_placeholders PASSED
backend/tests/test_security_guardrails.py::test_parse_aes_256_key_strictly_enforces_32_bytes PASSED
backend/tests/test_security_guardrails.py::test_secret_management_enforces_key_separation_and_blocks_wildcard_cors PASSED
backend/tests/test_security_guardrails.py::test_auth_guardrails_reject_allow_any_and_unbounded_jwt PASSED
backend/tests/test_security_guardrails.py::test_zero_pii_log_filter_redacts_16_digit_nik_and_bearer_jwt PASSED

5 passed in 0.48s
```

---

## Quick Start (Fase 0)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Salin template environment lokal
Copy-Item .env.example .env

# Jalankan verifikasi security guardrails
pytest tests/test_security_guardrails.py -v
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
