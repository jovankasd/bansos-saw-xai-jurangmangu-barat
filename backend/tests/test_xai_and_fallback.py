"""
backend/tests/test_xai_and_fallback.py — Task 3: Zero-PII Sanitizer, Gemini Flash XAI Explainer,
Deterministic Fallback, and Async Worker Tests.

Tests:
  - build_anonymous_payload():
      * Zero PII enforcement (no NIK, KK, name, address in payload or serialized JSON)
      * Reads BatchCriteria.frozen_weight, NEVER Criteria.weight
      * Standard JSON serializability (no raw Decimal objects)
      * Correct calculation of avg_passed_score across LOLOS candidates
      * Handles quota=0 (zero passed) and quota >= eligible (all passed) safely
      * Rejects DISQUALIFIED (TMS) evaluations or uncalculated batches
  - generate_deterministic_fallback():
      * Computes weighted gap Δ_j * w_j = (avg_passed_score_j - normalized_score_j) * w_j
      * Canonical tie-breaking order: C1 -> C2 -> C3 -> C4
      * Borderline narrative when all Δ_j <= 0 (lost due to tie-breaker / quota)
      * Explains LOLOS status appropriately
      * Output contains standard fields (ringkasan_keputusan, faktor_penentu_utama, narasi_lengkap, rekomendasi_tindak_lanjut)
  - map_explanation_to_public_schema():
      * Maps internal/Gemini keys to public API schema {ringkasan, faktor_utama, narasi_lengkap, rekomendasi}
  - generate_xai_for_evaluation():
      * Uses Gemini API when client succeeds, saves explanation_source="GEMINI_API"
      * Validates output schema, rejects malformed JSON and retries
      * Rejects hallucinated criteria codes (e.g. C99, C5) and retries
      * Exponential backoff on retries (max 2 retries)
      * Graceful fallback to DETERMINISTIC_FALLBACK without raising HTTP 500
  - process_batch_xai_task():
      * Iterates over all ELIGIBLE candidates
      * Transitions batch.status to "Narrated" ONLY when ALL eligible candidates have narratives
      * Creates AuditLog entry (XAI_GENERATED)
      * Rejects batches not in Calculated status
  - Security & Zero-PII Audit:
      * OWASP LLM02 Sensitive Information Disclosure & UU PDP No. 27/2022 verification
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from core.models import (
    AuditLog,
    BatchCriteria,
    Citizen,
    Criteria,
    Evaluation,
    EvaluationDetail,
    Period,
    SelectionBatch,
    SelectionResult,
)
from core.services.saw_engine import calculate_batch_saw
from core.services.sanitizer import build_anonymous_payload
from core.services.deterministic_fallback import generate_deterministic_fallback
from core.services.xai_explainer import (
    generate_xai_for_evaluation,
    map_explanation_to_public_schema,
    validate_xai_output,
)
from core.tasks import process_batch_xai_task


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _seed(db):
    call_command("seed_initial_data", verbosity=0)


def _make_citizen(raw_nik: str, name: str, kk_last4: str = "5501", address: str = "Jl. Melati 1") -> Citizen:
    citizen, _ = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4=kk_last4,
        full_name=name,
        address=address,
        rt="003",
        rw="001",
    )
    return citizen


def _make_batch(quota: int = 2) -> SelectionBatch:
    period = Period.objects.create(
        name=f"Period XAI {timezone.now().timestamp()}",
        year=2026,
        semester=1,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )
    return SelectionBatch.objects.create(
        period=period,
        name="Batch Test XAI",
        quota=quota,
        status=SelectionBatch.Status.COLLECTING,
    )


def _add_evaluation(
    batch: SelectionBatch,
    citizen: Citizen,
    *,
    eligibility: str = "ELIGIBLE",
    tms_reason: str = "",
    real_dependents: int = 3,
    crips: dict[str, int] | None = None,
) -> Evaluation:
    eval_obj = Evaluation.objects.create(
        batch=batch,
        citizen=citizen,
        eligibility_status=eligibility,
        tms_reason=tms_reason,
        real_dependents_count=real_dependents,
    )
    if crips:
        c_map = {c.code: c for c in Criteria.objects.all()}
        for code, val in crips.items():
            EvaluationDetail.objects.create(
                evaluation=eval_obj,
                criteria=c_map[code],
                raw_crips_value=val,
            )
    return eval_obj


@pytest.fixture
def calculated_batch_with_evaluations():
    """
    Creates a batch with 1 TMS citizen and 4 ELIGIBLE citizens, then calculates SAW.
    Quota = 2 (so top 2 LOLOS, bottom 2 TIDAK_LOLOS).
    """
    batch = _make_batch(quota=2)

    # 1 TMS citizen
    c_tms = _make_citizen("3674039999990001", "Pak Budi ASN", "1111", "Jl. ASN No 1")
    _add_evaluation(
        batch, c_tms,
        eligibility="DISQUALIFIED",
        tms_reason="ASN",
        crips={"C1": 1, "C2": 5, "C3": 1, "C4": 1},
    )

    # 4 ELIGIBLE citizens
    # KPM 1: Low income (C1=1), high dependents (C2=5), poor housing (C3=1), no asset (C4=1) -> Best (LOLOS)
    c1 = _make_citizen("3674031111110001", "Ahmad Subarjo", "5501", "Jl. Jurangmangu Timur No. 1")
    _add_evaluation(batch, c1, real_dependents=4, crips={"C1": 1, "C2": 5, "C3": 1, "C4": 1})

    # KPM 2: Good priority -> LOLOS
    c2 = _make_citizen("3674032222220002", "Siti Aminah", "5502", "Jl. Jurangmangu Barat No. 2")
    _add_evaluation(batch, c2, real_dependents=3, crips={"C1": 1, "C2": 4, "C3": 2, "C4": 1})

    # KPM 3: Moderate priority -> TIDAK_LOLOS (Rank 3)
    c3 = _make_citizen("3674033333330003", "Bambang Pamungkas", "5503", "Jl. Ceger Raya No. 3")
    _add_evaluation(batch, c3, real_dependents=2, crips={"C1": 2, "C2": 3, "C3": 3, "C4": 2})

    # KPM 4: Highest income / lowest need -> TIDAK_LOLOS (Rank 4)
    c4 = _make_citizen("3674034444440004", "Dewi Lestari", "5504", "Jl. Pondok Aren No. 4")
    _add_evaluation(batch, c4, real_dependents=1, crips={"C1": 4, "C2": 2, "C3": 4, "C4": 3})

    calculate_batch_saw(batch.id, performed_by="test_admin")
    batch.refresh_from_db()
    return batch


# ---------------------------------------------------------------------------
# Tests: Sanitizer & Zero-PII
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_anonymous_payload_contains_zero_pii_and_uses_frozen_weights(calculated_batch_with_evaluations):
    """
    FR-04, FR-01, UU PDP No. 27/2022:
    Payload MUST NEVER contain citizen PII, and MUST use BatchCriteria.frozen_weight even
    if master Criteria.weight is mutated after calculation.
    """
    batch = calculated_batch_with_evaluations

    # Mutate master Criteria C1 weight to 0.90
    Criteria.objects.filter(code="C1").update(weight=Decimal("0.90"))

    eval_obj = batch.evaluations.filter(eligibility_status="ELIGIBLE").first()
    payload = build_anonymous_payload(eval_obj.id)

    # 1. Zero-PII checks
    serialized = json.dumps(payload)
    citizen = eval_obj.citizen
    assert citizen.full_name not in serialized
    assert citizen.full_name_masked not in serialized
    assert citizen.nik_masked not in serialized
    assert citizen.nik_encrypted not in serialized
    assert citizen.nik_hash not in serialized
    assert citizen.kk_last4 not in serialized
    assert citizen.address not in serialized
    assert citizen.rt not in serialized
    assert citizen.rw not in serialized

    # 2. Key schema check (PRD Section 8.1)
    assert "applicant_code" in payload
    assert "rank" in payload
    assert "quota" in payload
    assert "status" in payload
    assert "final_score" in payload
    assert "cutoff_score" in payload
    assert "criteria_data" in payload

    # 3. Frozen weight check (must still be 0.30, NOT 0.90)
    c1_item = next(item for item in payload["criteria_data"] if item["code"] == "C1")
    assert c1_item["weight"] == 0.30
    assert isinstance(c1_item["weight"], float)
    assert isinstance(payload["final_score"], float)
    assert isinstance(payload["cutoff_score"], float)


@pytest.mark.django_db
def test_anonymous_payload_criteria_data_fields_and_avg_passed_score(calculated_batch_with_evaluations):
    """
    Verify criteria_data structure: code, name, type, weight, raw_crips_label,
    normalized_score, avg_passed_score.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="TIDAK_LOLOS").first()
    payload = build_anonymous_payload(eval_obj.id)

    assert len(payload["criteria_data"]) == 4
    for item in payload["criteria_data"]:
        assert set(item.keys()) == {
            "code",
            "name",
            "type",
            "weight",
            "raw_crips_label",
            "normalized_score",
            "avg_passed_score",
        }
        assert item["type"] in ("COST", "BENEFIT")
        assert isinstance(item["normalized_score"], float)
        assert isinstance(item["avg_passed_score"], float)
        assert len(item["raw_crips_label"]) > 0


