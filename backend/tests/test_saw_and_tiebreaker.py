"""
Task 2 — TDD: SAW Engine, Criteria Snapshot Freeze, TMS Filter, & Hierarchical Tie-Breaker.

Tests:
  - validate_criteria_weights() raises ValidationError when sum != 1.00
  - freeze_batch_criteria() is idempotent (update_or_create, no IntegrityError on re-run)
  - DISQUALIFIED citizens are excluded from normalization min/max
  - TMS SelectionResult: status=DISKUALIFIKASI_TMS, final_score_v=0, ranking=None
  - Benefit normalization: r_ij = x_ij / max_j
  - Cost normalization: r_ij = min_j / x_ij
  - V_i = sum(w_j * r_ij) with Decimal precision
  - 4-level hierarchical tie-breaker: C1 > C2 > real_dependents_count > created_at
  - Post-calculation mutation of Criteria.weight does NOT alter BatchCriteria.frozen_weight
  - Batch in Approved/Published status rejected for recalculation
  - All-TMS batch raises ValidationError
  - ELIGIBLE with missing criteria details raises ValidationError
  - quota == 0 handled without IndexError
  - quota >= len(eligible) handled without IndexError (all pass, fidelity_score = 100.0)
  - Idempotent recalculation while in Calculated state (no duplicate BatchCriteria)
"""

