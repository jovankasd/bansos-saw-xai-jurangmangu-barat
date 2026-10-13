"""
Task 1 — TDD: Crypto Service (UU PDP No. 27/2022) & Database Models.

Tests:
  - AES-256-GCM roundtrip (32-byte key enforcement)
  - HMAC-SHA256 nik_hash determinism
  - No plaintext NIK at rest (nik_encrypted must not contain raw NIK)
  - mask_nik -> "367403******0002"
  - mask_name multi-word -> "Ahmad S******", single-word -> "Su*****"
  - sign_pdf_download_token / verify_pdf_download_token roundtrip
  - Invalid NIK (wrong length, non-numeric) raises ValidationError
  - CitizenManager.create_or_update_with_nik upsert idempotency
  - Default criteria C1-C4 seeded correctly (via seed_initial_data command)
"""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from core.crypto import (
    decrypt_nik,
    encrypt_nik,
    hash_nik,
    mask_name,
    mask_nik,
    sign_pdf_download_token,
    validate_nik,
    verify_pdf_download_token,
)
from core.models import Citizen, Criteria


# ---------------------------------------------------------------------------
# Crypto tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_nik_crypto_roundtrip_and_no_plaintext_at_rest():
    """Core UU PDP requirement: NIK must never appear in plaintext in the DB."""
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

    # Masking
    assert mask_name("Ahmad Subarjo") == "Ahmad S******"
    assert mask_name("Sukarno") == "Su*****"

    # Signed PDF download token
    token = sign_pdf_download_token(citizen.id)
    assert verify_pdf_download_token(token) == citizen.id


@pytest.mark.django_db
def test_invalid_nik_rejected():
    """NIK must be exactly 16 numeric digits."""
    with pytest.raises(ValidationError):
        validate_nik("36740312088500")   # 14 digits
    with pytest.raises(ValidationError):
        validate_nik("367403120885ABCD")  # non-numeric


def test_mask_nik_format():
    """mask_nik must produce the PRD-specified pattern."""
    assert mask_nik("3674031208850002") == "367403******0002"


def test_mask_name_single_word():
    """Single-word name must show first 2 characters + asterisks."""
    assert mask_name("Sukarno") == "Su*****"


def test_mask_name_multi_word():
    """Multi-word name: first word shown, subsequent words masked from 2nd char."""
    assert mask_name("Ahmad Subarjo") == "Ahmad S******"
    # Two-char surname edge case
    assert mask_name("Budi Su") == "Budi S*"


def test_encrypt_nik_32byte_key_enforcement(monkeypatch):
    """AES-256-GCM must reject non-32-byte keys at call time."""
    import core.crypto as cc
    monkeypatch.setattr(cc, "_AES_KEY", b"shortkey")  # 8 bytes — invalid
    with pytest.raises(ValueError, match="32"):
        cc.encrypt_nik("3674031208850002")


def test_nik_hash_is_deterministic():
    """Same NIK + same pepper must always produce the same 64-char hex hash."""
    h1 = hash_nik("3674031208850002")
    h2 = hash_nik("3674031208850002")
    assert h1 == h2
    assert len(h1) == 64


def test_pdf_token_expired_raises(monkeypatch):
    """Expired tokens must not be accepted."""
    import time
    token = sign_pdf_download_token(42)
    # verify with max_age=0 should raise
    with pytest.raises(Exception):
        verify_pdf_download_token(token, max_age=0)


# ---------------------------------------------------------------------------
# Model / upsert tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_citizen_upsert_idempotency():
    """create_or_update_with_nik must return created=False on second call."""
    raw_nik = "1234567890123456"
    _, created1 = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4="9999",
        full_name="Budi Santoso",
        address="Jl. Test 1",
        rt="001",
        rw="002",
    )
    citizen2, created2 = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4="9999",
        full_name="Budi Santoso Updated",
        address="Jl. Test 1 Updated",
        rt="001",
        rw="002",
    )
    assert created1 is True
    assert created2 is False
    assert citizen2.full_name == "Budi Santoso Updated"
    assert Citizen.objects.filter(nik_hash=hash_nik(raw_nik)).count() == 1


@pytest.mark.django_db
def test_seed_initial_data_creates_criteria():
    """seed_initial_data management command must populate C1-C4 with correct weights."""
    from decimal import Decimal

    call_command("seed_initial_data", verbosity=0)

    criteria = {c.code: c for c in Criteria.objects.all()}
    assert set(criteria.keys()) >= {"C1", "C2", "C3", "C4"}

    assert criteria["C1"].criterion_type == "COST"
    assert criteria["C1"].weight == Decimal("0.30")

    assert criteria["C2"].criterion_type == "BENEFIT"
    assert criteria["C2"].weight == Decimal("0.25")

    assert criteria["C3"].criterion_type == "BENEFIT"
    assert criteria["C3"].weight == Decimal("0.25")

    assert criteria["C4"].criterion_type == "COST"
    assert criteria["C4"].weight == Decimal("0.20")

    # Weights must sum to 1.00
    total = sum(c.weight for c in criteria.values())
    assert total == Decimal("1.00")

    # COST C1 Crips 1 must be lowest income (<= Rp 500.000) so min(X)/X_ij gives 1.00 to poorest
    c1_crips1 = criteria["C1"].subcriteria.get(crips_value=1)
    c1_crips5 = criteria["C1"].subcriteria.get(crips_value=5)
    assert "500.000" in c1_crips1.label
    assert "500.000" not in c1_crips5.label


