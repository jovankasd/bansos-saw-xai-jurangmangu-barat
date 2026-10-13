"""
core/services/saw_engine.py — SAW Engine: Snapshot Freeze, TMS Filter, Normalization, Tie-Breaker.

Public API:
  validate_criteria_weights() -> Decimal
  freeze_batch_criteria(batch) -> list[BatchCriteria]
  calculate_batch_saw(batch_id, performed_by) -> dict

PRD References:
  - FR-01: validate + freeze weights
  - FR-02: TMS exclusion from min/max normalization
  - FR-03: SAW normalization + 4-level tie-breaker
  - Section 6: Batch state machine (Draft → Calculated)
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import (
    AuditLog,
    BatchCriteria,
    Criteria,
    Evaluation,
    EvaluationDetail,
    SelectionBatch,
    SelectionResult,
)
from core.services.tie_breaker import resolve_rankings_with_tie_breaker


# ---------------------------------------------------------------------------
# Weight Validation
# ---------------------------------------------------------------------------


def validate_criteria_weights() -> Decimal:
    """
    Compute the sum of all active Criteria weights and raise ValidationError
    if it is not exactly Decimal("1.00").

    Returns:
        The total weight (Decimal("1.00")) when valid.

    Raises:
        ValidationError: When sum != Decimal("1.00").
    """
    criteria_qs = Criteria.objects.filter(is_active=True)
    total = sum((c.weight for c in criteria_qs), Decimal("0"))
    if total != Decimal("1.00"):
        raise ValidationError(
            f"Total bobot harus persis bernilai 1.00; saat ini total = {total}.",
            code="invalid_weight_sum",
        )
    return total


# ---------------------------------------------------------------------------
# Criteria Snapshot Freeze
# ---------------------------------------------------------------------------


def freeze_batch_criteria(batch: SelectionBatch) -> list[BatchCriteria]:
    """
    Idempotently snapshot all active Criteria weights into BatchCriteria for `batch`.

    Uses update_or_create so re-running on an already-calculated batch
    does NOT raise IntegrityError or create duplicate rows.

    Returns:
        List of BatchCriteria instances (4 items for C1-C4).
    """
    results: list[BatchCriteria] = []
    for criteria in Criteria.objects.filter(is_active=True).order_by("order"):
        bc, _ = BatchCriteria.objects.update_or_create(
            batch=batch,
            criteria=criteria,
            defaults={
                "code": criteria.code,
                "name": criteria.name,
                "criterion_type": criteria.criterion_type,
                "frozen_weight": criteria.weight,
            },
        )
        results.append(bc)
    return results


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def _normalize_benefit(value: Decimal, max_val: Decimal) -> Decimal:
    """r_ij = x_ij / max_j  (Benefit criterion: higher is better)."""
    if max_val == 0:
        return Decimal("0.0000")
    return (value / max_val).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def _normalize_cost(value: Decimal, min_val: Decimal) -> Decimal:
    """r_ij = min_j / x_ij  (Cost criterion: lower is better)."""
    if value == 0:
        return Decimal("0.0000")
    return (min_val / value).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Main SAW Calculation
# ---------------------------------------------------------------------------


@transaction.atomic
def calculate_batch_saw(
    batch_id: int,
    performed_by: str = "system",
) -> dict[str, Any]:
    """
    Execute the full SAW pipeline for a SelectionBatch atomically.

    Pipeline:
      1. Guard: reject if batch.status in (Approved, Published).
      2. Validate ∑w_j == 1.00 and freeze weights into BatchCriteria.
      3. Partition Evaluations into DISQUALIFIED and ELIGIBLE.
      4. Write DISKUALIFIKASI_TMS SelectionResults for DISQUALIFIED.
      5. Validate ELIGIBLE: non-empty, all have complete EvaluationDetail.
      6. Compute min/max per criterion across ELIGIBLE only.
      7. Compute r_ij (normalized) and V_i (preference score) per ELIGIBLE.
      8. Run 4-level tie-breaker and write SelectionResult rows.
      9. Transition batch.status → Calculated; write AuditLog.

    Args:
        batch_id: PK of the SelectionBatch to process.
        performed_by: Username/identifier for AuditLog.

    Returns:
        Summary dict: {status, eligible_candidates, disqualified_tms,
                       tie_breaks_resolved, cutoff_score}.

    Raises:
        SelectionBatch.DoesNotExist: If batch_id is invalid.
        ValidationError: For invalid weight sum, all-TMS batch, or incomplete crips.
    """
    batch = SelectionBatch.objects.select_for_update().get(pk=batch_id)

    # --- 1. State machine guard ---
    if batch.status in (SelectionBatch.Status.APPROVED, SelectionBatch.Status.PUBLISHED):
        raise ValidationError(
            f"Kalkulasi ditolak: batch sudah berstatus '{batch.status}'. "
            "Hanya Approved atau Published yang tidak dapat dikalkulasi ulang.",
            code="batch_already_approved_or_published",
        )

    # --- 2. Weight validation + snapshot freeze ---
    validate_criteria_weights()
    freeze_batch_criteria(batch)

    # Load frozen criteria snapshot (ordered by criteria__order for C1→C4 consistency)
    batch_criteria = list(
        BatchCriteria.objects.filter(batch=batch).select_related("criteria").order_by("criteria__order")
    )
    criteria_by_code: dict[str, BatchCriteria] = {bc.code: bc for bc in batch_criteria}

    # --- 3. Partition evaluations ---
    all_evaluations = list(
        Evaluation.objects.filter(batch=batch).select_related("citizen").prefetch_related("details__criteria")
    )

    if not all_evaluations:
        raise ValidationError(
            "Batch tidak memiliki data usulan evaluasi warga untuk dikalkulasi.",
            code="empty_batch_evaluations",
        )

    disqualified_evals = [e for e in all_evaluations if e.eligibility_status == "DISQUALIFIED"]
    eligible_evals = [e for e in all_evaluations if e.eligibility_status == "ELIGIBLE"]

    # --- 4. Write TMS results (idempotent update_or_create) ---
    for eval_obj in disqualified_evals:
        SelectionResult.objects.update_or_create(
            evaluation=eval_obj,
            defaults={
                "status": SelectionResult.ResultStatus.DISKUALIFIKASI_TMS,
                "final_score_v": Decimal("0.0000"),
                "ranking": None,
                "tie_break_level": 0,
                "cutoff_score": None,
                "explanation_source": SelectionResult.ExplanationSource.INELIGIBLE_NOTICE,
            },
        )

    # --- 5. Validate ELIGIBLE set ---
    if not eligible_evals:
        raise ValidationError(
            "Semua warga dalam batch ini berstatus DISQUALIFIED (TMS). "
            "Tidak ada kandidat ELIGIBLE untuk kalkulasi SAW.",
            code="no_eligible_candidates",
        )

    active_criteria_codes = {bc.code for bc in batch_criteria}
    for eval_obj in eligible_evals:
        detail_codes = {d.criteria.code for d in eval_obj.details.all()}
        missing = active_criteria_codes - detail_codes
        if missing:
            raise ValidationError(
                f"Evaluasi warga {eval_obj.citizen.nik_masked} tidak memiliki data "
                f"kriteria lengkap. Kriteria yang hilang: {sorted(missing)}.",
                code="incomplete_criteria_details",
            )
        for detail in eval_obj.details.all():
            if detail.raw_crips_value <= 0:
                raise ValidationError(
                    f"Evaluasi warga {eval_obj.citizen.nik_masked}: "
                    f"raw_crips_value untuk {detail.criteria.code} harus > 0.",
                    code="invalid_crips_value",
                )

    # --- 6. Compute min/max across ELIGIBLE only ---
    # Build per-criterion raw value sets
    raw_values: dict[str, list[Decimal]] = {code: [] for code in active_criteria_codes}
    for eval_obj in eligible_evals:
        for detail in eval_obj.details.all():
            code = detail.criteria.code
            raw_values[code].append(Decimal(str(detail.raw_crips_value)))

    col_min: dict[str, Decimal] = {code: min(vals) for code, vals in raw_values.items()}
    col_max: dict[str, Decimal] = {code: max(vals) for code, vals in raw_values.items()}

    # --- 7. Compute r_ij and V_i for each ELIGIBLE candidate ---
    candidate_dicts: list[dict[str, Any]] = []

    for eval_obj in eligible_evals:
        details_map: dict[str, EvaluationDetail] = {d.criteria.code: d for d in eval_obj.details.all()}
        normalized: dict[str, Decimal] = {}
        v_i = Decimal("0.0000")

        for bc in batch_criteria:
            code = bc.code
            detail = details_map[code]
            x_ij = Decimal(str(detail.raw_crips_value))

            if bc.criterion_type == Criteria.CriterionType.BENEFIT:
                r_ij = _normalize_benefit(x_ij, col_max[code])
            else:  # COST
                r_ij = _normalize_cost(x_ij, col_min[code])

            normalized[code] = r_ij
            w_j = bc.frozen_weight
            v_i += (w_j * r_ij).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

            # Save normalized value to EvaluationDetail
            detail.normalized_value = r_ij
            detail.save(update_fields=["normalized_value"])

        v_i = v_i.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        candidate_dicts.append({
            "evaluation_id": eval_obj.id,
            "evaluation": eval_obj,
            "final_score_v": v_i,
            "r_c1": normalized.get("C1", Decimal("0")),
            "r_c2": normalized.get("C2", Decimal("0")),
            "real_dependents_count": eval_obj.real_dependents_count or 0,
            "created_at": eval_obj.created_at,
        })

    # --- 8. Tie-breaker + ranking ---
    ranked = resolve_rankings_with_tie_breaker(candidate_dicts, batch.quota)

    cutoff_score = ranked[0]["cutoff_score"] if ranked else None
    tie_breaks_resolved = sum(1 for c in ranked if c["tie_break_level"] > 0)

    # Write SelectionResult for each ELIGIBLE candidate
    for c in ranked:
        SelectionResult.objects.update_or_create(
            evaluation=c["evaluation"],
            defaults={
                "status": c["status"],
                "final_score_v": c["final_score_v"],
                "ranking": c["ranking"],
                "tie_break_level": c["tie_break_level"],
                "cutoff_score": c["cutoff_score"],
            },
        )

    # --- 9. Transition batch status + AuditLog ---
    batch.status = SelectionBatch.Status.CALCULATED
    batch.cutoff_score = cutoff_score
    batch.calculated_at = timezone.now()
    batch.save(update_fields=["status", "cutoff_score", "calculated_at", "updated_at"])

    AuditLog.objects.create(
        batch=batch,
        action=AuditLog.Action.BATCH_CALCULATED,
        performed_by=performed_by,
        detail=(
            f"SAW kalkulasi selesai: {len(eligible_evals)} ELIGIBLE, "
            f"{len(disqualified_evals)} TMS, {tie_breaks_resolved} tie-breaks. "
            f"Cutoff={cutoff_score}."
        ),
    )

    return {
        "status": batch.status,
        "eligible_candidates": len(eligible_evals),
        "disqualified_tms": len(disqualified_evals),
        "tie_breaks_resolved": tie_breaks_resolved,
        "cutoff_score": cutoff_score,
    }
