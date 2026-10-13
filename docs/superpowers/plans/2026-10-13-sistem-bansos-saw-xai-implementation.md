# Sistem Pendukung Keputusan Hibrida (SAW + XAI Gemini) Bansos Jurangmangu Barat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a full-stack, privacy-compliant (UU PDP No. 27/2022) hybrid Decision Support System combining deterministic Simple Additive Weighting (SAW) with asynchronous Google Gemini Flash Explainable AI (XAI) and a responsive (Mobile, Tablet, Desktop) Civic Precision web interface for social assistance selection in Kelurahan Jurangmangu Barat.

**Architecture:** A decoupled two-tier web application with a Django 5 + Django REST Framework backend and a React (Vite) + Tailwind CSS frontend. The backend enforces AES-256-GCM (strictly 32-byte key) at-rest encryption and HMAC-SHA256 indexing for NIK, executes deterministic SAW normalization with an immutable criteria snapshot (`BATCH_CRITERIA`) and 4-level hierarchical tie-breaker (`C1`, `C2`, `real_dependents_count`, `created_at`), and dispatches zero-PII background jobs to Gemini Flash with automatic rule-based fallback (`deterministic_fallback.py`). The frontend implements a mobile-first refactored version of the `.stitch/designs/` reference screens with a mandatory user design-review gate before each screen is coded.

**Tech Stack:** Python 3.11+, Django 5.x, Django REST Framework, SimpleJWT, Django-Q2 (or Celery + Redis), `cryptography` (AES-256-GCM), `google-genai` (Gemini Flash API), `openpyxl`, `reportlab`, `qrcode`, React 18, TypeScript 5, Vite, Tailwind CSS, Vitest + React Testing Library.

**Spec:** `d:\Kuliah\SKRIPSI\BANSOS_SAW+LLM\PRD_Sistem_Bansos_Jurangmangu_Barat_Final.md` and `d:\Kuliah\SKRIPSI\BANSOS_SAW+LLM\AGENTS.md`

## Global Constraints

- **Criteria Weights Validation (FR-01):** SAW calculation MUST be rejected if $\sum w_j \neq 1.00$ (`Decimal("1.00")`). Active criteria defaults: $C_1$ Pendapatan Keluarga (`COST`, `0.30`), $C_2$ Jumlah Tanggungan (`BENEFIT`, `0.25`), $C_3$ Kondisi Tempat Tinggal (`BENEFIT`, `0.25`), $C_4$ Kepemilikan Aset (`COST`, `0.20`).
- **Criteria Snapshot Freeze (FR-01):** Starting a SAW calculation MUST freeze current weights into `BATCH_CRITERIA` (`UniqueConstraint(fields=["batch", "criteria"])`). All post-calculation modules (`sanitizer.py`, `deterministic_fallback.py`, `evaluation_metrics.py`) MUST read `BatchCriteria.frozen_weight`, never master `Criteria.weight`.
- **TMS Exclusion Gate (FR-02):** Citizens marked `DISQUALIFIED` (`ASN`, `PKH_GANDA`, `PINDAH`, `MENINGGAL`) MUST be filtered out before validating/computing the SAW normalization matrix ($\min/\max$ calculation), while remaining stored for the Berita Acara TMS appendix.
- **Hierarchical Tie-Breaker (FR-03):** Identical $V_i$ scores MUST be resolved deterministically in order: (1) highest normalized $r_{i, C_1}$, (2) highest normalized $r_{i, C_2}$, (3) highest `Evaluation.real_dependents_count`, (4) earliest `Evaluation.created_at` (and `Evaluation.id` ASC as final deterministic tie-breaker).
- **Zero-PII & Cryptographic Storage (Section 5.1 & FR-04):** Never store plaintext NIK in DB or logs; store AES-256-GCM ciphertext in `nik_encrypted` (enforcing `len(key) == 32`), HMAC-SHA256 digest in `nik_hash`, and `367403******0002` in `nik_masked`. Support both multi-word (`"Ahmad S******"`) and single-word (`"Su*****"`) names in `mask_name()`. Never send name, NIK, KK, or address to Gemini API.
- **Async XAI & Deterministic Fallback (FR-04, FR-05):** Gemini Flash calls (`temperature: 0.15`, `response_mime_type: "application/json"`) run asynchronously; after 2 failed retries with exponential backoff, automatically invoke `deterministic_fallback.py` using $\operatorname{argmax}_j (\Delta_j \cdot w_j)$ (tie-broken by `C1 -> C2 -> C3 -> C4`, with a borderline tie-break explanation if all $\Delta_j \le 0$) without throwing HTTP 500.
- **Batch State Machine (Section 6):** Strict progression `Draft` $\rightarrow$ `Collecting` $\rightarrow$ `Calculated` $\rightarrow$ `Narrated` $\rightarrow$ `Approved` $\rightarrow$ `Published`. Recalculation is rejected once `Approved` or `Published`. Public portal `/cek-bansos` ONLY exposes batches in `Published` status.
- **Public Portal Anti-Bot & Anti-IDOR Protection (FR-06):** Requires 16-digit NIK + last 4 digits of KK + CAPTCHA (CAPTCHA verified before incrementing NIK failure counter); rate-limited to 5 req/min/IP and 15-minute lockout after 5 consecutive failed KK attempts per NIK. Individual PDF download uses a signed `TimestampSigner` token (`download_token`), never an unauthenticated sequential ID.
- **UI/UX `.stitch` Review & 3-Tier Responsiveness (AGENTS.md Section 2):** Never blindly copy-paste `.stitch/designs/*.html`. Present a design review to the user before implementing each screen, enforce responsive layouts for Mobile (`< 768px` drawer sidebar, single-column stack), Tablet (`768px–1023px` 2-column grid), and Desktop (`>= 1024px` fixed `w-64` sidebar, 12-column grid), unify $C_4$ as "Kepemilikan Aset", and exclude "Not Doing" features (no public two-way appeal form, no live SIKS-NG/DTKS sync).