def test_security_audit_unicode_nik_and_tampered_ciphertext_rejected():
    """
    Security audit check (UU PDP & OWASP A02/A03):
    - Non-ASCII Unicode digits (e.g. Arabic-Indic 16 digits) must be rejected by validate_nik & hash_nik.
    - Tampered AES-256-GCM ciphertext or truncated token must raise ValueError.
    - Empty or 2-char names in mask_name must not raise IndexError or leak unmasked chars.
    """
    arabic_digits_nik = "٠١٢٣٤٥٦٧٨٩٠١٢٣٤٥"  # 16 Unicode digits, not ASCII 0-9
    with pytest.raises(ValidationError):
        validate_nik(arabic_digits_nik)
    with pytest.raises(ValidationError):
        hash_nik(arabic_digits_nik)
    with pytest.raises(ValidationError):
        validate_nik(3674031208850002)  # type: ignore[arg-type]

    # Tampered AES-GCM token must raise ValueError
    valid_token = encrypt_nik("3674031208850002")
    flipped_char = "A" if valid_token[-2] != "A" else "B"
    tampered_token = valid_token[:-2] + flipped_char + valid_token[-1]
    with pytest.raises(ValueError, match="Gagal mendekripsi NIK"):
        decrypt_nik(tampered_token)

    with pytest.raises(ValueError, match="Gagal mendekripsi NIK"):
        decrypt_nik("dG9vc2hvcnQ=")  # truncated blob

    # Edge cases for mask_name
    assert mask_name("") == ""
    assert mask_name("   ") == ""
    assert mask_name("Su") == "S*"
    assert mask_name("A") == "*"


@pytest.mark.django_db
def test_citizen_blocks_plaintext_nik_at_rest_and_enforces_prd_schema_constraints():
    """
    Security audit check (UU PDP No. 27/2022):
    - Saving a Citizen directly with plaintext 16-digit NIK in nik_encrypted or nik_masked must raise ValidationError.
    - PRD Section 9 fields (SelectionBatch.cutoff_score, EvaluationDetail.normalized_value, AuditLog.batch)
      and UniqueConstraints (BatchCriteria, Evaluation, EvaluationDetail) must be enforced.
    """
    from decimal import Decimal
    from django.db import IntegrityError
    from django.utils import timezone
    from core.models import (
        AuditLog,
        BatchCriteria,
        Evaluation,
        EvaluationDetail,
        Period,
        SelectionBatch,
    )

    raw_nik = "3674031208850002"
    with pytest.raises(ValidationError, match="UU PDP"):
        bad_citizen = Citizen(
            nik_hash=hash_nik(raw_nik),
            nik_encrypted=raw_nik,  # Plaintext NIK violation!
            nik_masked="367403******0002",
            kk_last4="5501",
            full_name="Ahmad Subarjo",
            address="Jl. Test",
            rt="003",
            rw="001",
        )
        bad_citizen.save()

    call_command("seed_initial_data", verbosity=0)
    c1 = Criteria.objects.get(code="C1")
    assert c1.attribute_type == "COST"

    period = Period.objects.create(
        period_name="Tahap Uji 2026",
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )
    batch = SelectionBatch.objects.create(
        period=period,
        name="Batch Uji 1",
        quota=10,
        cutoff_score=Decimal("0.7250"),
    )
    assert batch.cutoff_score == Decimal("0.7250")

    bc = BatchCriteria.objects.create(
        batch=batch,
        criteria=c1,
        code=c1.code,
        name=c1.name,
        attribute_type=c1.attribute_type,
        frozen_weight=c1.weight,
    )
    assert bc.attribute_type == "COST"

    citizen, _ = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4="5501",
        full_name="Ahmad Subarjo",
        address="Jl. Jurangmangu Barat No. 10",
        rt="003",
        rw="001",
    )
    eval_obj = Evaluation.objects.create(
        batch=batch,
        citizen=citizen,
        real_dependents_count=3,
        disqualification_reason="",
    )
    detail = EvaluationDetail.objects.create(
        evaluation=eval_obj,
        criteria=c1,
        raw_crips_value=3,
        normalized_value=Decimal("0.6000"),
    )
    assert detail.normalized_value == Decimal("0.6000")
    assert detail.normalized_score == Decimal("0.6000")

    log = AuditLog.objects.create(
        batch=batch,
        user_action=AuditLog.Action.BATCH_CALCULATED,
        performed_by="kasi_kesos",
    )
    assert log.batch == batch
    assert log.user_action == AuditLog.Action.BATCH_CALCULATED

    # Duplicate Evaluation for same (batch, citizen) must violate UniqueConstraint
    with pytest.raises(IntegrityError):
        Evaluation.objects.create(batch=batch, citizen=citizen)