@pytest.mark.django_db
def test_anonymous_payload_zero_passed_or_all_passed():
    """
    Check edge cases where quota=0 (no passed candidates) and quota=10 (all pass).
    avg_passed_score must not fail with ZeroDivisionError.
    """
    # 1. Quota 0
    batch_zero = _make_batch(quota=0)
    c1 = _make_citizen("3674035555550001", "Kandidat Satu", "1234")
    c2 = _make_citizen("3674035555550002", "Kandidat Dua", "1235")
    e1 = _add_evaluation(batch_zero, c1, crips={"C1": 1, "C2": 5, "C3": 1, "C4": 1})
    e2 = _add_evaluation(batch_zero, c2, crips={"C1": 2, "C2": 4, "C3": 2, "C4": 2})
    calculate_batch_saw(batch_zero.id, performed_by="admin")

    payload_zero = build_anonymous_payload(e1.id)
    assert payload_zero["status"] == "TIDAK_LOLOS"
    # avg_passed_score should fallback gracefully (e.g., to candidate's own normalized score or 0.0)
    for item in payload_zero["criteria_data"]:
        assert isinstance(item["avg_passed_score"], float)

    # 2. Quota all pass
    batch_all = _make_batch(quota=5)
    c3 = _make_citizen("3674035555550003", "Kandidat Tiga", "1236")
    e3 = _add_evaluation(batch_all, c3, crips={"C1": 1, "C2": 5, "C3": 1, "C4": 1})
    calculate_batch_saw(batch_all.id, performed_by="admin")
    payload_all = build_anonymous_payload(e3.id)
    assert payload_all["status"] == "LOLOS"
    for item in payload_all["criteria_data"]:
        assert item["avg_passed_score"] == item["normalized_score"]