## Review Focus

1. **Malformed/Plaintext NIK, Non-32-Byte AES Key, or Mononymic Name Masking:** Passing a non-16-digit NIK raises `ValidationError`, a non-32-byte `NIK_AES_KEY` raises `ValueError`, single-word names like `"Sukarno"` mask to `"Su*****"`, and plaintext NIK never appears in `nik_encrypted`.
2. **All-TMS Batch, Incomplete Crips Details, or All-Pass Quota (`quota >= eligible`):** Filtering `DISQUALIFIED` citizens happens before checking `ELIGIBLE` completeness; an all-TMS batch raises `ValidationError`, and `quota >= eligible_candidates` computes `cutoff_score` without `IndexError` and `fidelity_score = 100.0` without `ZeroDivisionError`.
3. **Post-Calculation Weight Mutation & Idempotent Recalculation:** Updating master `Criteria.weight` after a batch is `Calculated` never alters `BatchCriteria.frozen_weight`, XAI payloads, or `Fidelity Score` of that batch; re-running `calculate_batch_saw()` while in `Collecting`/`Calculated` updates existing snapshots/results atomically without `IntegrityError` or `MultipleObjectsReturned`, and is blocked once `Approved`/`Published`.
4. **LLM Malformed JSON / Hallucinated Keys / Rate Limit 429 & Key Mapping:** When Gemini returns invalid JSON or HTTP 429, the worker records a `DETERMINISTIC_FALLBACK` explanation, maps `ringkasan_keputusan`/`faktor_penentu_utama`/`rekomendasi_tindak_lanjut` to public API keys `ringkasan`/`faktor_utama`/`rekomendasi`, and only transitions the batch to `Narrated` when all `ELIGIBLE` candidates have narratives.
5. **Unpublished Batch Access, CAPTCHA-First Lockout Order, & Signed PDF Token on Public Portal:** Querying `/api/public/check-status/` before `Published` returns HTTP 404; invalid CAPTCHA returns HTTP 403 without incrementing the NIK lockout counter; 5 wrong `kk_last4` attempts lock out the NIK for 15 minutes (HTTP 429); and public PDF download requires a valid signed `download_token`.

---

## File Structure

```text
BANSOS_SAW+LLM/
├── backend/
│   ├── manage.py
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── urls.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── crypto.py                      # AES-256-GCM (32B check) + HMAC-SHA256 + masking + signed PDF token
│   │   ├── models.py                      # 9 PRD tables (incl. real_dependents_count) + StaffUser
│   │   ├── permissions.py                 # RBAC guards (SuperAdmin, Surveyor RT-scoped, Viewer)
│   │   ├── serializers.py                 # DRF serializers + Gemini-to-Public key mapper
│   │   ├── views.py                       # REST API controllers (CRUD, SAW, XAI, PDF, Excel, Public)
│   │   ├── urls.py                        # API route declarations
│   │   ├── tasks.py                       # Async XAI batch worker & rate limiter
│   │   ├── management/commands/
│   │   │   └── seed_initial_data.py       # Seeds C1..C4, Crips 1..5, demo staff & sample batch
│   │   └── services/
│   │       ├── saw_engine.py              # Snapshot freeze, TMS filter, normalization R_ij, V_i
│   │       ├── tie_breaker.py             # 4-level deterministic tie-breaker (C1, C2, real_dependents, timestamp)
│   │       ├── sanitizer.py               # Zero-PII payload builder reading BatchCriteria.frozen_weight
│   │       ├── deterministic_fallback.py  # Rule-based narrative generator (Delta_j * w_j + tie-break notice)
│   │       ├── xai_explainer.py           # Gemini Flash client + retry + fallback switch
│   │       ├── excel_ingest.py            # openpyxl batch import (Citizen upsert + Evaluation per batch) + Excel export
│   │       ├── rate_limiter.py            # Public portal IP rate limit + CAPTCHA check + per-NIK 15m lockout
│   │       ├── pdf_generator.py           # ReportLab Berita Acara + QR + TMS appendix & Individual PDF
│   │       └── evaluation_metrics.py      # Fidelity Score, Hallucination Rate, SUS export
│   └── tests/
│       ├── test_crypto_and_models.py
│       ├── test_saw_and_tiebreaker.py
│       ├── test_xai_and_fallback.py
│       ├── test_api_endpoints.py
│       └── test_pdf_and_evaluation.py
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js                 # Civic Precision tokens (#003426, Hanken Grotesk, JetBrains Mono)
    ├── src/
    │   ├── main.tsx
    │   ├── App.tsx
    │   ├── lib/api.ts
    │   ├── context/AuthContext.tsx
    │   ├── components/
    │   │   ├── layout/
    │   │   │   ├── AppShell.tsx           # Responsive container (lg:pl-64)
    │   │   │   ├── Sidebar.tsx            # Fixed on lg+, Off-Canvas Drawer on <lg, RBAC menu
    │   │   │   └── Topbar.tsx             # Unclipped flex-wrap header + mobile hamburger button
    │   │   └── public/
    │   │       └── CriteriaGapChart.tsx   # Applicant vs Passed Average bar chart
    │   ├── pages/
    │   │   ├── PublicPortalPage.tsx       # / and /cek-bansos
    │   │   ├── LoginPage.tsx              # /admin/login
    │   │   └── dashboard/
    │   │       ├── ExecutiveDashboardPage.tsx
    │   │       ├── CriteriaManagementPage.tsx
    │   │       ├── SurveyorInputPage.tsx
    │   │       ├── SawRankingPage.tsx
    │   │       ├── XaiGeneratorPage.tsx
    │   │       ├── LurahApprovalPage.tsx
    │   │       └── ThesisEvaluationPage.tsx
    │   └── __tests__/
    │       ├── AppShell.responsive.test.tsx
    │       ├── PublicPortalPage.test.tsx
    │       ├── DashboardScreens.test.tsx
    │       └── ApprovalAndEvaluation.test.tsx
```