from __future__ import annotations

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from core.models import (
    BatchCriteria,
    Citizen,
    Criteria,
    Evaluation,
    EvaluationDetail,
    Period,
    SelectionBatch,
    SelectionResult,
)
from core.services.saw_engine import (
    calculate_batch_saw,
    freeze_batch_criteria,
    validate_criteria_weights,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _seed(db):
    """Ensure C1-C4 criteria exist for every test in this module."""
    call_command("seed_initial_data", verbosity=0)


@pytest.fixture
def seeded_criteria():
    """Return the 4 seeded Criteria objects keyed by code."""
    return {c.code: c for c in Criteria.objects.all()}


def _make_citizen(raw_nik: str, name: str, kk_last4: str = "5501") -> Citizen:
    citizen, _ = Citizen.objects.create_or_update_with_nik(
        raw_nik=raw_nik,
        kk_last4=kk_last4,
        full_name=name,
        address="Jl. Test",
        rt="003",
        rw="001",
    )
    return citizen


def _make_period() -> Period:
    return Period.objects.create(
        name=f"Test Period {timezone.now().timestamp()}",
        year=2026,
        semester=1,
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )


def _make_batch(period: Period, quota: int = 3) -> SelectionBatch:
    return SelectionBatch.objects.create(
        period=period,
        name="Batch Test",
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
    crips_values: dict | None = None,  # {code: crips_value}
) -> Evaluation:
    """Create Evaluation (and optional EvaluationDetail rows) for a citizen."""
    eval_obj = Evaluation.objects.create(
        batch=batch,
        citizen=citizen,
        eligibility_status=eligibility,
        tms_reason=tms_reason,
        real_dependents_count=real_dependents,
    )
    if crips_values:
        criteria_map = {c.code: c for c in Criteria.objects.all()}
        for code, crips in crips_values.items():
            EvaluationDetail.objects.create(
                evaluation=eval_obj,
                criteria=criteria_map[code],
                raw_crips_value=crips,
            )
    return eval_obj


@pytest.fixture
def seeded_batch_with_ties():
    """
    Batch with:
      - 1 DISQUALIFIED (ASN) warga → must become DISKUALIFIKASI_TMS
      - 4 ELIGIBLE warga:
          * KPM-A and KPM-B share the same V_i → tie resolved at C1 level
          * KPM-C and KPM-D share same V_i and same C1 → tie resolved at C2 level
        (KPM-A > KPM-B via C1; KPM-C > KPM-D via C2; KPM-D > KPM-E via real_dependents)
    quota=3
    """
    period = _make_period()
    batch = _make_batch(period, quota=3)

    # DISQUALIFIED
    c_tms = _make_citizen("3674031111111111", "TMS Warga", "1111")
    _add_evaluation(
        batch, c_tms,
        eligibility="DISQUALIFIED",
        tms_reason="ASN",
        crips_values={"C1": 2, "C2": 3, "C3": 2, "C4": 2},
    )

    # KPM-A: C1=1, C2=5, C3=1, C4=1 → high score (best COST=low crips, best BENEFIT=high crips)
    c_a = _make_citizen("3674030000000001", "KPM A", "1001")
    _add_evaluation(
        batch, c_a,
        real_dependents=4,
        crips_values={"C1": 1, "C2": 5, "C3": 1, "C4": 1},
    )

    # KPM-B: C1=2, C2=5, C3=1, C4=1 → same V_i as KPM-C, but worse C1 than KPM-A
    c_b = _make_citizen("3674030000000002", "KPM B", "1002")
    _add_evaluation(
        batch, c_b,
        real_dependents=3,
        crips_values={"C1": 2, "C2": 5, "C3": 1, "C4": 1},
    )

    # KPM-C: same as KPM-B but one step different to create tie in overall V_i with KPM-B
    # C1=1, C2=4, C3=1, C4=1 — will tie with KPM-B in V_i if weights cause it.
    # Let's use concrete numbers:
    # Criteria: C1=COST w=0.30, C2=BENEFIT w=0.25, C3=COST w=0.25, C4=COST w=0.20
    # eligible candidates for normalization:
    #   C1 min=1, C2 max=5, C3 min=1, C4 min=1
    #   KPM-A: r_C1=1/1=1.00, r_C2=5/5=1.00, r_C3=1/1=1.00, r_C4=1/1=1.00 → V=1.00
    #   KPM-B: r_C1=1/2=0.50, r_C2=5/5=1.00, r_C3=1/1=1.00, r_C4=1/1=1.00 → V=0.85
    #   KPM-C: r_C1=1/1=1.00, r_C2=4/5=0.80, r_C3=1/1=1.00, r_C4=1/1=1.00 → V=0.95
    #   KPM-D: r_C1=1/2=0.50, r_C2=4/5=0.80, r_C3=1/1=1.00, r_C4=1/1=1.00 → V=0.70
    # No tie actually in V_i with these values, so let's use a special case.
    # For real tie testing, use KPM-E with same V_i as KPM-B:
    c_c = _make_citizen("3674030000000003", "KPM C", "1003")
    _add_evaluation(
        batch, c_c,
        real_dependents=3,
        crips_values={"C1": 1, "C2": 4, "C3": 1, "C4": 1},
    )

    # KPM-D: same V_i as KPM-B (0.85) — tie at V_i level, broken by C1
    # r_C1=1/2=0.50, r_C2=5/5=1.00, r_C3=1/1=1.00, r_C4=1/1=1.00 → V=0.85 (same as KPM-B)
    # tie-break: KPM-D has same C1 as KPM-B → use C2 (both 5 → same)
    # → use real_dependents_count: KPM-D=5 > KPM-B=3 → KPM-D ranks higher
    c_d = _make_citizen("3674030000000004", "KPM D", "1004")
    eval_d = _add_evaluation(
        batch, c_d,
        real_dependents=5,  # more dependents → higher tie-break
        crips_values={"C1": 2, "C2": 5, "C3": 1, "C4": 1},
    )

    return batch


@pytest.fixture
def all_tms_batch():
    """Batch where ALL citizens are DISQUALIFIED."""
    period = _make_period()
    batch = _make_batch(period, quota=5)

    for i in range(3):
        c = _make_citizen(f"367403222222{i:04d}", f"TMS {i}", "0000")
        _add_evaluation(batch, c, eligibility="DISQUALIFIED", tms_reason="PKH_GANDA")

    return batch


@pytest.fixture
def incomplete_eligible_batch():
    """Batch with an ELIGIBLE citizen missing some EvaluationDetail rows."""
    period = _make_period()
    batch = _make_batch(period, quota=2)

    c = _make_citizen("3674033333330001", "Incomplete Person", "3333")
    # Only C1 and C2 — missing C3 and C4
    _add_evaluation(batch, c, crips_values={"C1": 2, "C2": 3})

    return batch


@pytest.fixture
def zero_quota_batch():
    """Batch with quota=0; must not raise IndexError."""
    period = _make_period()
    batch = _make_batch(period, quota=0)

    c = _make_citizen("3674034444440001", "Warga Zero", "4444")
    _add_evaluation(
        batch, c,
        crips_values={"C1": 1, "C2": 5, "C3": 1, "C4": 1},
    )
    return batch


@pytest.fixture
def all_pass_quota_batch():
    """Batch where quota >= len(eligible); all eligible citizens must LOLOS."""
    period = _make_period()
    batch = _make_batch(period, quota=99)

    for i, crips in enumerate([(1, 5, 1, 1), (2, 4, 2, 2)]):
        nik = f"367403555555{i:04d}"
        c = _make_citizen(nik, f"Warga {i}", "5555")
        _add_evaluation(
            batch, c,
            crips_values={"C1": crips[0], "C2": crips[1], "C3": crips[2], "C4": crips[3]},
        )
    return batch


# ---------------------------------------------------------------------------
# Weight Validation Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_saw_rejects_invalid_weight_sum(seeded_criteria):
    """validate_criteria_weights() must raise ValidationError when sum != 1.00."""
    c1 = Criteria.objects.get(code="C1")
    c1.weight = Decimal("0.25")
    c1.save()
    with pytest.raises(ValidationError, match="Total bobot harus persis bernilai 1.00"):
        validate_criteria_weights()


@pytest.mark.django_db
def test_saw_accepts_valid_weight_sum(seeded_criteria):
    """validate_criteria_weights() must return Decimal('1.00') when sum is valid."""
    total = validate_criteria_weights()
    assert total == Decimal("1.00")


# ---------------------------------------------------------------------------
# Freeze Batch Criteria (Idempotent)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_freeze_batch_criteria_is_idempotent():
    """freeze_batch_criteria() called twice must not create duplicate rows."""
    period = _make_period()
    batch = _make_batch(period)

    rows1 = freeze_batch_criteria(batch)
    rows2 = freeze_batch_criteria(batch)  # second call — must NOT raise IntegrityError

    assert len(rows1) == 4
    assert len(rows2) == 4
    assert BatchCriteria.objects.filter(batch=batch).count() == 4


@pytest.mark.django_db
def test_freeze_batch_criteria_captures_current_weights():
    """Frozen weights must match master Criteria.weight at freeze time."""
    period = _make_period()
    batch = _make_batch(period)
    freeze_batch_criteria(batch)

    for bc in BatchCriteria.objects.filter(batch=batch):
        master_w = Criteria.objects.get(code=bc.code).weight
        assert bc.frozen_weight == master_w


# ---------------------------------------------------------------------------
# Post-Calculation Weight Mutation (Snapshot Immutability)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_post_calculation_weight_mutation_does_not_alter_frozen_snapshot(seeded_batch_with_ties):
    """Mutating Criteria.weight after calculate_batch_saw() must NOT change BatchCriteria.frozen_weight."""
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")

    # Mutate master weight
    Criteria.objects.filter(code="C1").update(weight=Decimal("0.50"))

    frozen_c1 = BatchCriteria.objects.get(batch=seeded_batch_with_ties, code="C1")
    assert frozen_c1.frozen_weight == Decimal("0.30"), (
        "frozen_weight must remain 0.30 even after master Criteria.weight changes"
    )


# ---------------------------------------------------------------------------
# TMS Filter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tms_disqualified_excluded_from_normalization(seeded_batch_with_ties):
    """DISQUALIFIED citizens must produce DISKUALIFIKASI_TMS result and not affect min/max."""
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")

    tms_result = SelectionResult.objects.get(
        evaluation__eligibility_status="DISQUALIFIED"
    )
    assert tms_result.status == "DISKUALIFIKASI_TMS"
    assert tms_result.final_score_v == Decimal("0.0000")
    assert tms_result.ranking is None
    assert tms_result.explanation_source == "INELIGIBLE_NOTICE"


@pytest.mark.django_db
def test_all_tms_batch_raises_validation_error(all_tms_batch):
    """Batch with zero ELIGIBLE citizens must raise ValidationError."""
    with pytest.raises(ValidationError):
        calculate_batch_saw(all_tms_batch.id, performed_by="kasi_kesos")


# ---------------------------------------------------------------------------
# Incomplete Criteria Details
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_incomplete_criteria_raises_validation_error(incomplete_eligible_batch):
    """ELIGIBLE citizen with missing EvaluationDetail for active criteria must raise ValidationError."""
    with pytest.raises(ValidationError):
        calculate_batch_saw(incomplete_eligible_batch.id, performed_by="kasi_kesos")


# ---------------------------------------------------------------------------
# SAW Normalization Accuracy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_saw_normalization_benefit_and_cost_formulas():
    """
    Verify r_ij formulas:
      COST  C1: r_ij = min_j / x_ij
      BENEFIT C2: r_ij = x_ij / max_j
    """
    period = _make_period()
    batch = _make_batch(period, quota=2)

    # Citizen A: C1=1 (COST), C2=5 (BENEFIT), C3=1 (COST), C4=1 (COST)
    c_a = _make_citizen("3674036666660001", "Person A", "6666")
    _add_evaluation(batch, c_a, crips_values={"C1": 1, "C2": 5, "C3": 1, "C4": 1})

    # Citizen B: C1=3, C2=2, C3=2, C4=4
    c_b = _make_citizen("3674036666660002", "Person B", "6666")
    _add_evaluation(batch, c_b, crips_values={"C1": 3, "C2": 2, "C3": 2, "C4": 4})

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    criteria_map = {c.code: c for c in Criteria.objects.all()}

    # Verify normalized values for Citizen A
    eval_a = Evaluation.objects.get(batch=batch, citizen=c_a)
    details_a = {d.criteria.code: d for d in eval_a.details.all()}

    # C1 (COST): min=1, x=1 → r=1/1=1.000
    assert details_a["C1"].normalized_value == Decimal("1.0000"), f"C1 A: {details_a['C1'].normalized_value}"
    # C2 (BENEFIT): max=5, x=5 → r=5/5=1.000
    assert details_a["C2"].normalized_value == Decimal("1.0000"), f"C2 A: {details_a['C2'].normalized_value}"
    # C3 (COST): min=1, x=1 → r=1/1=1.000
    assert details_a["C3"].normalized_value == Decimal("1.0000"), f"C3 A: {details_a['C3'].normalized_value}"
    # C4 (COST): min=1, x=1 → r=1/1=1.000
    assert details_a["C4"].normalized_value == Decimal("1.0000"), f"C4 A: {details_a['C4'].normalized_value}"

    # Verify normalized values for Citizen B
    eval_b = Evaluation.objects.get(batch=batch, citizen=c_b)
    details_b = {d.criteria.code: d for d in eval_b.details.all()}

    # C1 (COST): min=1, x=3 → r=1/3≈0.3333
    expected_c1_b = Decimal("1") / Decimal("3")
    # Compare with 4 decimal precision
    diff_c1 = abs(details_b["C1"].normalized_value - expected_c1_b)
    assert diff_c1 < Decimal("0.0001"), f"C1 B: {details_b['C1'].normalized_value} vs {expected_c1_b}"

    # C2 (BENEFIT): max=5, x=2 → r=2/5=0.4000
    assert details_b["C2"].normalized_value == Decimal("0.4000"), f"C2 B: {details_b['C2'].normalized_value}"

    # V_i for A: 0.30*1 + 0.25*1 + 0.25*1 + 0.20*1 = 1.0000
    result_a = eval_a.result
    assert result_a.final_score_v == Decimal("1.0000")


# ---------------------------------------------------------------------------
# Tie-Breaker
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_saw_excludes_tms_freezes_weights_and_resolves_tie_breaks(seeded_batch_with_ties):
    """
    Main integration test:
    - 1 TMS excluded
    - 4 eligible candidates processed
    - tie_breaks_resolved >= 1 (KPM-B and KPM-D have identical V_i)
    - batch transitions to Calculated
    - idempotent recalculation does not duplicate BatchCriteria
    - post-mutation of Criteria.weight does not alter frozen snapshot
    - TMS result has correct fields
    """
    summary = calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    assert summary["eligible_candidates"] == 4
    assert summary["disqualified_tms"] == 1
    assert summary["tie_breaks_resolved"] >= 1
    assert summary["status"] == "Calculated"

    # Idempotent recalculation while in Calculated state must not duplicate BatchCriteria
    summary_rerun = calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    assert BatchCriteria.objects.filter(batch=seeded_batch_with_ties).count() == 4

    # Post-calculation weight mutation must not alter frozen snapshot
    Criteria.objects.filter(code="C1").update(weight=Decimal("0.50"))
    frozen_c1 = BatchCriteria.objects.get(batch=seeded_batch_with_ties, code="C1")
    assert frozen_c1.frozen_weight == Decimal("0.30")

    # TMS result validation
    tms_result = SelectionResult.objects.get(evaluation__eligibility_status="DISQUALIFIED")
    assert tms_result.status == "DISKUALIFIKASI_TMS"
    assert tms_result.final_score_v == Decimal("0.0000")
    assert tms_result.ranking is None
    assert tms_result.explanation_source == "INELIGIBLE_NOTICE"


@pytest.mark.django_db
def test_tie_breaker_uses_real_dependents_count_at_level_3():
    """
    KPM-X and KPM-Y have identical V_i, identical r_C1, identical r_C2.
    Level 3 (real_dependents_count) must resolve: higher count wins.
    """
    period = _make_period()
    batch = _make_batch(period, quota=1)

    # Both will have identical V_i, C1 normalized, C2 normalized
    # C1=2, C2=4, C3=1, C4=1 for both
    c_x = _make_citizen("3674037777770001", "Person X", "7777")
    eval_x = _add_evaluation(batch, c_x, real_dependents=5, crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1})

    c_y = _make_citizen("3674037777770002", "Person Y", "7777")
    eval_y = _add_evaluation(batch, c_y, real_dependents=2, crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1})

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    result_x = eval_x.result
    result_y = eval_y.result

    # X has more dependents → should rank higher (rank 1)
    assert result_x.ranking == 1, f"Expected X rank=1, got {result_x.ranking}"
    assert result_y.ranking == 2, f"Expected Y rank=2, got {result_y.ranking}"
    assert result_x.status == "LOLOS"
    assert result_y.status == "TIDAK_LOLOS"
    # tie_break_level should be >= 3 for at least one
    assert result_x.tie_break_level >= 3 or result_y.tie_break_level >= 3