@pytest.mark.django_db
def test_anonymous_payload_rejects_disqualified_or_uncalculated(calculated_batch_with_evaluations):
    """
    Disqualified (TMS) candidates must raise ValidationError (they get INELIGIBLE_NOTICE, not XAI).
    Uncalculated evaluations also raise ValidationError.
    """
    batch = calculated_batch_with_evaluations
    tms_eval = batch.evaluations.get(eligibility_status="DISQUALIFIED")
    with pytest.raises(ValidationError, match="TMS"):
        build_anonymous_payload(tms_eval.id)

    # Uncalculated evaluation
    uncalc_batch = _make_batch(quota=1)
    c = _make_citizen("3674036666660001", "Warga Baru", "9999")
    uncalc_eval = _add_evaluation(uncalc_batch, c, crips={"C1": 1, "C2": 5, "C3": 1, "C4": 1})
    with pytest.raises(ValidationError, match="belum memiliki hasil kalkulasi"):
        build_anonymous_payload(uncalc_eval.id)


# ---------------------------------------------------------------------------
# Tests: Deterministic Fallback & Key Mapping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fallback_selects_highest_weighted_gap_and_maps_public_keys(calculated_batch_with_evaluations):
    """
    FR-05: When Gemini fails, deterministic fallback selects the criterion with the
    maximum weighted gap Δ_j * w_j = (avg_passed_score_j - normalized_score_j) * w_j.
    """
    batch = calculated_batch_with_evaluations
    failed_eval = batch.evaluations.filter(result__status="TIDAK_LOLOS").order_by("-result__ranking").first()
    payload = build_anonymous_payload(failed_eval.id)

    fallback_res = generate_deterministic_fallback(payload)

    assert "ringkasan_keputusan" in fallback_res
    assert "faktor_penentu_utama" in fallback_res
    assert "narasi_lengkap" in fallback_res
    assert "rekomendasi_tindak_lanjut" in fallback_res
    assert "primary_criterion_code" in fallback_res

    # Check mapping to public schema
    mapped = map_explanation_to_public_schema(fallback_res)
    assert set(mapped.keys()) == {"ringkasan", "faktor_utama", "narasi_lengkap", "rekomendasi"}
    assert mapped["ringkasan"] == fallback_res["ringkasan_keputusan"]
    assert mapped["faktor_utama"] == fallback_res["faktor_penentu_utama"]
    assert mapped["narasi_lengkap"] == fallback_res["narasi_lengkap"]
    assert mapped["rekomendasi"] == fallback_res["rekomendasi_tindak_lanjut"]


@pytest.mark.django_db
def test_fallback_canonical_tie_break_order_c1_to_c4():
    """
    When multiple criteria produce identical weighted gap Δ_j * w_j, break tie by
    canonical criterion order: C1 -> C2 -> C3 -> C4.
    """
    # Create payload where C1 and C2 have identical weighted gap
    # e.g., C1: gap=0.2, w=0.3 -> 0.06; C2: gap=0.24, w=0.25 -> 0.06
    payload = {
        "applicant_code": "KPM-TEST",
        "rank": 4,
        "quota": 3,
        "status": "TIDAK_LOLOS",
        "final_score": 0.70,
        "cutoff_score": 0.75,
        "criteria_data": [
            {
                "code": "C1",
                "name": "Pendapatan Keluarga",
                "type": "COST",
                "weight": 0.30,
                "raw_crips_label": "Sedang",
                "normalized_score": 0.60,
                "avg_passed_score": 0.80,  # Δ = 0.20 * 0.30 = 0.060
            },
            {
                "code": "C2",
                "name": "Jumlah Tanggungan",
                "type": "BENEFIT",
                "weight": 0.25,
                "raw_crips_label": "2 Orang",
                "normalized_score": 0.56,
                "avg_passed_score": 0.80,  # Δ = 0.24 * 0.25 = 0.060
            },
            {
                "code": "C3",
                "name": "Kondisi Tempat Tinggal",
                "type": "COST",
                "weight": 0.25,
                "raw_crips_label": "Layak",
                "normalized_score": 0.80,
                "avg_passed_score": 0.80,  # Δ = 0.0
            },
            {
                "code": "C4",
                "name": "Kepemilikan Aset",
                "type": "COST",
                "weight": 0.20,
                "raw_crips_label": "Motor",
                "normalized_score": 0.70,
                "avg_passed_score": 0.70,  # Δ = 0.0
            },
        ],
    }

    fallback_res = generate_deterministic_fallback(payload)
    # C1 should be chosen over C2 due to canonical priority C1 -> C2 -> C3 -> C4
    assert fallback_res["primary_criterion_code"] == "C1"
    assert "Pendapatan Keluarga" in fallback_res["faktor_penentu_utama"][0]