---

### Task 1: Backend Scaffolding, Crypto Service (UU PDP), & Database Models (Milestone 1)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/manage.py`
- Create: `backend/config/__init__.py`
- Create: `backend/config/settings.py`
- Create: `backend/config/urls.py`
- Create: `backend/core/__init__.py`
- Create: `backend/core/crypto.py`
- Create: `backend/core/models.py`
- Create: `backend/core/management/commands/seed_initial_data.py`
- Test: `backend/tests/test_crypto_and_models.py`

**Interfaces:**
- Consumes: Environment variables `NIK_AES_KEY` (32-byte key) and `NIK_HMAC_PEPPER`
- Produces:
  - `validate_nik(nik: str) -> str`
  - `hash_nik(nik: str) -> str` (64-char hex HMAC-SHA256)
  - `encrypt_nik(nik: str) -> str` (base64 nonce + ciphertext + tag via AES-256-GCM; validates 32-byte key)
  - `decrypt_nik(token: str) -> str`
  - `mask_nik(nik: str) -> str` (`"367403******0002"`)
  - `mask_name(full_name: str) -> str` (`"Ahmad S******"` for multi-word, `"Su*****"` for single-word)
  - `sign_pdf_download_token(evaluation_id: int) -> str` & `verify_pdf_download_token(token: str, max_age: int = 900) -> int`
  - Django ORM Models in `core.models`: `StaffUser`, `Criteria`, `SubCriteria`, `BatchCriteria`, `Citizen` (`CitizenManager.create_or_update_with_nik`), `Period`, `SelectionBatch`, `Evaluation` (with `real_dependents_count` and `UniqueConstraint(fields=["batch", "citizen"])`), `EvaluationDetail` (`UniqueConstraint(fields=["evaluation", "criteria"])`), `SelectionResult`, `AuditLog`

- [ ] **Step 1: Write the failing test in `backend/tests/test_crypto_and_models.py`**

```python
import pytest
from django.core.exceptions import ValidationError
from core.crypto import (
    encrypt_nik,
    decrypt_nik,
    hash_nik,
    mask_nik,
    mask_name,
    validate_nik,
    sign_pdf_download_token,
    verify_pdf_download_token,
)
from core.models import Citizen, Criteria

@pytest.mark.django_db
def test_nik_crypto_roundtrip_and_no_plaintext_at_rest():
    raw_nik = "3674031208850002"
    citizen, created = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4="5501",
        full_name="Ahmad Subarjo",
        address="Jl. Jurangmangu Barat No. 10",
        rt="003",
        rw="001",
    )
    assert created is True
    assert citizen.nik_hash == hash_nik(raw_nik)
    assert citizen.nik_masked == "367403******0002"
    assert raw_nik not in citizen.nik_encrypted
    assert decrypt_nik(citizen.nik_encrypted) == raw_nik
    assert mask_name("Ahmad Subarjo") == "Ahmad S******"
    assert mask_name("Sukarno") == "Su*****"

    token = sign_pdf_download_token(citizen.id)
    assert verify_pdf_download_token(token) == citizen.id

@pytest.mark.django_db
def test_invalid_nik_rejected():
    with pytest.raises(ValidationError):
        validate_nik("36740312088500")  # 14 digits
    with pytest.raises(ValidationError):
        validate_nik("367403120885ABCD")  # non-numeric
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_crypto_and_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core'`

- [ ] **Step 3: Create Django project scaffolding, `backend/core/crypto.py`, `backend/core/models.py`, and `seed_initial_data.py`**

Implement `AESGCM` (strictly asserting `len(key) == 32`), HMAC-SHA256, `mask_nik`, `mask_name`, and `TimestampSigner` helpers in `core/crypto.py`. Implement the 9 PRD tables + `StaffUser` in `core/models.py`, including `Evaluation.real_dependents_count` (`PositiveSmallIntegerField(default=0)`) and unique constraints (`batch+citizen` on `Evaluation`, `batch+criteria` on `BatchCriteria`, `evaluation+criteria` on `EvaluationDetail`). Implement `seed_initial_data.py` for $C_1$–$C_4$, Crips 1–5, and demo staff accounts.

- [ ] **Step 4: Run migrations and test to verify it passes**

Run: `python backend/manage.py makemigrations core && python backend/manage.py migrate && pytest backend/tests/test_crypto_and_models.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(backend): add Django models, AES-256-GCM + HMAC-SHA256 NIK crypto, and criteria seed"
```

---

### Task 2: SAW Engine, Criteria Snapshot Freeze, TMS Filter, & Hierarchical Tie-Breaker (Milestone 2)

**Files:**
- Create: `backend/core/services/tie_breaker.py`
- Create: `backend/core/services/saw_engine.py`
- Test: `backend/tests/test_saw_and_tiebreaker.py`