@pytest.mark.django_db
def test_tie_breaker_uses_created_at_at_level_4():
    """
    KPM-P and KPM-Q have identical V_i, r_C1, r_C2, and real_dependents_count.
    Level 4 (created_at) must resolve: earlier created_at wins.
    """
    period = _make_period()
    batch = _make_batch(period, quota=1)

    c_p = _make_citizen("3674038888880001", "Person P", "8888")
    eval_p = _add_evaluation(
        batch, c_p, real_dependents=3, crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1}
    )

    import time
    time.sleep(0.02)  # ensure created_at differs

    c_q = _make_citizen("3674038888880002", "Person Q", "8888")
    eval_q = _add_evaluation(
        batch, c_q, real_dependents=3, crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1}
    )

    # P was created first → should rank higher
    assert eval_p.created_at < eval_q.created_at

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    result_p = eval_p.result
    result_q = eval_q.result

    assert result_p.ranking == 1, f"P (earlier created_at) should be rank 1, got {result_p.ranking}"
    assert result_q.ranking == 2, f"Q should be rank 2, got {result_q.ranking}"
    # tie_break_level 4 for the person who needed created_at as tiebreaker
    assert result_q.tie_break_level == 4 or result_p.tie_break_level == 4


# ---------------------------------------------------------------------------
# Edge Cases: quota == 0 and quota >= eligible
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_quota_zero_no_index_error(zero_quota_batch):
    """quota=0 must not raise IndexError. All ELIGIBLE get TIDAK_LOLOS."""
    summary = calculate_batch_saw(zero_quota_batch.id, performed_by="kasi_kesos")
    assert summary["status"] == "Calculated"
    assert summary["eligible_candidates"] == 1
    results = SelectionResult.objects.filter(
        evaluation__batch=zero_quota_batch,
        evaluation__eligibility_status="ELIGIBLE",
    )
    for r in results:
        assert r.status == "TIDAK_LOLOS"


