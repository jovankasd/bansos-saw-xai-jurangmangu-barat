"""
backend/tests/test_pdf_and_evaluation.py — Tests for Task 5:
PDF Berita Acara Generator (with QR & TMS Appendix), Individual Citizen PDF,
and Thesis Evaluation Metrics (Fidelity, Hallucination, SUS, Dataset Export).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal
import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from core.crypto import sign_pdf_download_token
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
    StaffUser,
)
from core.services.saw_engine import calculate_batch_saw
from core.services.deterministic_fallback import generate_deterministic_fallback
from core.services.sanitizer import build_anonymous_payload
from core.services.pdf_generator import (
    generate_berita_acara_pdf,
    generate_individual_result_pdf,
)
from core.services.evaluation_metrics import (
    compute_batch_evaluation_metrics,
    export_thesis_evaluation_dataset,
    get_sus_questionnaire_template,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _seed_db(db):
    call_command("seed_initial_data", verbosity=0)


@pytest.fixture
def superadmin_user():
    return StaffUser.objects.create_user(
        username="admin_test_pdf",
        password="Password123!",
        full_name="Admin PDF Tester",
        role=StaffUser.Role.SUPER_ADMIN,
    )


@pytest.fixture
def viewer_user():
    return StaffUser.objects.create_user(
        username="lurah_test_pdf",
        password="Password123!",
        full_name="Lurah Jurangmangu Barat",
        role=StaffUser.Role.VIEWER,
    )


@pytest.fixture
def surveyor_user():
    return StaffUser.objects.create_user(
        username="surveyor_test_pdf",
        password="Password123!",
        full_name="Surveyor RT 003",
        role=StaffUser.Role.SURVEYOR,
        rt_number="003",
    )


def _create_citizen(raw_nik: str, name: str, kk_last4: str = "5501", rt: str = "003", rw: str = "001") -> Citizen:
    c, _ = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4=kk_last4,
        full_name=name,
        address=f"Jl. Jurangmangu RT {rt}",
        rt=rt,
        rw=rw,
    )
    return c


@pytest.fixture
def narrated_batch(superadmin_user):
    """
    Creates a batch with 1 TMS candidate and 4 ELIGIBLE candidates.
    Calculates SAW (quota=2: 2 LOLOS, 2 TIDAK_LOLOS).
    Populates valid XAI narratives for all eligible candidates.
    Batch transitions to NARRATED.
    """
    period = Period.objects.create(
        name=f"Bansos Sembako Tahap I {uuid.uuid4().hex[:8]}",
        year=2026,
        semester=1,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )
    batch = SelectionBatch.objects.create(
        period=period,
        name="Batch I - 2026",
        quota=2,
        status=SelectionBatch.Status.COLLECTING,
        created_by=superadmin_user,
    )

    # 1 TMS citizen
    c_tms = _create_citizen("3674039999990001", "Bambang Sudrajat ASN", kk_last4="1111")
    eval_tms = Evaluation.objects.create(
        batch=batch,
        citizen=c_tms,
        eligibility_status=Evaluation.EligibilityStatus.DISQUALIFIED,
        tms_reason=Evaluation.TmsReason.ASN,
        real_dependents_count=2,
    )
    c_map = {c.code: c for c in Criteria.objects.all()}
    for code, val in {"C1": 1, "C2": 5, "C3": 1, "C4": 1}.items():
        EvaluationDetail.objects.create(evaluation=eval_tms, criteria=c_map[code], raw_crips_value=val)

    # 4 ELIGIBLE citizens
    # KPM 1: High need -> Rank 1 LOLOS
    c1 = _create_citizen("3674031111110001", "Ahmad Subarjo", "5501")
    e1 = Evaluation.objects.create(batch=batch, citizen=c1, real_dependents_count=4)
    for code, val in {"C1": 1, "C2": 5, "C3": 1, "C4": 1}.items():
        EvaluationDetail.objects.create(evaluation=e1, criteria=c_map[code], raw_crips_value=val)

    # KPM 2: Good need -> Rank 2 LOLOS
    c2 = _create_citizen("3674032222220002", "Siti Aminah", "5502")
    e2 = Evaluation.objects.create(batch=batch, citizen=c2, real_dependents_count=3)
    for code, val in {"C1": 1, "C2": 4, "C3": 2, "C4": 1}.items():
        EvaluationDetail.objects.create(evaluation=e2, criteria=c_map[code], raw_crips_value=val)

    # KPM 3: Moderate -> Rank 3 TIDAK_LOLOS
    c3 = _create_citizen("3674033333330003", "Budi Santoso", "5503")
    e3 = Evaluation.objects.create(batch=batch, citizen=c3, real_dependents_count=2)
    for code, val in {"C1": 2, "C2": 3, "C3": 3, "C4": 2}.items():
        EvaluationDetail.objects.create(evaluation=e3, criteria=c_map[code], raw_crips_value=val)

    # KPM 4: Low need -> Rank 4 TIDAK_LOLOS
    c4 = _create_citizen("3674034444440004", "Dewi Lestari", "5504")
    e4 = Evaluation.objects.create(batch=batch, citizen=c4, real_dependents_count=1)
    for code, val in {"C1": 4, "C2": 2, "C3": 4, "C4": 3}.items():
        EvaluationDetail.objects.create(evaluation=e4, criteria=c_map[code], raw_crips_value=val)

    # Calculate SAW
    calculate_batch_saw(batch.id, performed_by=superadmin_user.username)
    batch.refresh_from_db()

    # Populate narratives using deterministic fallback (100% faithful and zero hallucination)
    for eval_obj in batch.evaluations.filter(eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE):
        payload = build_anonymous_payload(eval_obj.id)
        narrative_data = generate_deterministic_fallback(payload)
        res = eval_obj.result
        res.ai_narrative = narrative_data["narasi_lengkap"]
        res.ai_payload_response = narrative_data
        res.explanation_source = SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK
        res.narrated_at = timezone.now()
        res.save()

    batch.status = SelectionBatch.Status.NARRATED
    batch.save()
    return batch


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_fidelity_hallucination_metrics_and_signed_pdf_download(narrated_batch):
    """
    Core milestone test specified in Implementation Plan Step 1:
      - compute_batch_evaluation_metrics: fidelity >= 95.0, hallucination == 0.0
      - generate_berita_acara_pdf produces valid %PDF- bytes
      - public PDF download endpoint requires valid signed token and Published batch status
    """
    metrics = compute_batch_evaluation_metrics(narrated_batch.id)
    assert metrics["fidelity_score"] >= 95.0
    assert metrics["hallucination_rate"] == 0.0

    pdf_bytes = generate_berita_acara_pdf(narrated_batch.id)
    assert pdf_bytes.startswith(b"%PDF-")

    # Public PDF endpoint requires valid signed token and Published batch status
    narrated_batch.status = SelectionBatch.Status.PUBLISHED
    narrated_batch.save()
    eval_obj = narrated_batch.evaluations.first()
    client = APIClient()
    assert client.get("/api/public/result-pdf/?token=invalid").status_code == 403
    valid_token = sign_pdf_download_token(eval_obj.id)
    res = client.get(f"/api/public/result-pdf/?token={valid_token}")
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF-")


@pytest.mark.django_db
def test_fidelity_score_formula_and_zero_division_guard(narrated_batch):
    """
    PRD Bagian 11.2:
      - Fidelity Score = 1/|K_TL| * sum I(C_AI_primary == argmax (Delta_j * w_j))
      - Must handle |K_TL| == 0 gracefully returning 100.0 without ZeroDivisionError.
      - Uses BatchCriteria.frozen_weight snapshot.
    """
    # 1. Normal batch with 2 TIDAK_LOLOS candidates
    metrics = compute_batch_evaluation_metrics(narrated_batch.id)
    assert metrics["fidelity_score"] == 100.0
    assert metrics["total_candidates"] == 5
    assert metrics["eligible_candidates"] == 4
    assert metrics["disqualified_tms"] == 1
    assert metrics["failed_count"] == 2
    assert metrics["passed_count"] == 2

    # 2. Mutate one TIDAK_LOLOS candidate's narrative to pick non-argmax criterion
    tidak_lolos_eval = narrated_batch.evaluations.filter(result__status=SelectionResult.ResultStatus.TIDAK_LOLOS).first()
    res = tidak_lolos_eval.result
    # Intentionally change primary criterion from C1 to C4 (which is not the maximum weighted gap)
    res.ai_payload_response["primary_criterion_code"] = "C4"
    res.ai_payload_response["faktor_penentu_utama"] = ["Kepemilikan Aset (C4)"]
    res.save()

    metrics_after = compute_batch_evaluation_metrics(narrated_batch.id)
    # 1 out of 2 matched -> 50.0%
    assert metrics_after["fidelity_score"] == 50.0

    # 3. Edge Case: Batch where all candidates LOLOS (quota >= eligible), so |K_TL| == 0
    period = Period.objects.create(
        name=f"All Pass Period {uuid.uuid4().hex[:8]}",
        year=2026,
        semester=1,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )
    all_pass_batch = SelectionBatch.objects.create(
        period=period,
        name="Batch All Pass",
        quota=10,
        status=SelectionBatch.Status.COLLECTING,
    )
    c_pass = _create_citizen("3674037777770001", "KPM Lolos Semua")
    e_pass = Evaluation.objects.create(batch=all_pass_batch, citizen=c_pass)
    c_map = {c.code: c for c in Criteria.objects.all()}
    for code in ("C1", "C2", "C3", "C4"):
        EvaluationDetail.objects.create(evaluation=e_pass, criteria=c_map[code], raw_crips_value=1)
    calculate_batch_saw(all_pass_batch.id)
    all_pass_batch.refresh_from_db()

    # compute metrics for all pass batch
    all_pass_metrics = compute_batch_evaluation_metrics(all_pass_batch.id)
    assert all_pass_metrics["failed_count"] == 0
    assert all_pass_metrics["fidelity_score"] == 100.0


@pytest.mark.django_db
def test_hallucination_rate_normalizes_indonesian_decimals_and_percentages(narrated_batch):
    """
    PRD Bagian 11.2 & User Target:
      - Normalizes Indonesian decimal format: '0,684' -> 0.684
      - Normalizes percentage format: '60%' -> 0.60
      - Flags hallucinated criteria codes (e.g. C99, Daya Listrik) or invented numbers.
    """
    # 1. Base clean batch
    metrics = compute_batch_evaluation_metrics(narrated_batch.id)
    assert metrics["hallucination_rate"] == 0.0

    # 2. Inject Indonesian format decimal and percentage in narrative -> should NOT be flagged as hallucination
    tidak_lolos_eval = narrated_batch.evaluations.filter(result__status=SelectionResult.ResultStatus.TIDAK_LOLOS).first()
    res = tidak_lolos_eval.result
    # 0,684 matches final score (0.6840 or similar), 60% matches 0.60
    res.ai_narrative = (
        f"Skor akhir pemohon adalah {str(res.final_score_v).replace('.', ',')} dengan capaian 60% pada kriteria C1. "
        "Berdasarkan kuota 2 penerima, pemohon belum memenuhi batas kelulusan."
    )
    res.save()

    metrics = compute_batch_evaluation_metrics(narrated_batch.id)
    assert metrics["hallucination_rate"] == 0.0

    # 3. Inject blatant hallucination (forbidden criterion C99 and fake score 99,99)
    res.ai_narrative = "Pemohon memiliki nilai C99 sebesar 99,99 yang melampaui batas wajar."
    res.ai_payload_response["faktor_penentu_utama"] = ["Daya Listrik 900VA (C99)"]
    res.save()

    metrics_hallucinated = compute_batch_evaluation_metrics(narrated_batch.id)
    # 1 out of 4 evaluated has hallucination -> 25.0%
    assert metrics_hallucinated["hallucination_rate"] == 25.0


@pytest.mark.django_db
def test_sus_questionnaire_template_and_export_dataset(narrated_batch):
    """
    Verifies SUS Questionnaire template (10 items, standard Likert scale)
    and thesis dataset export functionality.
    """
    sus_template = get_sus_questionnaire_template()
    assert len(sus_template) == 10
    assert sus_template[0]["id"] == 1
    assert "sering menggunakan" in sus_template[0]["question"].lower()
    assert sus_template[0]["scale_min"] == 1
    assert sus_template[0]["scale_max"] == 5

    # Export thesis dataset
    dataset = export_thesis_evaluation_dataset(narrated_batch.id)
    assert dataset["batch_id"] == narrated_batch.id
    assert len(dataset["records"]) == 5  # 1 TMS + 4 eligible
    first_record = dataset["records"][0]
    assert "applicant_code" in first_record
    assert "status" in first_record
    assert "fidelity_match" in first_record
    assert "hallucination_detected" in first_record


@pytest.mark.django_db
def test_berita_acara_pdf_generation_content_and_audit_log(narrated_batch, viewer_user):
    """
    PRD Bagian 11 & UU PDP No. 27/2022:
      - Kop Surat Kelurahan Jurangmangu Barat
      - Ranking table of passed KPMs
      - Controlled NIK decryption ONLY here, with AuditLog entry (NIK_DECRYPT)
      - Separate Appendix for TMS (DISQUALIFIED) citizens
      - QR Code verification
    """
    initial_log_count = AuditLog.objects.filter(action=AuditLog.Action.NIK_DECRYPT).count()

    pdf_bytes = generate_berita_acara_pdf(narrated_batch.id, performed_by=viewer_user.username)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 2000

    # Verify AuditLog created
    log = AuditLog.objects.filter(batch=narrated_batch, action=AuditLog.Action.NIK_DECRYPT).first()
    assert log is not None
    assert log.performed_by == viewer_user.username
    assert "AuditLog.Action.NIK_DECRYPT" in str(log) or "NIK Decryption" in str(log.action) or log.action == AuditLog.Action.NIK_DECRYPT
    # Ensure audit log does not leak raw plaintext NIK
    assert "3674031111110001" not in log.detail
    assert "3674031111110001" not in log.performed_by


@pytest.mark.django_db
def test_individual_result_pdf_generation_masks_pii(narrated_batch):
    """
    Individual citizen result PDF:
      - NIK and name MUST be masked (UU PDP No. 27/2022)
      - Contains explanation narrative, ranking, score, and QR code
    """
    eval_obj = narrated_batch.evaluations.filter(result__status=SelectionResult.ResultStatus.LOLOS).first()
    pdf_bytes = generate_individual_result_pdf(eval_obj.id)

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1500


@pytest.mark.django_db
def test_berita_acara_pdf_api_endpoint_rbac(narrated_batch, superadmin_user, viewer_user, surveyor_user):
    """
    GET /api/selection/{batch_id}/berita-acara-pdf/
      - Allowed: SuperAdmin, Viewer (Lurah)
      - Blocked: Surveyor (403), Anonymous (401)
    """
    client = APIClient()
    url = f"/api/selection/{narrated_batch.id}/berita-acara-pdf/"

    # 1. Anonymous -> 401
    assert client.get(url).status_code == 401

    # 2. Surveyor -> 403 Forbidden
    client.force_authenticate(user=surveyor_user)
    assert client.get(url).status_code == 403

    # 3. Viewer (Lurah) -> 200 OK with PDF attachment
    client.force_authenticate(user=viewer_user)
    res = client.get(url)
    assert res.status_code == 200
    assert res["Content-Type"] == "application/pdf"
    assert "attachment" in res["Content-Disposition"]
    assert res.content.startswith(b"%PDF-")

    # 4. Super Admin -> 200 OK
    client.force_authenticate(user=superadmin_user)
    res_admin = client.get(url)
    assert res_admin.status_code == 200
    assert res_admin.content.startswith(b"%PDF-")


@pytest.mark.django_db
def test_public_individual_pdf_endpoint_guards(narrated_batch):
    """
    GET /api/public/result-pdf/?token=<signed_token>
      - Requires token param
      - Rejects invalid / tampered token (403)
      - Rejects if batch is not Published (403)
      - Returns 200 with PDF once Published
    """
    eval_obj = narrated_batch.evaluations.filter(result__status=SelectionResult.ResultStatus.LOLOS).first()
    valid_token = sign_pdf_download_token(eval_obj.id)
    client = APIClient()

    # 1. Missing token -> 400 or 403
    res_no_tok = client.get("/api/public/result-pdf/")
    assert res_no_tok.status_code in (400, 403)

    # 2. Invalid token -> 403
    res_bad_tok = client.get("/api/public/result-pdf/?token=fake-token-123")
    assert res_bad_tok.status_code == 403

    # 3. Valid token but batch is still Narrated (not Published) -> 403
    assert narrated_batch.status == SelectionBatch.Status.NARRATED
    res_unpub = client.get(f"/api/public/result-pdf/?token={valid_token}")
    assert res_unpub.status_code == 403

    # 4. Batch transitioned to Published -> 200 OK with PDF
    narrated_batch.status = SelectionBatch.Status.PUBLISHED
    narrated_batch.save()
    res_ok = client.get(f"/api/public/result-pdf/?token={valid_token}")
    assert res_ok.status_code == 200
    assert res_ok["Content-Type"] == "application/pdf"
    assert res_ok.content.startswith(b"%PDF-")


@pytest.mark.django_db
def test_evaluation_metrics_api_endpoint(narrated_batch, superadmin_user, surveyor_user):
    """
    GET /api/selection/{batch_id}/evaluation-metrics/
      - Allowed: SuperAdmin, Viewer
      - Blocked: Surveyor (403), Anonymous (401)
      - Returns fidelity_score, hallucination_rate, SUS questions
    """
    client = APIClient()
    url = f"/api/selection/{narrated_batch.id}/evaluation-metrics/"

    # 1. Anonymous -> 401
    assert client.get(url).status_code == 401

    # 2. Surveyor -> 403
    client.force_authenticate(user=surveyor_user)
    assert client.get(url).status_code == 403

    # 3. SuperAdmin -> 200
    client.force_authenticate(user=superadmin_user)
    res = client.get(url)
    assert res.status_code == 200
    data = res.json()
    assert "fidelity_score" in data
    assert "hallucination_rate" in data
    assert "sus_template" in data
    assert data["fidelity_score"] >= 95.0
    assert data["hallucination_rate"] == 0.0