@pytest.mark.django_db
def test_fallback_borderline_tie_break_when_all_gaps_non_positive():
    """
    Borderline candidate: candidate who failed (TIDAK_LOLOS) purely due to quota/tie-breaker
    even though all normalized scores are >= avg_passed_score (all Δ_j <= 0).
    Must return specific borderline narrative.
    """
    payload = {
        "applicant_code": "KPM-BORDER",
        "rank": 4,
        "quota": 3,
        "status": "TIDAK_LOLOS",
        "final_score": 0.85,
        "cutoff_score": 0.85,
        "criteria_data": [
            {
                "code": "C1",
                "name": "Pendapatan Keluarga",
                "type": "COST",
                "weight": 0.30,
                "raw_crips_label": "Rendah",
                "normalized_score": 0.85,
                "avg_passed_score": 0.85,  # Δ = 0
            },
            {
                "code": "C2",
                "name": "Jumlah Tanggungan",
                "type": "BENEFIT",
                "weight": 0.25,
                "raw_crips_label": "4 Orang",
                "normalized_score": 0.85,
                "avg_passed_score": 0.80,  # Δ = -0.05
            },
            {
                "code": "C3",
                "name": "Kondisi Tempat Tinggal",
                "type": "COST",
                "weight": 0.25,
                "raw_crips_label": "Kurang Layak",
                "normalized_score": 0.85,
                "avg_passed_score": 0.85,  # Δ = 0
            },
            {
                "code": "C4",
                "name": "Kepemilikan Aset",
                "type": "COST",
                "weight": 0.20,
                "raw_crips_label": "Sederhana",
                "normalized_score": 0.85,
                "avg_passed_score": 0.85,  # Δ = 0
            },
        ],
    }

    fallback_res = generate_deterministic_fallback(payload)
    assert "batas kuota" in fallback_res["narasi_lengkap"].lower() or "tie-breaker" in fallback_res["narasi_lengkap"].lower()
    assert len(fallback_res["faktor_penentu_utama"]) > 0


@pytest.mark.django_db
def test_fallback_for_status_lolos():
    """
    Deterministic fallback for a LOLOS candidate:
    Highlights priority criteria and reminds candidate of physical document verification.
    """
    payload = {
        "applicant_code": "KPM-WIN",
        "rank": 1,
        "quota": 2,
        "status": "LOLOS",
        "final_score": 0.95,
        "cutoff_score": 0.85,
        "criteria_data": [
            {
                "code": "C1",
                "name": "Pendapatan Keluarga",
                "type": "COST",
                "weight": 0.30,
                "raw_crips_label": "Sangat Rendah",
                "normalized_score": 1.0,
                "avg_passed_score": 0.90,
            },
            {
                "code": "C2",
                "name": "Jumlah Tanggungan",
                "type": "BENEFIT",
                "weight": 0.25,
                "raw_crips_label": "5 Orang",
                "normalized_score": 1.0,
                "avg_passed_score": 0.85,
            },
            {
                "code": "C3",
                "name": "Kondisi Tempat Tinggal",
                "type": "COST",
                "weight": 0.25,
                "raw_crips_label": "Kurang Layak",
                "normalized_score": 0.8,
                "avg_passed_score": 0.80,
            },
            {
                "code": "C4",
                "name": "Kepemilikan Aset",
                "type": "COST",
                "weight": 0.20,
                "raw_crips_label": "Sederhana",
                "normalized_score": 1.0,
                "avg_passed_score": 0.80,
            },
        ],
    }

    fallback_res = generate_deterministic_fallback(payload)
    assert "selamat" in fallback_res["narasi_lengkap"].lower() or "lolos" in fallback_res["ringkasan_keputusan"].lower()
    assert "verifikasi" in fallback_res["narasi_lengkap"].lower() or "verifikasi" in fallback_res["rekomendasi_tindak_lanjut"].lower()


# ---------------------------------------------------------------------------
# Tests: Gemini Explainer, Validation, Retries, & Fallback Switch
# ---------------------------------------------------------------------------


class MockGeminiClient:
    """Mock for google.genai Client."""
    def __init__(self, response_text: str | None = None, side_effect: Exception | None = None):
        self.response_text = response_text
        self.side_effect = side_effect
        self.call_count = 0
        self.recorded_calls = []

    class _Models:
        def __init__(self, outer):
            self.outer = outer

        def generate_content(self, model: str, contents: Any, config: Any):
            self.outer.call_count += 1
            self.outer.recorded_calls.append({"model": model, "contents": contents, "config": config})
            if self.outer.side_effect:
                raise self.outer.side_effect

            class _Response:
                def __init__(self, text):
                    self.text = text

            return _Response(self.outer.response_text)

    @property
    def models(self):
        return self._Models(self)