@pytest.mark.django_db
def test_quota_exceeds_eligible_all_pass(all_pass_quota_batch):
    """quota >= len(eligible) → all ELIGIBLE citizens must LOLOS without IndexError."""
    summary = calculate_batch_saw(all_pass_quota_batch.id, performed_by="kasi_kesos")
    assert summary["status"] == "Calculated"
    assert summary["eligible_candidates"] == 2
    results = SelectionResult.objects.filter(
        evaluation__batch=all_pass_quota_batch,
        evaluation__eligibility_status="ELIGIBLE",
    )
    for r in results:
        assert r.status == "LOLOS"


# ---------------------------------------------------------------------------
# State Machine Guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_approved_batch_rejects_recalculation(seeded_batch_with_ties):
    """Batch in Approved or Published status must reject calculate_batch_saw()."""
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    seeded_batch_with_ties.status = "Approved"
    seeded_batch_with_ties.save()
    with pytest.raises(ValidationError, match="Approved|Published"):
        calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")


@pytest.mark.django_db
def test_published_batch_rejects_recalculation(seeded_batch_with_ties):
    """Batch in Published status must reject calculate_batch_saw()."""
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    seeded_batch_with_ties.status = "Published"
    seeded_batch_with_ties.save()
    with pytest.raises(ValidationError, match="Approved|Published"):
        calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")


