"""
backend/tests/test_api_endpoints.py — Task 4: REST API Endpoints, RBAC Guards,
Excel Ingest/Export, and Public Portal Shield Tests.

Tests:
  1. POST /api/auth/login/
     - Super Admin, Surveyor, and Viewer authentication
     - Returns JWT access/refresh + role + name + rt_number
     - Invalid credentials return 401
  2. GET /api/criteria/ & PUT /api/criteria/batch-update/
     - List criteria and subcriteria
     - Super Admin can update weights summing to 1.00
     - Rejects weight sum != 1.00 (HTTP 400)
     - Surveyor and Viewer blocked with 403 Forbidden
  3. GET /api/batches/ & POST /api/batches/
     - List selection batches
     - Super Admin can create batches
     - Surveyor and Viewer blocked with 403 Forbidden
  4. POST /api/citizens/ & POST /api/citizens/import-excel/
     - Surveyor RT-003 can only create citizen with rt='003' (rt='005' blocked 403)
     - Super Admin can create citizen in any RT
     - Excel import: per-row error reporting, surveyor RT scoping, nik_hash deduplication
  5. Selection Workflow & RBAC:
     - mark-rt-submitted
     - calculate (Super Admin only, transitions to Calculated)
     - results (Surveyor scoped to their RT, Super Admin sees all)
     - generate-xai (Super Admin only, HTTP 202) & xai-progress
     - approve (Viewer / Lurah only, requires status == 'Narrated')
     - publish (Super Admin only, requires status == 'Approved')
     - export-excel (recapitulation .xlsx download)
  6. Public Portal Shield (/api/public/check-status/):
     - Batch unpublished -> HTTP 404
     - CAPTCHA failure -> HTTP 403 without incrementing NIK lockout counter
     - 5 req/min/IP rate limit -> HTTP 429
     - 5 consecutive wrong kk_last4 -> NIK locked out for 15 minutes (HTTP 429)
     - Successful query -> HTTP 200 with masked data, explanation, chart_data, and signed download_token
"""

from __future__ import annotations