@pytest.mark.django_db
def test_xai_explainer_with_mocked_gemini_success(calculated_batch_with_evaluations):
    """
    When Gemini API succeeds with valid JSON, generate_xai_for_evaluation saves
    explanation_source="GEMINI_API" and updates SelectionResult.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="LOLOS").first()

    valid_json = json.dumps({
        "ringkasan_keputusan": "Pemohon dinyatakan lolos seleksi bantuan sosial berdasarkan prioritas kebutuhan ekonomi.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)", "Jumlah Tanggungan (C2)"],
        "narasi_lengkap": "Selamat, Bapak/Ibu Pemohon dinyatakan lolos seleksi penerima bantuan sosial berdasarkan evaluasi SAW dengan menempati peringkat 1 dari kuota 2 penerima. Bobot preferensi C1 dan C2 menjadi kontributor tertinggi.",
        "rekomendasi_tindak_lanjut": "Silakan hadir di kantor kelurahan pada jadwal yang ditentukan untuk verifikasi berkas.",
    })

    client = MockGeminiClient(response_text=valid_json)
    res = generate_xai_for_evaluation(eval_obj.id, gemini_client=client, backoff_seconds=0)

    assert res.explanation_source == SelectionResult.ExplanationSource.GEMINI_API
    assert "lolos seleksi" in res.ai_narrative
    assert res.ai_payload_response["ringkasan_keputusan"] == "Pemohon dinyatakan lolos seleksi bantuan sosial berdasarkan prioritas kebutuhan ekonomi."
    assert client.call_count == 1
    assert res.narrated_at is not None


@pytest.mark.django_db
def test_xai_explainer_retries_and_falls_back_on_error(calculated_batch_with_evaluations):
    """
    FR-05: When Gemini throws exceptions (e.g. RateLimitError 429), it retries up to 2 times
    (3 calls total), then switches to DETERMINISTIC_FALLBACK without raising HTTP 500.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="TIDAK_LOLOS").first()

    client = MockGeminiClient(side_effect=TimeoutError("429 Resource Exhausted / Rate Limit"))
    res = generate_xai_for_evaluation(eval_obj.id, gemini_client=client, backoff_seconds=0)

    assert client.call_count == 3  # Initial attempt + 2 retries
    assert res.explanation_source == SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK
    assert len(res.ai_narrative) > 0
    assert "faktor_penentu_utama" in res.ai_payload_response


@pytest.mark.django_db
def test_xai_explainer_rejects_hallucinated_criteria_and_falls_back(calculated_batch_with_evaluations):
    """
    If Gemini hallucinates non-existent criteria (e.g. C99, Daya Listrik 900 VA, C5),
    validate_xai_output rejects it, retries, and switches to DETERMINISTIC_FALLBACK.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="TIDAK_LOLOS").first()

    hallucinated_json = json.dumps({
        "ringkasan_keputusan": "Pemohon tidak lolos.",
        "faktor_penentu_utama": ["Daya Listrik 900VA (C99)", "Kepemilikan Mobil Mewah (C5)"],
        "narasi_lengkap": "Pemohon memiliki kriteria C99 yang tidak memadai.",
        "rekomendasi_tindak_lanjut": "Perbaiki daya listrik.",
    })

    client = MockGeminiClient(response_text=hallucinated_json)
    res = generate_xai_for_evaluation(eval_obj.id, gemini_client=client, backoff_seconds=0)

    assert client.call_count == 3
    assert res.explanation_source == SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK


@pytest.mark.django_db
def test_xai_explainer_rejects_malformed_json_and_falls_back(calculated_batch_with_evaluations):
    """
    If Gemini returns non-JSON or missing required keys, validate_xai_output rejects it
    and switches to DETERMINISTIC_FALLBACK.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="TIDAK_LOLOS").first()

    malformed_json = "Maaf, saya tidak dapat memproses data ini sebagai JSON."
    client = MockGeminiClient(response_text=malformed_json)
    res = generate_xai_for_evaluation(eval_obj.id, gemini_client=client, backoff_seconds=0)

    assert client.call_count == 3
    assert res.explanation_source == SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK


# ---------------------------------------------------------------------------
# Tests: Async Worker (process_batch_xai_task)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_process_batch_xai_task_transitions_to_narrated(calculated_batch_with_evaluations):
    """
    process_batch_xai_task processes all ELIGIBLE evaluations in the batch.
    Once all eligible evaluations have narratives, batch.status transitions to "Narrated".
    """
    batch = calculated_batch_with_evaluations
    assert batch.status == SelectionBatch.Status.CALCULATED

    # Run with a client that succeeds
    valid_json = json.dumps({
        "ringkasan_keputusan": "Hasil seleksi bansos diumumkan secara transparan.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Berdasarkan kalkulasi SAW, keputusan telah diverifikasi secara objektif.",
        "rekomendasi_tindak_lanjut": "Menunggu instruksi lebih lanjut dari pengurus RT setempat.",
    })
    client = MockGeminiClient(response_text=valid_json)

    summary = process_batch_xai_task(batch.id, gemini_client=client)

    batch.refresh_from_db()
    assert batch.status == SelectionBatch.Status.NARRATED
    assert summary["status"] == SelectionBatch.Status.NARRATED
    assert summary["narrated_count"] == 4
    assert summary["all_narrated"] is True

    # Check AuditLog
    log = AuditLog.objects.filter(batch=batch, action=AuditLog.Action.XAI_GENERATED).first()
    assert log is not None


@pytest.mark.django_db
def test_process_batch_xai_task_rejects_invalid_batch_status():
    """
    process_batch_xai_task must reject batches that are not Calculated (e.g. Draft, Approved, Published).
    """
    batch = _make_batch(quota=2)
    batch.status = SelectionBatch.Status.DRAFT
    batch.save()

    with pytest.raises(ValidationError, match="Hanya batch berstatus 'Calculated'"):
        process_batch_xai_task(batch.id)

    batch.status = SelectionBatch.Status.PUBLISHED
    batch.save()

    with pytest.raises(ValidationError, match="Hanya batch berstatus 'Calculated'"):
        process_batch_xai_task(batch.id)