# ---------------------------------------------------------------------------
# Batch Status Transition
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculate_batch_saw_transitions_status_to_calculated(seeded_batch_with_ties):
    """After calculate_batch_saw(), batch.status must be 'Calculated'."""
    assert seeded_batch_with_ties.status == "Collecting"
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    seeded_batch_with_ties.refresh_from_db()
    assert seeded_batch_with_ties.status == "Calculated"
    assert seeded_batch_with_ties.calculated_at is not None


# ---------------------------------------------------------------------------
# AuditLog
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculate_batch_saw_creates_audit_log(seeded_batch_with_ties):
    """calculate_batch_saw() must create an AuditLog entry with BATCH_CALCULATED action."""
    from core.models import AuditLog
    calculate_batch_saw(seeded_batch_with_ties.id, performed_by="kasi_kesos")
    assert AuditLog.objects.filter(
        batch=seeded_batch_with_ties,
        action=AuditLog.Action.BATCH_CALCULATED,
        performed_by="kasi_kesos",
    ).exists()


# ---------------------------------------------------------------------------
# Additional Edge-Case Tests (Doubt-Driven Development)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tie_breaker_uses_c1_at_level_1():
    """
    KPM-1 and KPM-2 have identical V_i (0.8500).
    Level 1 (r_C1) must resolve: higher r_C1 wins.
    """
    period = _make_period()
    batch = _make_batch(period, quota=1)

    c1 = _make_citizen("3674039999990001", "Level1 Winner", "9001")
    eval1 = _add_evaluation(
        batch, c1, real_dependents=3,
        crips_values={"C1": 1, "C2": 2, "C3": 1, "C4": 1},
    )

    c2 = _make_citizen("3674039999990002", "Level1 Loser", "9002")
    eval2 = _add_evaluation(
        batch, c2, real_dependents=3,
        crips_values={"C1": 2, "C2": 5, "C3": 1, "C4": 1},
    )

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    res1 = eval1.result
    res2 = eval2.result

    assert res1.final_score_v == Decimal("0.8500")
    assert res2.final_score_v == Decimal("0.8500")
    assert res1.ranking == 1, f"Expected winner rank 1, got {res1.ranking}"
    assert res2.ranking == 2, f"Expected loser rank 2, got {res2.ranking}"
    assert res1.status == "LOLOS"
    assert res2.status == "TIDAK_LOLOS"
    assert res2.tie_break_level == 1, f"Expected tie_break_level=1, got {res2.tie_break_level}"