**Interfaces:**
- Consumes: `Criteria`, `BatchCriteria`, `SelectionBatch`, `Evaluation`, `EvaluationDetail`, `SelectionResult` from `core.models`
- Produces:
  - `validate_criteria_weights() -> Decimal` (raises `ValidationError` if $\sum w_j \neq \text{Decimal}("1.00")$)
  - `freeze_batch_criteria(batch: SelectionBatch) -> list[BatchCriteria]` (idempotent `update_or_create`)
  - `resolve_rankings_with_tie_breaker(candidates: list[dict], quota: int) -> list[dict]`
  - `calculate_batch_saw(batch_id: int, performed_by: str = "system") -> dict`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_saw_and_tiebreaker.py`**

```python
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from core.models import Criteria, BatchCriteria, SelectionResult
from core.services.saw_engine import calculate_batch_saw, validate_criteria_weights

@pytest.mark.django_db
def test_saw_rejects_invalid_weight_sum(seeded_criteria):
    c1 = Criteria.objects.get(code="C1")
    c1.weight = Decimal("0.25")
    c1.save()
    with pytest.raises(ValidationError, match="Total bobot harus persis bernilai 1.00"):
        validate_criteria_weights()

@pytest.mark.django_db
def test_saw_excludes_tms_freezes_weights_and_resolves_all_4_tie_break_levels(seeded_batch_with_ties):
    summary = calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    assert summary["eligible_candidates"] == 4
    assert summary["disqualified_tms"] == 1
    assert summary["tie_breaks_resolved"] >= 1
    assert summary["status"] == "Calculated"

    # Idempotent recalculation while in Calculated state must not duplicate BatchCriteria
    summary_rerun = calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    assert BatchCriteria.objects.filter(batch=seeded_batch_with_ties).count() == 4

    # Mutate master criteria weight after calculation -> frozen snapshot & results remain unchanged
    Criteria.objects.filter(code="C1").update(weight=Decimal("0.50"))
    frozen_c1 = BatchCriteria.objects.get(batch=seeded_batch_with_ties, code="C1")
    assert frozen_c1.frozen_weight == Decimal("0.30")

    tms_result = SelectionResult.objects.get(evaluation__eligibility_status="DISQUALIFIED")
    assert tms_result.status == "DISKUALIFIKASI_TMS"
    assert tms_result.final_score_v == Decimal("0.0000")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_saw_and_tiebreaker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.saw_engine'`

- [ ] **Step 3: Implement `tie_breaker.py` and `saw_engine.py`**

In `saw_engine.py` (wrapped in `transaction.atomic()`):
1. Reject if `batch.status in ("Approved", "Published")`.
2. Verify $\sum w_j == \text{Decimal}("1.00")` and `update_or_create` `BatchCriteria` rows for `batch`.
3. Partition `Evaluation` rows into `DISQUALIFIED` (immediately `update_or_create` `SelectionResult` with `status="DISKUALIFIKASI_TMS"`, `final_score_v=0`, `ranking=None`, `explanation_source="INELIGIBLE_NOTICE"`) and `ELIGIBLE`.
4. Raise `ValidationError` if `ELIGIBLE` is empty or any `ELIGIBLE` candidate lacks all active criteria details or has `raw_crips_value <= 0`.
5. Compute $\max_i x_{ij}$ and $\min_i x_{ij}$ across `ELIGIBLE` evaluations using `BatchCriteria.frozen_weight`.
6. In `tie_breaker.py`, sort `ELIGIBLE` candidates by `(-final_score_v, -r_C1, -r_C2, -real_dependents_count, created_at, evaluation_id)` and set `tie_break_level` (`0` if unique $V_i$, `1` if broken by $C_1$, `2` by $C_2$, `3` by `real_dependents_count`, `4` by `created_at`). Handle `cutoff_score` safely when `quota == 0` or `quota >= len(eligible)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_saw_and_tiebreaker.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/services/ backend/tests/test_saw_and_tiebreaker.py
git commit -m "feat(saw): implement atomic SAW engine, snapshot freeze, TMS filter, and 4-tier tie-breaker"
```

---

### Task 3: Zero-PII Sanitizer, Gemini Flash XAI Explainer, Deterministic Fallback, & Async Worker (Milestone 3)

**Files:**
- Create: `backend/core/services/sanitizer.py`
- Create: `backend/core/services/deterministic_fallback.py`
- Create: `backend/core/services/xai_explainer.py`
- Create: `backend/core/tasks.py`
- Test: `backend/tests/test_xai_and_fallback.py`

**Interfaces:**
- Consumes: `SelectionBatch`, `Evaluation`, `SelectionResult`, `BatchCriteria`
- Produces:
  - `build_anonymous_payload(evaluation_id: int) -> dict` (reads `BatchCriteria.frozen_weight`; zero PII)
  - `generate_deterministic_fallback(payload: dict) -> dict` (returns `ringkasan_keputusan`, `faktor_penentu_utama`, `narasi_lengkap`, `rekomendasi_tindak_lanjut`, `primary_criterion_code`)
  - `map_explanation_to_public_schema(ai_payload: dict) -> dict` (maps to `ringkasan`, `faktor_utama`, `narasi_lengkap`, `rekomendasi`)
  - `generate_xai_for_evaluation(evaluation_id: int, gemini_client=None, backoff_seconds: float = 1.0) -> SelectionResult`
  - `process_batch_xai_task(batch_id: int, gemini_client=None) -> dict`

- [ ] **Step 1: Write the failing tests in `backend/tests/test_xai_and_fallback.py`**

```python
import json
import pytest
from decimal import Decimal
from core.models import Criteria
from core.services.sanitizer import build_anonymous_payload
from core.services.xai_explainer import generate_xai_for_evaluation, map_explanation_to_public_schema