import io
from decimal import Decimal
import openpyxl
import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from core.crypto import sign_pdf_download_token, verify_pdf_download_token
from core.models import (
    AuditLog,
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
from core.services.xai_explainer import generate_xai_for_evaluation


@pytest.fixture(autouse=True)
def _seed_db(db):
    cache.clear()
    call_command("seed_initial_data", verbosity=0)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def superadmin_user():
    return StaffUser.objects.get(username="kasi_kesos")


@pytest.fixture
def surveyor_rt003_user():
    return StaffUser.objects.get(username="ketua_rt003")


@pytest.fixture
def surveyor_rt005_user():
    return StaffUser.objects.get(username="ketua_rt005")


@pytest.fixture
def viewer_user():
    return StaffUser.objects.get(username="lurah_jurangmangu")


def _auth_client(user: StaffUser) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _create_sample_excel(rows_data: list[dict]) -> io.BytesIO:
    """Helper to create in-memory .xlsx file for import testing."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Usulan KPM"
    headers = [
        "NIK",
        "Nama Lengkap",
        "4 Digit KK",
        "RT",
        "RW",
        "Alamat",
        "Status Kelayakan",
        "Alasan TMS",
        "Tanggungan Riil",
        "C1 (Pendapatan)",
        "C2 (Tanggungan)",
        "C3 (Kondisi Rumah)",
        "C4 (Aset)",
    ]
    ws.append(headers)
    for row in rows_data:
        ws.append([
            row.get("nik", "3674031208850001"),
            row.get("name", "Budi Santoso"),
            row.get("kk_last4", "1234"),
            row.get("rt", "003"),
            row.get("rw", "001"),
            row.get("address", "Jl. Flamboyan 1"),
            row.get("status", "ELIGIBLE"),
            row.get("tms_reason", ""),
            row.get("real_dependents", 3),
            row.get("c1", 1),
            row.get("c2", 4),
            row.get("c3", 2),
            row.get("c4", 1),
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    buf.name = "import_test.xlsx"
    return buf


@pytest.fixture
def active_batch():
    period = Period.objects.filter(is_active=True).first()
    if not period:
        period = Period.objects.create(name="Tahap I 2026", year=2026, semester=1, is_active=True)
    batch, _ = SelectionBatch.objects.get_or_create(
        period=period,
        batch_number=1,
        defaults={"quota": 2, "status": "Draft"},
    )
    return batch


# ---------------------------------------------------------------------------
# 1. Staff Authentication
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_staff_login_success_and_jwt_payload(api_client, superadmin_user, surveyor_rt003_user):
    # Test Super Admin login
    res = api_client.post("/api/auth/login/", {
        "username": "kasi_kesos",
        "password": "BansosAdmin2026!",
    }, format="json")
    assert res.status_code == 200
    assert "access" in res.data
    assert "refresh" in res.data
    assert res.data["role"] == "SUPER_ADMIN"
    assert "Budi Hartono" in res.data["name"]
    assert res.data["rt_number"] == ""

    # Test Surveyor RT 003 login
    res_surveyor = api_client.post("/api/auth/login/", {
        "username": "ketua_rt003",
        "password": "SurveyRT003!",
    }, format="json")
    assert res_surveyor.status_code == 200
    assert res_surveyor.data["role"] == "SURVEYOR"
    assert res_surveyor.data["rt_number"] == "003"


@pytest.mark.django_db
def test_staff_login_invalid_credentials(api_client):
    res = api_client.post("/api/auth/login/", {
        "username": "kasi_kesos",
        "password": "WrongPassword123!",
    }, format="json")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# 2. Criteria Management & RBAC
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_criteria_list_and_batch_update_rbac(superadmin_user, surveyor_rt003_user, viewer_user):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)
    viewer_client = _auth_client(viewer_user)

    # 1. All authenticated roles can list criteria
    res = admin_client.get("/api/criteria/")
    assert res.status_code == 200
    assert len(res.data) == 4

    res_viewer = viewer_client.get("/api/criteria/")
    assert res_viewer.status_code == 200

    # 2. Surveyor & Viewer CANNOT update criteria weights (403 Forbidden)
    c_list = [{"id": c.id, "weight": 0.25, "criterion_type": c.criterion_type} for c in Criteria.objects.all()]
    assert surveyor_client.put("/api/criteria/batch-update/", {"criteria": c_list}, format="json").status_code == 403
    assert viewer_client.put("/api/criteria/batch-update/", {"criteria": c_list}, format="json").status_code == 403

    # 3. Super Admin can update criteria weights when sum == 1.00
    res_admin = admin_client.put("/api/criteria/batch-update/", {"criteria": c_list}, format="json")
    assert res_admin.status_code == 200
    assert "berhasil diperbarui" in res_admin.data["message"]

    # 4. Super Admin rejected when sum != 1.00 (400 Bad Request)
    invalid_list = [{"id": c.id, "weight": 0.20, "criterion_type": c.criterion_type} for c in Criteria.objects.all()]
    res_bad = admin_client.put("/api/criteria/batch-update/", {"criteria": invalid_list}, format="json")
    assert res_bad.status_code == 400
    assert "harus persis bernilai 1.00" in res_bad.data["error"]


# ---------------------------------------------------------------------------
# 3. Batch Management & RBAC
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_batches_list_and_create_rbac(superadmin_user, surveyor_rt003_user, active_batch):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)

    # All authenticated staff can list batches
    res = surveyor_client.get("/api/batches/")
    assert res.status_code == 200
    assert len(res.data) >= 1

    # Surveyor cannot create a batch (403)
    res_forbid = surveyor_client.post("/api/batches/", {
        "period_id": active_batch.period.id,
        "batch_number": 2,
        "quota": 10,
    }, format="json")
    assert res_forbid.status_code == 403

    # Super Admin can create a batch (201)
    res_create = admin_client.post("/api/batches/", {
        "period_id": active_batch.period.id,
        "batch_number": 2,
        "quota": 10,
    }, format="json")
    assert res_create.status_code == 201
    assert res_create.data["batch_number"] == 2


# ---------------------------------------------------------------------------
# 4. Citizen Creation & Excel Ingest RBAC
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_single_create_surveyor_rt_scope(superadmin_user, surveyor_rt003_user, active_batch):
    surveyor_client = _auth_client(surveyor_rt003_user)
    admin_client = _auth_client(superadmin_user)

    payload_rt003 = {
        "batch_id": active_batch.id,
        "nik": "3674031208850001",
        "kk_last4": "1234",
        "full_name": "Warga RT 003",
        "address": "Jl. Melati 1",
        "rt": "003",
        "rw": "001",
        "real_dependents_count": 3,
        "eligibility_status": "ELIGIBLE",
        "criteria_values": {"C1": 1, "C2": 4, "C3": 2, "C4": 1},
    }

    # Surveyor RT 003 can create citizen in RT 003
    res_ok = surveyor_client.post("/api/citizens/", payload_rt003, format="json")
    assert res_ok.status_code == 201

    # Surveyor RT 003 CANNOT create citizen in RT 005 (403 Forbidden)
    payload_rt005 = dict(payload_rt003)
    payload_rt005["nik"] = "3674031208850005"
    payload_rt005["rt"] = "005"
    res_err = surveyor_client.post("/api/citizens/", payload_rt005, format="json")
    assert res_err.status_code == 403
    assert "hanya berwenang mengelola data wilayah RT 003" in res_err.data["error"]

    # Super Admin can create citizen in RT 005
    res_admin = admin_client.post("/api/citizens/", payload_rt005, format="json")
    assert res_admin.status_code == 201


@pytest.mark.django_db
def test_citizens_import_excel_deduplication_and_surveyor_scoping(superadmin_user, surveyor_rt003_user, active_batch):
    surveyor_client = _auth_client(surveyor_rt003_user)
    admin_client = _auth_client(superadmin_user)

    # 1. Surveyor RT 003 imports file containing rows for RT 003 and RT 005
    test_rows = [
        {"nik": "3674031208850011", "name": "Warga RT3-A", "rt": "003"},
        {"nik": "3674031208850012", "name": "Warga RT3-B", "rt": "003"},
        {"nik": "3674031208850013", "name": "Warga RT5-A", "rt": "005"},  # Out of scope!
    ]
    excel_file = _create_sample_excel(test_rows)
    res_surveyor = surveyor_client.post(
        "/api/citizens/import-excel/",
        {"file": excel_file, "batch_id": active_batch.id},
        format="multipart",
    )
    assert res_surveyor.status_code == 200
    assert res_surveyor.data["total_imported"] == 2
    assert len(res_surveyor.data["errors"]) == 1
    assert "RT 005 berada di luar wilayah wewenang" in res_surveyor.data["errors"][0]["error"]

    # 2. Re-importing same NIK deduplicates (skips or updates)
    excel_dup = _create_sample_excel([test_rows[0]])
    res_dup = surveyor_client.post(
        "/api/citizens/import-excel/",
        {"file": excel_dup, "batch_id": active_batch.id},
        format="multipart",
    )
    assert res_dup.status_code == 200
    assert res_dup.data["duplicates_skipped"] == 1


# ---------------------------------------------------------------------------
# 5. Selection Workflow & RBAC (Calculate, Results, XAI, Approve, Publish)
# ---------------------------------------------------------------------------

@pytest.fixture
def populated_batch(active_batch, surveyor_rt003_user):
    # Populate batch with 3 eligible candidates and 1 TMS candidate
    client = _auth_client(surveyor_rt003_user)
    rows = [
        {"nik": "3674031208850021", "name": "Calon Lolos 1", "rt": "003", "c1": 1, "c2": 5, "c3": 1, "c4": 1, "status": "ELIGIBLE"},
        {"nik": "3674031208850022", "name": "Calon Lolos 2", "rt": "003", "c1": 2, "c2": 4, "c3": 2, "c4": 2, "status": "ELIGIBLE"},
        {"nik": "3674031208850023", "name": "Calon Kalah",   "rt": "003", "c1": 4, "c2": 1, "c3": 4, "c4": 4, "status": "ELIGIBLE"},
        {"nik": "3674031208850024", "name": "Calon TMS ASN", "rt": "003", "c1": 1, "c2": 1, "c3": 1, "c4": 1, "status": "DISQUALIFIED", "tms_reason": "ASN"},
    ]
    excel_file = _create_sample_excel(rows)
    res = client.post(
        "/api/citizens/import-excel/",
        {"file": excel_file, "batch_id": active_batch.id},
        format="multipart",
    )
    assert res.status_code == 200
    active_batch.status = "Collecting"
    active_batch.save()
    return active_batch


@pytest.mark.django_db
def test_selection_calculate_and_results_rbac(superadmin_user, surveyor_rt003_user, viewer_user, populated_batch):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)
    viewer_client = _auth_client(viewer_user)

    # 1. Surveyor & Viewer cannot trigger calculation (403)
    assert surveyor_client.post(f"/api/selection/{populated_batch.id}/calculate/").status_code == 403
    assert viewer_client.post(f"/api/selection/{populated_batch.id}/calculate/").status_code == 403

    # 2. Super Admin can trigger calculation
    res_calc = admin_client.post(f"/api/selection/{populated_batch.id}/calculate/")
    assert res_calc.status_code == 200
    assert res_calc.data["status"] == "Calculated"
    assert res_calc.data["eligible_candidates"] == 3
    assert res_calc.data["disqualified_tms"] == 1

    # 3. Results endpoint accessible to staff
    res_res = admin_client.get(f"/api/selection/{populated_batch.id}/results/")
    assert res_res.status_code == 200
    assert len(res_res.data["results"]) == 4

    # Filter results by status
    res_filtered = admin_client.get(f"/api/selection/{populated_batch.id}/results/?status=LOLOS")
    assert res_filtered.status_code == 200
    assert len(res_filtered.data["results"]) == 2


@pytest.mark.django_db
def test_selection_generate_xai_and_progress(superadmin_user, surveyor_rt003_user, populated_batch):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)

    # Calculate first
    calculate_batch_saw(populated_batch.id)

    # Surveyor cannot trigger XAI (403)
    assert surveyor_client.post(f"/api/selection/{populated_batch.id}/generate-xai/").status_code == 403

    # Super Admin triggers XAI -> 202 Accepted
    res_xai = admin_client.post(f"/api/selection/{populated_batch.id}/generate-xai/")
    assert res_xai.status_code == 202
    assert "job_id" in res_xai.data

    # Check progress endpoint
    res_prog = admin_client.get(f"/api/selection/{populated_batch.id}/xai-progress/")
    assert res_prog.status_code == 200
    assert "status" in res_prog.data
    assert "progress_percent" in res_prog.data


@pytest.mark.django_db
def test_selection_approval_and_publish_state_machine_rbac(
    superadmin_user, surveyor_rt003_user, viewer_user, populated_batch
):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)
    viewer_client = _auth_client(viewer_user)

    calculate_batch_saw(populated_batch.id)

    # 1. Try to approve when batch is still Calculated (not yet Narrated) -> 400 Bad Request
    assert viewer_client.patch(f"/api/selection/{populated_batch.id}/approve/").status_code == 400

    # Simulate completion of narratives
    for eval_obj in populated_batch.evaluations.filter(eligibility_status="ELIGIBLE"):
        generate_xai_for_evaluation(eval_obj.id, backoff_seconds=0)
    populated_batch.status = "Narrated"
    populated_batch.save()

    # 2. Super Admin or Surveyor CANNOT approve (403 Forbidden; Lurah/Viewer only)
    assert admin_client.patch(f"/api/selection/{populated_batch.id}/approve/").status_code == 403
    assert surveyor_client.patch(f"/api/selection/{populated_batch.id}/approve/").status_code == 403

    # 3. Viewer approves batch -> transitions to Approved
    res_app = viewer_client.patch(f"/api/selection/{populated_batch.id}/approve/")
    assert res_app.status_code == 200
    populated_batch.refresh_from_db()
    assert populated_batch.status == "Approved"

    # 4. Viewer or Surveyor CANNOT publish (403 Forbidden; Super Admin only)
    assert viewer_client.patch(f"/api/selection/{populated_batch.id}/publish/").status_code == 403
    assert surveyor_client.patch(f"/api/selection/{populated_batch.id}/publish/").status_code == 403

    # 5. Super Admin publishes batch -> transitions to Published
    res_pub = admin_client.patch(f"/api/selection/{populated_batch.id}/publish/")
    assert res_pub.status_code == 200
    populated_batch.refresh_from_db()
    assert populated_batch.status == "Published"


@pytest.mark.django_db
def test_export_batch_results_excel(superadmin_user, surveyor_rt003_user, populated_batch):
    admin_client = _auth_client(superadmin_user)
    surveyor_client = _auth_client(surveyor_rt003_user)

    calculate_batch_saw(populated_batch.id)

    # Surveyor cannot export full recapitulation (403)
    assert surveyor_client.get(f"/api/selection/{populated_batch.id}/export-excel/").status_code == 403

    # Super Admin can export
    res = admin_client.get(f"/api/selection/{populated_batch.id}/export-excel/")
    assert res.status_code == 200
    assert res["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(res.content) > 0


# ---------------------------------------------------------------------------
# 6. Public Portal Shield (/api/public/check-status/)
# ---------------------------------------------------------------------------

@pytest.fixture
def published_batch_with_results(populated_batch):
    calculate_batch_saw(populated_batch.id)
    for eval_obj in populated_batch.evaluations.filter(eligibility_status="ELIGIBLE"):
        generate_xai_for_evaluation(eval_obj.id, backoff_seconds=0)
    populated_batch.status = "Published"
    populated_batch.save()
    return populated_batch


@pytest.mark.django_db
def test_public_check_status_blocks_unpublished_batch(api_client, populated_batch):
    calculate_batch_saw(populated_batch.id)
    populated_batch.status = "Narrated"
    populated_batch.save()

    # Querying unpublished batch returns 404
    res = api_client.post("/api/public/check-status/", {
        "nik": "3674031208850021",
        "kk_last4": "1234",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="192.168.1.1")
    assert res.status_code == 404
    assert res.data["found"] is False


@pytest.mark.django_db
def test_public_check_status_captcha_fail_does_not_increment_lockout(api_client, published_batch_with_results):
    nik = "3674031208850021"

    # Send 10 invalid CAPTCHA requests
    for i in range(10):
        res = api_client.post("/api/public/check-status/", {
            "nik": nik,
            "kk_last4": "9999",  # Wrong KK too
            "captcha_token": "invalid_token",
        }, format="json", REMOTE_ADDR=f"192.168.1.{i}")
        assert res.status_code == 403
        assert "CAPTCHA" in res.data["error"]

    # Now send with valid CAPTCHA but wrong KK -> must return 404, NOT 429 lockout!
    res_valid_cap = api_client.post("/api/public/check-status/", {
        "nik": nik,
        "kk_last4": "9999",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="192.168.2.1")
    assert res_valid_cap.status_code == 404


@pytest.mark.django_db
def test_public_check_status_ip_rate_limit(api_client, published_batch_with_results):
    ip = "10.10.10.10"
    for _ in range(5):
        res = api_client.post("/api/public/check-status/", {
            "nik": "3674031208850021",
            "kk_last4": "1234",
            "captcha_token": "valid_test_token",
        }, format="json", REMOTE_ADDR=ip)
        assert res.status_code == 200

    # 6th request from same IP within 1 min -> 429
    res_blocked = api_client.post("/api/public/check-status/", {
        "nik": "3674031208850021",
        "kk_last4": "1234",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR=ip)
    assert res_blocked.status_code == 429
    assert "Terlalu banyak permintaan" in res_blocked.data["error"]


@pytest.mark.django_db
def test_public_check_status_nik_lockout_across_ips(api_client, published_batch_with_results):
    nik = "3674031208850021"

    # 5 wrong KK attempts with valid CAPTCHA across 5 different IPs
    for i in range(5):
        res = api_client.post("/api/public/check-status/", {
            "nik": nik,
            "kk_last4": "0000",
            "captcha_token": "valid_test_token",
        }, format="json", REMOTE_ADDR=f"10.20.1.{i}")
        assert res.status_code == 404

    # 6th attempt from a brand new IP -> 429 NIK Lockout
    res_locked = api_client.post("/api/public/check-status/", {
        "nik": nik,
        "kk_last4": "1234",  # Even with correct KK now!
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="10.20.2.99")
    assert res_locked.status_code == 429
    assert "dikunci sementara selama 15 menit" in res_locked.data["error"]


@pytest.mark.django_db
def test_public_check_status_success_payload_structure(api_client, published_batch_with_results):
    res = api_client.post("/api/public/check-status/", {
        "nik": "3674031208850021",
        "kk_last4": "1234",
        "captcha_token": "valid_test_token",
    }, format="json", REMOTE_ADDR="172.16.0.1")

    assert res.status_code == 200
    assert res.data["found"] is True
    assert "period_name" in res.data
    assert res.data["applicant"]["nik_masked"] == "367403******0021"
    assert "Calon" in res.data["applicant"]["name_masked"]
    assert res.data["applicant"]["rt"] == "003"
    assert res.data["result"]["status"] == "LOLOS"
    assert "explanation" in res.data["result"]
    assert "chart_data" in res.data["result"]
    assert len(res.data["result"]["chart_data"]) == 4

    # Check signed download token
    token = res.data.get("download_token")
    assert token is not None
    eval_id = verify_pdf_download_token(token)
    assert eval_id is not None