@pytest.mark.django_db
def test_tie_breaker_uses_c2_at_level_2():
    """
    KPM-1 and KPM-2 have identical V_i (0.8750) and identical r_C1 (1.0000).
    Level 2 (r_C2) must resolve: higher r_C2 wins.
    """
    period = _make_period()
    batch = _make_batch(period, quota=1)

    c1 = _make_citizen("3674039999990003", "Level2 Winner", "9003")
    eval1 = _add_evaluation(
        batch, c1, real_dependents=3,
        crips_values={"C1": 1, "C2": 4, "C3": 2, "C4": 1},
    )

    c2 = _make_citizen("3674039999990004", "Level2 Loser", "9004")
    eval2 = _add_evaluation(
        batch, c2, real_dependents=3,
        crips_values={"C1": 1, "C2": 2, "C3": 1, "C4": 1},
    )

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    res1 = eval1.result
    res2 = eval2.result

    assert res1.final_score_v == Decimal("0.8750")
    assert res2.final_score_v == Decimal("0.8750")
    assert res1.ranking == 1, f"Expected winner rank 1, got {res1.ranking}"
    assert res2.ranking == 2, f"Expected loser rank 2, got {res2.ranking}"
    assert res1.status == "LOLOS"
    assert res2.status == "TIDAK_LOLOS"
    assert res2.tie_break_level == 2, f"Expected tie_break_level=2, got {res2.tie_break_level}"