@pytest.mark.django_db
def test_anonymous_payload_contains_zero_pii_and_uses_frozen_weights(calculated_batch_with_evaluations):
    # Mutate master Criteria C1 weight to 0.90; payload MUST still use frozen_weight 0.30
    Criteria.objects.filter(code="C1").update(weight=Decimal("0.90"))
    eval_obj = calculated_batch_with_evaluations.evaluations.filter(eligibility_status="ELIGIBLE").first()
    payload = build_anonymous_payload(eval_obj.id)
    serialized = json.dumps(payload)

    assert eval_obj.citizen.full_name not in serialized
    assert eval_obj.citizen.nik_masked not in serialized
    assert eval_obj.citizen.kk_last4 not in serialized
    c1_item = next(item for item in payload["criteria_data"] if item["code"] == "C1")
    assert c1_item["weight"] == 0.30

@pytest.mark.django_db
def test_fallback_selects_highest_weighted_gap_and_maps_public_keys(calculated_batch_with_evaluations):
    failed_eval = calculated_batch_with_evaluations.evaluations.filter(
        result__status="TIDAK_LOLOS"
    ).first()

    class FailingGeminiClient:
        def generate(self, payload):
            raise TimeoutError("429 Resource Exhausted")

    result = generate_xai_for_evaluation(failed_eval.id, gemini_client=FailingGeminiClient(), backoff_seconds=0)
    assert result.explanation_source == "DETERMINISTIC_FALLBACK"
    mapped = map_explanation_to_public_schema(result.ai_payload_response)
    assert set(mapped.keys()) == {"ringkasan", "faktor_utama", "narasi_lengkap", "rekomendasi"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_xai_and_fallback.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.sanitizer'`

- [ ] **Step 3: Implement `sanitizer.py`, `deterministic_fallback.py`, `xai_explainer.py`, and `tasks.py`**

1. `sanitizer.py`: Build the PRD Section 8.1 payload strictly from `BatchCriteria.objects.filter(batch=evaluation.batch)` so master weight changes never leak into calculated batches.
2. `deterministic_fallback.py`: Compute $\Delta_j \cdot w_j = (\text{avg\_passed\_score}_j - \text{normalized\_score}_j) \cdot w_j$ with canonical criterion tie-break order `C1 -> C2 -> C3 -> C4` (and a dedicated borderline tie-break explanation if all $\Delta_j \le 0$).
3. `xai_explainer.py`: Call Gemini Flash (`temperature=0.15`, `response_mime_type="application/json"`), retry up to 2 times on error or invalid/hallucinated output, and fall back to `generate_deterministic_fallback()`. Provide `map_explanation_to_public_schema()`.
4. `tasks.py`: Implement `process_batch_xai_task(batch_id)` and ensure `batch.status` transitions to `"Narrated"` only when all `ELIGIBLE` evaluations have non-empty `ai_narrative`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_xai_and_fallback.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/core/services/ backend/core/tasks.py backend/tests/test_xai_and_fallback.py
git commit -m "feat(xai): add zero-PII sanitizer, Gemini Flash explainer, deterministic fallback, and batch worker"
```

---

### Task 4: REST API Endpoints, RBAC Guards, Excel Import/Export, & Public Portal Shield (Milestone 4 Backend)

**Files:**
- Create: `backend/core/permissions.py`
- Create: `backend/core/serializers.py`
- Create: `backend/core/services/excel_ingest.py`
- Create: `backend/core/services/rate_limiter.py`
- Create: `backend/core/views.py`
- Create: `backend/core/urls.py`
- Modify: `backend/config/urls.py`
- Test: `backend/tests/test_api_endpoints.py`

**Interfaces:**
- Consumes: Services from Tasks 1–3
- Produces REST Endpoints (PRD Section 10 + Dashboard Read/Write APIs):
  - `POST /api/auth/login/` -> `{access, refresh, role, name, rt_number}`
  - `GET /api/criteria/` & `PUT /api/criteria/batch-update/`
  - `GET /api/batches/` & `POST /api/batches/`
  - `POST /api/citizens/` & `POST /api/citizens/import-excel/` (upserts `Citizen` by `nik_hash`, creates/updates `Evaluation` for `batch_id`, enforces Surveyor `rt_number` scope)
  - `POST /api/selection/{batch_id}/mark-rt-submitted/`
  - `POST /api/selection/{batch_id}/calculate/`
  - `GET /api/selection/{batch_id}/results/` (supports filtering by status/RT, Cutoff Zone, and RT distribution)
  - `POST /api/selection/{batch_id}/generate-xai/` (HTTP 202) & `GET /api/selection/{batch_id}/xai-progress/`
  - `PATCH /api/selection/{batch_id}/approve/` (Viewer / Lurah only, requires `status == "Narrated"`)
  - `PATCH /api/selection/{batch_id}/publish/` (Super Admin only, requires `status == "Approved"`)
  - `POST /api/public/check-status/` (CAPTCHA verified first -> IP rate limit 5 req/min/IP -> per-NIK 5-failure 15-min lockout -> returns `download_token` + PRD §10.6 payload if batch is `Published`)

- [ ] **Step 1: Write the failing API tests in `backend/tests/test_api_endpoints.py`**

```python
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
def test_public_check_status_blocks_unpublished_and_enforces_nik_lockout_and_ip_rate_limit(unpublished_narrated_batch):
    client = APIClient()
    # 1. Batch is Narrated (not Published) -> must return 404
    res = client.post("/api/public/check-status/", {
        "nik": "3674031208850002",
        "kk_last4": "5501",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="10.0.0.1")
    assert res.status_code == 404

    # 2. Publish batch; send 5 wrong KK attempts across rotating IPs -> 6th attempt returns 429 NIK Lockout
    unpublished_narrated_batch.status = "Published"
    unpublished_narrated_batch.save()
    for idx in range(5):
        client.post("/api/public/check-status/", {
            "nik": "3674031208850002",
            "kk_last4": "0000",
            "captcha_token": "valid_test_token",
        }, format="json", REMOTE_ADDR=f"10.0.1.{idx}")

    locked_res = client.post("/api/public/check-status/", {
        "nik": "3674031208850002",
        "kk_last4": "5501",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="10.0.2.99")
    assert locked_res.status_code == 429
    assert "dikunci sementara selama 15 menit" in locked_res.data["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_api_endpoints.py -v`
Expected: FAIL with 404 / missing URL routes

- [ ] **Step 3: Implement `permissions.py`, `excel_ingest.py`, `rate_limiter.py`, `serializers.py`, `views.py`, and `urls.py`**

Implement all REST endpoints, state transition guards, Surveyor RT scoping, `openpyxl` batch import + Excel recapitulation export (`export_batch_results_xlsx`), and public portal anti-bot shield (checking CAPTCHA before incrementing NIK failure count).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_api_endpoints.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(api): implement DRF endpoints, RBAC permissions, Excel ingest/export, and public anti-bot lockout"
```

---

### Task 5: PDF Berita Acara Generator (with QR & TMS Appendix) & Thesis Evaluation Metrics (Milestone 5 & 6 Backend)

**Files:**
- Create: `backend/core/services/pdf_generator.py`
- Create: `backend/core/services/evaluation_metrics.py`
- Modify: `backend/core/views.py`
- Modify: `backend/core/urls.py`
- Test: `backend/tests/test_pdf_and_evaluation.py`

**Interfaces:**
- Consumes: `SelectionBatch`, `SelectionResult`, `BatchCriteria`, `decrypt_nik`, `verify_pdf_download_token`
- Produces:
  - `generate_berita_acara_pdf(batch_id: int) -> bytes` (`GET /api/selection/{batch_id}/berita-acara-pdf/`)
  - `generate_individual_result_pdf(evaluation_id: int) -> bytes` (`GET /api/public/result-pdf/?token=<signed_token>`)
  - `compute_batch_evaluation_metrics(batch_id: int) -> dict` (`GET /api/selection/{batch_id}/evaluation-metrics/`)

- [ ] **Step 1: Write the failing tests in `backend/tests/test_pdf_and_evaluation.py`**

```python
import pytest
from rest_framework.test import APIClient
from core.crypto import sign_pdf_download_token
from core.services.pdf_generator import generate_berita_acara_pdf
from core.services.evaluation_metrics import compute_batch_evaluation_metrics

@pytest.mark.django_db
def test_fidelity_hallucination_metrics_and_signed_pdf_download(narrated_batch):
    metrics = compute_batch_evaluation_metrics(narrated_batch.id)
    assert metrics["fidelity_score"] >= 95.0
    assert metrics["hallucination_rate"] == 0.0

    pdf_bytes = generate_berita_acara_pdf(narrated_batch.id)
    assert pdf_bytes.startswith(b"%PDF-")

    # Public PDF endpoint requires valid signed token and Published batch status
    narrated_batch.status = "Published"
    narrated_batch.save()
    eval_obj = narrated_batch.evaluations.first()
    client = APIClient()
    assert client.get("/api/public/result-pdf/?token=invalid").status_code == 403
    valid_token = sign_pdf_download_token(eval_obj.id)
    res = client.get(f"/api/public/result-pdf/?token={valid_token}")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_pdf_and_evaluation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.services.pdf_generator'`

- [ ] **Step 3: Implement `pdf_generator.py` and `evaluation_metrics.py` and wire endpoints**

1. `evaluation_metrics.py`: Compute PRD Section 11.2 `fidelity_score` (using `BatchCriteria.frozen_weight`, handling $|K_{\text{TL}}| == 0$ as `100.0`, and matching criterion codes/names canonically) and `hallucination_rate` (normalizing Indonesian comma decimals `0,684` and percentages `60%`).
2. `pdf_generator.py`: Render official Berita Acara PDF (decrypting `nik_encrypted` only here and logging to `AuditLog`, embedding QR code and TMS appendix) and individual citizen transparency PDF (verified via `verify_pdf_download_token` on a `Published` batch).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_pdf_and_evaluation.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(reporting): add ReportLab Berita Acara PDF, signed public PDF token, and Fidelity/Hallucination evaluator"
```

---

### Task 6: Frontend Scaffolding, Civic Precision Theme, & 3-Tier Responsive AppShell (Milestone 4A)

> **MANDATORY DESIGN REVIEW GATE (AGENTS.md Section 2):** Present the responsive layout plan for `<AppShell />` (Desktop `lg:w-64` fixed sidebar, Tablet `md` drawer layout, Mobile `< 768px` slide-over drawer + unclipped Topbar + unified RBAC menu) to the user before finalizing UI screens.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/src/index.css`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/context/AuthContext.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/Topbar.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/test-utils.tsx`
- Test: `frontend/src/__tests__/AppShell.responsive.test.tsx`

**Interfaces:**
- Produces:
  - `<AppShell title={string} breadcrumb={string[]}>` with responsive drawer state (`isSidebarOpen`), RBAC-filtered navigation items (`SUPER_ADMIN`, `SURVEYOR`, `VIEWER`), and unclipped responsive Topbar.
  - `renderWithProviders(ui, { user, route })` helper in `frontend/src/test-utils.tsx`.

- [ ] **Step 1: Write the failing test in `frontend/src/__tests__/AppShell.responsive.test.tsx`**

```tsx
import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AppShell } from "../components/layout/AppShell";
import { renderWithProviders } from "../test-utils";

describe("AppShell Responsive & RBAC Layout", () => {
  it("toggles mobile drawer via hamburger button and hides SuperAdmin actions for Viewer (Lurah)", () => {
    renderWithProviders(
      <AppShell title="Pengesahan Batch" breadcrumb={["Tata Kelola", "Tahap I 2026"]}>
        <div>Konten Utama</div>
      </AppShell>,
      { user: { name: "H. Ahmad Syarif", role: "VIEWER" } }
    );
    expect(screen.queryByText(/Eksekusi Batch SAW/i)).toBeNull();
    const menuBtn = screen.getByRole("button", { name: /buka menu navigasi/i });
    fireEvent.click(menuBtn);
    expect(screen.getByRole("navigation", { name: /menu utama/i })).toHaveAttribute("data-drawer-open", "true");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/AppShell.responsive.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement Vite + Tailwind Civic Precision config, `test-utils.tsx`, and `AppShell.tsx`, `Sidebar.tsx`, `Topbar.tsx`**

Configure colors (`#003426` primary, `#0f4c3a` primary-container, `#f8f9ff` surface) and fonts (`Hanken Grotesk`, `JetBrains Mono`) in `frontend/tailwind.config.js`, and implement the responsive `AppShell`, `Sidebar`, and `Topbar`.

- [ ] **Step 4: Run test to verify it passes and commit**

Run: `npm --prefix frontend test -- --run src/__tests__/AppShell.responsive.test.tsx`
Expected: PASS

```bash
git add frontend/
git commit -m "feat(ui): scaffold React+Vite+Tailwind Civic Precision shell with mobile/tablet drawer and RBAC nav"
```

---

### Task 7: Public Portal (`/cek-bansos`) & Staff Login (`/admin/login`) (Milestone 4B)

> **MANDATORY DESIGN REVIEW GATE (AGENTS.md Section 2):** Review `.stitch/designs/portal-publik-cek-bansos.png` with the user before coding: confirm removal of the two-way anonymous appeal form (PRD Section 12.2), replacement of $C_4$ "Daya Listrik 900 VA" with "Kepemilikan Aset (Cost, 20%)", and responsive layout adjustments for Mobile, Tablet, and Desktop.

**Files:**
- Create: `frontend/src/components/public/CriteriaGapChart.tsx`
- Create: `frontend/src/pages/PublicPortalPage.tsx`
- Create: `frontend/src/pages/LoginPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/PublicPortalPage.test.tsx`

**Interfaces:**
- Consumes: `POST /api/public/check-status/`, `GET /api/public/result-pdf/?token=...`, `POST /api/auth/login/`
- Produces: `<PublicPortalPage />` and `<LoginPage />`

- [ ] **Step 1: Write the failing test in `frontend/src/__tests__/PublicPortalPage.test.tsx`**

```tsx
import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PublicPortalPage } from "../pages/PublicPortalPage";
import { renderWithProviders } from "../test-utils";

describe("PublicPortalPage PRD Compliance", () => {
  it("renders NIK + 4-digit KK + CAPTCHA verification form and excludes prohibited two-way appeal form", () => {
    renderWithProviders(<PublicPortalPage />);
    expect(screen.getByLabelText(/Nomor Induk Kependudukan \(NIK 16 Digit\)/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/4 Digit Terakhir Nomor Kartu Keluarga/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Kirim Sanggahan Anonim/i })).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/PublicPortalPage.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement `CriteriaGapChart.tsx`, `PublicPortalPage.tsx`, and `LoginPage.tsx`**

Connect `PublicPortalPage` to `/api/public/check-status/`, display masked identity (`367403******0002`, `Ahmad S******`), decision status badge (`LOLOS`, `TIDAK_LOLOS`, or `DISKUALIFIKASI_TMS`), 4-part XAI explanation, 4-criterion comparison bars ($C_1$..$C_4$), and signed-token PDF download button.

- [ ] **Step 4: Run test to verify it passes and commit**

Run: `npm --prefix frontend test -- --run src/__tests__/PublicPortalPage.test.tsx`
Expected: PASS

```bash
git add frontend/src/
git commit -m "feat(ui): add responsive Public Portal /cek-bansos and Staff Login page"
```

---

### Task 8: Admin & Surveyor Core Screens (Executive Dashboard, Criteria & Snapshot, Surveyor RT & TMS, SAW Ranking, XAI Worker Monitor) (Milestone 4C)

> **MANDATORY DESIGN REVIEW GATE (AGENTS.md Section 2):** Review the `.stitch` layout fixes for these 5 screens with the user before implementing them.

**Files:**
- Create: `frontend/src/pages/dashboard/ExecutiveDashboardPage.tsx`
- Create: `frontend/src/pages/dashboard/CriteriaManagementPage.tsx`
- Create: `frontend/src/pages/dashboard/SurveyorInputPage.tsx`
- Create: `frontend/src/pages/dashboard/SawRankingPage.tsx`
- Create: `frontend/src/pages/dashboard/XaiGeneratorPage.tsx`
- Test: `frontend/src/__tests__/DashboardScreens.test.tsx`

**Interfaces:**
- Consumes: `/api/batches/`, `/api/criteria/`, `/api/citizens/`, `/api/citizens/import-excel/`, `/api/selection/{id}/calculate/`, `/api/selection/{id}/results/`, `/api/selection/{id}/generate-xai/`, `/api/selection/{id}/xai-progress/`
- Produces: 5 responsive operational dashboard pages wrapped in `<AppShell />`

- [ ] **Step 1: Write the failing tests in `frontend/src/__tests__/DashboardScreens.test.tsx`**

```tsx
import { screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { renderWithProviders } from "../test-utils";
import { ExecutiveDashboardPage } from "../pages/dashboard/ExecutiveDashboardPage";
import { CriteriaManagementPage } from "../pages/dashboard/CriteriaManagementPage";
import { SurveyorInputPage } from "../pages/dashboard/SurveyorInputPage";
import { SawRankingPage } from "../pages/dashboard/SawRankingPage";
import { XaiGeneratorPage } from "../pages/dashboard/XaiGeneratorPage";

describe("Admin & Surveyor Operational Screens", () => {
  it("excludes Sinkronisasi DTKS button on ExecutiveDashboardPage per PRD Not-Doing", () => {
    renderWithProviders(<ExecutiveDashboardPage />);
    expect(screen.queryByRole("button", { name: /Sinkronisasi DTKS/i })).toBeNull();
  });

  it("disables weight save button when sum of weights != 1.00 on CriteriaManagementPage", () => {
    renderWithProviders(<CriteriaManagementPage />);
    const c1Input = screen.getByLabelText(/Bobot C1/i);
    fireEvent.change(c1Input, { target: { value: "0.45" } });
    expect(screen.getByText(/Total bobot harus persis bernilai 1.00/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Simpan & Validasi Bobot/i })).toBeDisabled();
  });

  it("renders real dependents count and TMS reason selector on SurveyorInputPage", () => {
    renderWithProviders(<SurveyorInputPage />, { user: { name: "Ketua RT 03", role: "SURVEYOR", rt_number: "003" } });
    expect(screen.getByLabelText(/Jumlah Tanggungan Riil/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Status Kelayakan Administratif/i)).toBeInTheDocument();
  });

  it("renders SAW ranking table and matrix detail drawer on SawRankingPage", () => {
    renderWithProviders(<SawRankingPage />);
    expect(screen.getByText(/Detail Matriks Normalisasi/i)).toBeInTheDocument();
  });

  it("displays C4 as Kepemilikan Aset in XAI payload monitor", () => {
    renderWithProviders(<XaiGeneratorPage />);
    expect(screen.getByText(/C4: Kepemilikan Aset/i)).toBeInTheDocument();
    expect(screen.queryByText(/Daya Listrik/i)).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/DashboardScreens.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement the 5 dashboard pages with responsive breakpoints (`base`, `md`, `lg`, `xl`)**

Implement `ExecutiveDashboardPage.tsx`, `CriteriaManagementPage.tsx`, `SurveyorInputPage.tsx`, `SawRankingPage.tsx`, and `XaiGeneratorPage.tsx`.

- [ ] **Step 4: Run test to verify it passes and commit**

Run: `npm --prefix frontend test -- --run src/__tests__/DashboardScreens.test.tsx`
Expected: PASS

```bash
git add frontend/src/
git commit -m "feat(ui): implement responsive Admin, Surveyor, SAW Ranking, and XAI Monitor screens"
```

---

### Task 9: Lurah Approval (`Pengesahan Berita Acara`) & Thesis Evaluation (`Evaluasi Skripsi`) Screens (Milestone 5 & 6 UI)

> **MANDATORY DESIGN REVIEW GATE (AGENTS.md Section 2):** Review `.stitch/designs/pengesahan-berita-acara-lurah.png` and the layout for the `Evaluasi Skripsi (Fidelity, Hallucination & SUS)` screen with the user before coding.

**Files:**
- Create: `frontend/src/pages/dashboard/LurahApprovalPage.tsx`
- Create: `frontend/src/pages/dashboard/ThesisEvaluationPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/__tests__/ApprovalAndEvaluation.test.tsx`

**Interfaces:**
- Consumes: `PATCH /api/selection/{batch_id}/approve/`, `PATCH /api/selection/{batch_id}/publish/`, `GET /api/selection/{batch_id}/berita-acara-pdf/`, `GET /api/selection/{batch_id}/export-excel/`, `GET /api/selection/{batch_id}/evaluation-metrics/`
- Produces: `<LurahApprovalPage />` and `<ThesisEvaluationPage />`

- [ ] **Step 1: Write the failing test in `frontend/src/__tests__/ApprovalAndEvaluation.test.tsx`**

```tsx
import { screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { renderWithProviders } from "../test-utils";
import { LurahApprovalPage } from "../pages/dashboard/LurahApprovalPage";
import { ThesisEvaluationPage } from "../pages/dashboard/ThesisEvaluationPage";

describe("Lurah Approval & Thesis Evaluation Pages", () => {
  it("renders Berita Acara preview, XAI spot-check tabs, and unclipped approval action for Viewer", () => {
    renderWithProviders(<LurahApprovalPage />, { user: { name: "H. Ahmad Syarif", role: "VIEWER" } });
    expect(screen.getByText(/Pratinjau Berita Acara Resmi/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sahkan & Terbitkan/i })).toBeInTheDocument();
    expect(screen.queryByText(/Eksekusi Batch SAW/i)).toBeNull();
  });

  it("renders Fidelity Score, Hallucination Rate, and SUS evaluation cards", () => {
    renderWithProviders(<ThesisEvaluationPage />);
    expect(screen.getByText(/Fidelity Score/i)).toBeInTheDocument();
    expect(screen.getByText(/Hallucination Rate/i)).toBeInTheDocument();
    expect(screen.getByText(/System Usability Scale \(SUS\)/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/__tests__/ApprovalAndEvaluation.test.tsx`
Expected: FAIL

- [ ] **Step 3: Implement `LurahApprovalPage.tsx` and `ThesisEvaluationPage.tsx` and wire routes in `App.tsx`**

Implement both pages and complete full-stack routing in `frontend/src/App.tsx`.

- [ ] **Step 4: Run full backend + frontend test suites and commit**

Run: `pytest backend/ -v && npm --prefix frontend test -- --run`
Expected: PASS (all backend and frontend tests green)

```bash
git add frontend/ backend/
git commit -m "feat(ui): add Lurah Berita Acara approval screen and Thesis Evaluation (Fidelity/SUS) module"
```