# ---------------------------------------------------------------------------
# Tests: Security & Zero-PII Audit (OWASP LLM02 & UU PDP)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_security_audit_zero_pii_in_llm_prompt_and_network_payload(calculated_batch_with_evaluations):
    """
    Security Auditor verification:
    Inspect all recorded calls to Gemini Client. Ensure NOT A SINGLE PII item
    (name, NIK, KK, address, RT, RW) appears in prompt contents or config.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(eligibility_status="ELIGIBLE").first()
    citizen = eval_obj.citizen

    valid_json = json.dumps({
        "ringkasan_keputusan": "Keputusan valid.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Narasi valid.",
        "rekomendasi_tindak_lanjut": "Rekomendasi valid.",
    })
    client = MockGeminiClient(response_text=valid_json)

    generate_xai_for_evaluation(eval_obj.id, gemini_client=client, backoff_seconds=0)

    assert len(client.recorded_calls) == 1
    call_contents = str(client.recorded_calls[0]["contents"])
    call_config = str(client.recorded_calls[0]["config"])

    for pii in [
        citizen.full_name,
        citizen.full_name_masked,
        citizen.nik_masked,
        citizen.kk_last4,
        citizen.address,
        citizen.rt,
        citizen.rw,
    ]:
        if pii:
            assert pii not in call_contents, f"PII leak detected in LLM prompt: {pii}"
            assert pii not in call_config, f"PII leak detected in LLM config: {pii}"


# ---------------------------------------------------------------------------
# Tests: Hardened Edge Cases, Anti-Hallucination, & Task Worker Modes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_xai_output_strips_markdown_code_fences():
    """
    LLM output wrapped in markdown ```json ... ``` code blocks must be cleanly stripped and parsed.
    """
    raw_markdown = """```json
{
  "ringkasan_keputusan": "Pemohon memenuhi prioritas bantuan sosial.",
  "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
  "narasi_lengkap": "Berdasarkan evaluasi objektif, berkas disetujui.",
  "rekomendasi_tindak_lanjut": "Menunggu verifikasi fisik."
}
```"""
    parsed = validate_xai_output(raw_markdown, allowed_criteria_codes={"C1", "C2", "C3", "C4"})
    assert parsed["ringkasan_keputusan"] == "Pemohon memenuhi prioritas bantuan sosial."
    assert parsed["primary_criterion_code"] == "C1"


@pytest.mark.django_db
def test_validate_xai_output_rejects_hallucinated_code_in_summary_or_recommendation():
    """
    Hallucinated criterion codes must be caught even when they appear in ringkasan_keputusan
    or rekomendasi_tindak_lanjut (full field coverage).
    """
    # 1. Hallucinated in summary
    bad_summary_json = {
        "ringkasan_keputusan": "Pemohon ditolak akibat kriteria C99 tidak memenuhi syarat.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Keluarga memiliki pendapatan cukup.",
        "rekomendasi_tindak_lanjut": "Konsultasi RT.",
    }
    with pytest.raises(ValueError, match="Halusinasi kode kriteria terdeteksi.*C99"):
        validate_xai_output(bad_summary_json, allowed_criteria_codes={"C1", "C2", "C3", "C4"})

    # 2. Hallucinated 'daya listrik' in recommendation
    bad_rec_json = {
        "ringkasan_keputusan": "Pemohon tidak lolos.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Keluarga memiliki pendapatan cukup.",
        "rekomendasi_tindak_lanjut": "Turunkan daya listrik rumah tangga ke 450 VA.",
    }
    with pytest.raises(ValueError, match="Daya Listrik"):
        validate_xai_output(bad_rec_json, allowed_criteria_codes={"C1", "C2", "C3", "C4"})


@pytest.mark.django_db
def test_validate_xai_output_rejects_hallucinated_numbers_rank_and_quota():
    """
    PRD Section 11.2 & Task 3: Text mentioning fabricated rank or quota numbers
    must be rejected to ensure numeric fidelity.
    """
    payload = {
        "applicant_code": "KPM-010",
        "rank": 35,
        "quota": 30,
        "status": "TIDAK_LOLOS",
        "final_score": 0.6840,
        "cutoff_score": 0.7250,
        "criteria_data": [
            {"code": "C1", "name": "Pendapatan Keluarga", "weight": 0.30, "normalized_score": 0.60, "avg_passed_score": 0.85},
        ],
    }

    # Wrong rank: mentions peringkat 99 instead of 35
    hallucinated_rank = {
        "ringkasan_keputusan": "Pemohon berada di peringkat 99 dari kuota 30.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Berdasarkan seleksi, pemohon berada di peringkat 99.",
        "rekomendasi_tindak_lanjut": "Konsultasi ke RT.",
    }
    with pytest.raises(ValueError, match="Halusinasi angka terdeteksi.*peringkat 99.*35"):
        validate_xai_output(hallucinated_rank, allowed_criteria_codes={"C1"}, payload=payload)

    # Wrong quota: mentions kuota 10 instead of 30
    hallucinated_quota = {
        "ringkasan_keputusan": "Pemohon belum masuk kuota.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Pemohon berada di peringkat 35 dari kuota 10 penerima.",
        "rekomendasi_tindak_lanjut": "Konsultasi ke RT.",
    }
    with pytest.raises(ValueError, match="Halusinasi angka terdeteksi.*kuota 10.*30"):
        validate_xai_output(hallucinated_quota, allowed_criteria_codes={"C1"}, payload=payload)


@pytest.mark.django_db
def test_validate_xai_output_rejects_hallucinated_decimal_score():
    """
    PRD Section 11.2: Fabricated decimal scores (e.g. 0.9999) that do not correspond
    to any score in the payload must trigger numeric hallucination rejection.
    """
    payload = {
        "applicant_code": "KPM-010",
        "rank": 35,
        "quota": 30,
        "status": "TIDAK_LOLOS",
        "final_score": 0.6840,
        "cutoff_score": 0.7250,
        "criteria_data": [
            {"code": "C1", "name": "Pendapatan", "weight": 0.30, "normalized_score": 0.60, "avg_passed_score": 0.85},
        ],
    }

    hallucinated_score = {
        "ringkasan_keputusan": "Pemohon belum masuk kuota.",
        "faktor_penentu_utama": ["Pendapatan (C1)"],
        "narasi_lengkap": "Pemohon memperoleh skor 0.9999 yang tidak sesuai dengan kalkulasi.",
        "rekomendasi_tindak_lanjut": "Konsultasi ke RT.",
    }
    with pytest.raises(ValueError, match="Halusinasi nilai numerik terdeteksi.*0.9999"):
        validate_xai_output(hallucinated_score, allowed_criteria_codes={"C1"}, payload=payload)


@pytest.mark.django_db
def test_validate_xai_output_extracts_primary_criterion_code_for_fidelity():
    """
    PRD Section 11.2 Fidelity Score: Output dictionary must include primary_criterion_code
    extracted from faktor_penentu_utama.
    """
    data = {
        "ringkasan_keputusan": "Keputusan SAW sah.",
        "faktor_penentu_utama": ["Kondisi Tempat Tinggal (C3)", "Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Evaluasi menunjukkan kriteria C3 menjadi faktor utama.",
        "rekomendasi_tindak_lanjut": "Konsultasi ke RT.",
    }
    validated = validate_xai_output(data, allowed_criteria_codes={"C1", "C2", "C3", "C4"})
    assert validated["primary_criterion_code"] == "C3"


@pytest.mark.django_db
def test_map_explanation_to_public_schema_handles_existing_public_keys_and_edge_cases():
    """
    map_explanation_to_public_schema must handle internal keys, existing public keys,
    and non-dict inputs idempotently.
    """
    # Non-dict input
    assert map_explanation_to_public_schema(None) == {
        "ringkasan": "",
        "faktor_utama": [],
        "narasi_lengkap": "",
        "rekomendasi": "",
    }

    # Already mapped public keys
    already_mapped = {
        "ringkasan": "Sudah dalam skema publik.",
        "faktor_utama": ["C1"],
        "narasi_lengkap": "Narasi publik.",
        "rekomendasi": "Rekomendasi publik.",
    }
    mapped = map_explanation_to_public_schema(already_mapped)
    assert mapped["ringkasan"] == "Sudah dalam skema publik."
    assert mapped["faktor_utama"] == ["C1"]
    assert mapped["rekomendasi"] == "Rekomendasi publik."


@pytest.mark.django_db
def test_sanitizer_rejects_incomplete_evaluation_details(calculated_batch_with_evaluations):
    """
    If an evaluation is missing an EvaluationDetail for an active criterion,
    build_anonymous_payload must raise ValidationError instead of silently dropping it.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(eligibility_status="ELIGIBLE").first()

    # Delete one detail (e.g. C4)
    detail_c4 = eval_obj.details.filter(criteria__code="C4").first()
    assert detail_c4 is not None
    detail_c4.delete()

    with pytest.raises(ValidationError, match="Detail kriteria 'C4'"):
        build_anonymous_payload(eval_obj.id)