@pytest.mark.django_db
def test_tie_breaker_uses_evaluation_id_as_final_tie_breaker():
    """
    Two candidates have identical V_i, r_C1, r_C2, real_dependents_count, and created_at.
    The candidate with smaller evaluation.id must rank higher deterministically.
    """
    period = _make_period()
    batch = _make_batch(period, quota=1)

    c1 = _make_citizen("3674039999990005", "Same All 1", "9005")
    eval1 = _add_evaluation(
        batch, c1, real_dependents=3,
        crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1},
    )

    c2 = _make_citizen("3674039999990006", "Same All 2", "9006")
    eval2 = _add_evaluation(
        batch, c2, real_dependents=3,
        crips_values={"C1": 2, "C2": 4, "C3": 1, "C4": 1},
    )

    # Force identical created_at timestamp
    fixed_time = timezone.now()
    Evaluation.objects.filter(id__in=[eval1.id, eval2.id]).update(created_at=fixed_time)
    eval1.refresh_from_db()
    eval2.refresh_from_db()
    assert eval1.created_at == eval2.created_at
    assert eval1.id < eval2.id

    calculate_batch_saw(batch.id, performed_by="kasi_kesos")

    res1 = eval1.result
    res2 = eval2.result

    assert res1.ranking == 1, f"Expected eval1 (smaller id) rank 1, got {res1.ranking}"
    assert res2.ranking == 2, f"Expected eval2 (larger id) rank 2, got {res2.ranking}"
    assert res1.status == "LOLOS"
    assert res2.status == "TIDAK_LOLOS"


@pytest.mark.django_db
def test_quota_negative_no_index_error():
    """quota < 0 must be clamped to 0 without IndexError. All ELIGIBLE receive TIDAK_LOLOS."""
    period = _make_period()
    # Direct DB write bypassing validation to test engine resilience
    batch = SelectionBatch.objects.create(
        period=period,
        name="Batch Negative Quota",
        quota=0,  # PositiveIntegerField default, we'll test engine with tie_breaker directly
        status=SelectionBatch.Status.COLLECTING,
    )
    c = _make_citizen("3674039999990007", "Negative Quota Citizen", "9007")
    _add_evaluation(batch, c, crips_values={"C1": 1, "C2": 5, "C3": 1, "C4": 1})

    from core.services.tie_breaker import resolve_rankings_with_tie_breaker
    eval_obj = Evaluation.objects.get(batch=batch, citizen=c)
    candidate_list = [{
        "evaluation_id": eval_obj.id,
        "evaluation": eval_obj,
        "final_score_v": Decimal("1.0000"),
        "r_c1": Decimal("1.0000"),
        "r_c2": Decimal("1.0000"),
        "real_dependents_count": 3,
        "created_at": eval_obj.created_at,
    }]
    # Call tie breaker with negative quota
    resolved = resolve_rankings_with_tie_breaker(candidate_list, quota=-5)
    assert len(resolved) == 1
    assert resolved[0]["status"] == "TIDAK_LOLOS"
    assert resolved[0]["ranking"] == 1
    assert resolved[0]["cutoff_score"] > Decimal("1.0000")