@pytest.mark.django_db
def test_sanitizer_falls_back_to_batch_cutoff_score(calculated_batch_with_evaluations):
    """
    If SelectionResult.cutoff_score is None, sanitizer should fallback to batch.cutoff_score.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(eligibility_status="ELIGIBLE").first()
    res = eval_obj.result
    res.cutoff_score = None
    res.save()

    batch.cutoff_score = Decimal("0.7500")
    batch.save()

    payload = build_anonymous_payload(eval_obj.id)
    assert payload["cutoff_score"] == 0.75


@pytest.mark.django_db
def test_process_batch_xai_task_with_single_evaluation_id(calculated_batch_with_evaluations):
    """
    PRD Section 10.4: POST /api/selection/{batch_id}/generate-xai/?evaluation_id=45
    Worker can process a single targeted evaluation. In this case, batch status remains Calculated
    until all candidates are narrated.
    """
    batch = calculated_batch_with_evaluations
    eligible_evals = list(batch.evaluations.filter(eligibility_status="ELIGIBLE"))
    target = eligible_evals[0]

    valid_json = json.dumps({
        "ringkasan_keputusan": "Evaluasi spesifik berhasil diproses.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Narasi tunggal selesai.",
        "rekomendasi_tindak_lanjut": "Menunggu instruksi.",
    })
    client = MockGeminiClient(response_text=valid_json)

    summary = process_batch_xai_task(batch.id, gemini_client=client, evaluation_id=target.id)

    target.refresh_from_db()
    assert target.result.ai_narrative == "Narasi tunggal selesai."
    assert summary["narrated_count"] == 1
    assert summary["all_narrated"] is False
    # Batch status should NOT transition to Narrated because only 1 of 4 is narrated
    batch.refresh_from_db()
    assert batch.status == SelectionBatch.Status.CALCULATED


@pytest.mark.django_db
def test_process_batch_xai_task_skips_already_narrated_candidates_idempotently(calculated_batch_with_evaluations):
    """
    When re-running process_batch_xai_task, candidates that already have narratives
    must be skipped (unless force=True), preventing redundant API consumption.
    """
    batch = calculated_batch_with_evaluations
    valid_json = json.dumps({
        "ringkasan_keputusan": "Narasi valid.",
        "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
        "narasi_lengkap": "Narasi lengkap.",
        "rekomendasi_tindak_lanjut": "Rekomendasi tindak lanjut.",
    })
    client1 = MockGeminiClient(response_text=valid_json)

    # First run processes all 4 candidates
    process_batch_xai_task(batch.id, gemini_client=client1)
    assert client1.call_count == 4

    # Second run with force=False must skip all 4 candidates
    client2 = MockGeminiClient(response_text=valid_json)
    summary2 = process_batch_xai_task(batch.id, gemini_client=client2, force=False)
    assert client2.call_count == 0  # 0 calls made because all 4 were skipped
    assert summary2["all_narrated"] is True
    assert summary2["gemini_success"] == 4


@pytest.mark.django_db
def test_process_batch_xai_task_blocks_narrated_status_when_generation_fails_partially(calculated_batch_with_evaluations):
    """
    If generation fails for any candidate, batch status MUST NOT transition to Narrated.
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(eligibility_status="ELIGIBLE").first()

    # Simulate missing SelectionResult for this evaluation to simulate an unresolvable failure
    eval_obj.result.delete()

    summary = process_batch_xai_task(batch.id, gemini_client=None)

    batch.refresh_from_db()
    assert summary["all_narrated"] is False
    assert batch.status == SelectionBatch.Status.CALCULATED


@pytest.mark.django_db
def test_generate_xai_for_evaluation_duck_typed_client_support(calculated_batch_with_evaluations):
    """
    generate_xai_for_evaluation must support custom duck-typed clients that implement
    either client.models.generate_content or client.generate(user_prompt).
    """
    batch = calculated_batch_with_evaluations
    eval_obj = batch.evaluations.filter(result__status="LOLOS").first()

    class CustomDuckClient:
        def __init__(self):
            self.calls = 0

        def generate(self, user_prompt: str) -> str:
            self.calls += 1
            return json.dumps({
                "ringkasan_keputusan": "Duck-typed client success.",
                "faktor_penentu_utama": ["Pendapatan Keluarga (C1)"],
                "narasi_lengkap": "Duck-typed client output validated.",
                "rekomendasi_tindak_lanjut": "Menunggu instruksi.",
            })

    duck_client = CustomDuckClient()
    result = generate_xai_for_evaluation(eval_obj.id, gemini_client=duck_client, backoff_seconds=0)

    assert duck_client.calls == 1
    assert result.explanation_source == SelectionResult.ExplanationSource.GEMINI_API
    assert "Duck-typed client" in result.ai_narrative

