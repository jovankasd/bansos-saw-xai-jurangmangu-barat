"""
core/services/sanitizer.py — Zero-PII Anonymous Payload Builder for Gemini XAI & Fallback.

PRD References:
  - FR-04: Data masking 100%, anonymous payload strictly without name, NIK, KK, or address.
  - Section 8.1: Payload structure (applicant_code, rank, quota, status, final_score, cutoff_score, criteria_data).
  - UU PDP No. 27/2022: Strict Zero-PII boundary before contacting external AI services.
  - Snapshot Rule: Reads BatchCriteria.frozen_weight, NEVER master Criteria.weight.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError

from core.models import (
    BatchCriteria,
    Evaluation,
    EvaluationDetail,
    SelectionResult,
    SubCriteria,
)


def build_anonymous_payload(evaluation_id: int) -> dict[str, Any]:
    """
    Construct an anonymous, Zero-PII evaluation payload adhering to PRD Section 8.1.

    Guarantees:
      1. Contains ZERO personally identifiable information (no name, NIK, KK, address, RT/RW).
      2. Weights are loaded strictly from BatchCriteria.frozen_weight (immutable snapshot).
      3. All numbers are converted to native Python types (float/int) for standard JSON serialization.
      4. Calculates avg_passed_score for each criterion based on candidates with status 'LOLOS'.

    Args:
        evaluation_id: Primary key of the Evaluation instance.

    Returns:
        dict: Sanitized JSON-serializable dictionary.

    Raises:
        ValidationError: If evaluation is DISQUALIFIED (TMS) or not yet calculated.
        Evaluation.DoesNotExist: If evaluation_id is not found.
    """
    eval_obj = (
        Evaluation.objects.select_related("batch", "citizen")
        .prefetch_related("details__criteria")
        .get(pk=evaluation_id)
    )

    if eval_obj.eligibility_status == Evaluation.EligibilityStatus.DISQUALIFIED:
        raise ValidationError(
            f"Evaluasi #{eval_obj.id} berstatus DISQUALIFIED (TMS: {eval_obj.tms_reason}). "
            "Warga TMS tidak diproses oleh modul XAI (mendapatkan INELIGIBLE_NOTICE).",
            code="evaluation_is_tms",
        )

    try:
        result: SelectionResult = eval_obj.result
    except SelectionResult.DoesNotExist:
        raise ValidationError(
            f"Evaluasi #{eval_obj.id} belum memiliki hasil kalkulasi SAW (SelectionResult).",
            code="evaluation_not_calculated",
        )

    batch = eval_obj.batch

    # 1. Fetch frozen batch criteria (order by criteria__order)
    batch_criteria = list(
        BatchCriteria.objects.filter(batch=batch)
        .select_related("criteria")
        .order_by("criteria__order")
    )
    if not batch_criteria:
        raise ValidationError(
            f"Batch #{batch.id} belum memiliki snapshot kriteria (BatchCriteria).",
            code="missing_batch_criteria",
        )

    # 2. Compute avg_passed_score per criterion across candidates who achieved 'LOLOS'
    passed_results = SelectionResult.objects.filter(
        evaluation__batch=batch,
        evaluation__eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
        status=SelectionResult.ResultStatus.LOLOS,
    ).select_related("evaluation")

    passed_eval_ids = list(passed_results.values_list("evaluation_id", flat=True))

    avg_passed_by_criterion: dict[int, float] = {}
    if passed_eval_ids:
        # Fetch normalized values for passed candidates
        passed_details = EvaluationDetail.objects.filter(
            evaluation_id__in=passed_eval_ids
        ).values("criteria_id", "normalized_value")

        totals: dict[int, list[float]] = {}
        for d in passed_details:
            cid = d["criteria_id"]
            val = float(d["normalized_value"])
            totals.setdefault(cid, []).append(val)

        for cid, vals in totals.items():
            avg_passed_by_criterion[cid] = round(sum(vals) / len(vals), 4)

    # 3. Build candidate's criteria details map
    detail_by_criteria_id = {d.criteria_id: d for d in eval_obj.details.all()}

    # Pre-fetch SubCriteria labels for this batch's criteria
    subcriteria_map: dict[tuple[int, int], str] = {
        (sc.criteria_id, sc.crips_value): sc.label
        for sc in SubCriteria.objects.filter(
            criteria_id__in=[bc.criteria_id for bc in batch_criteria]
        )
    }

    criteria_data_list: list[dict[str, Any]] = []
    for bc in batch_criteria:
        cid = bc.criteria_id
        detail = detail_by_criteria_id.get(cid)
        if not detail:
            continue

        raw_crips = detail.raw_crips_value
        label = subcriteria_map.get((cid, raw_crips), f"Crips {raw_crips}")
        norm_val = float(detail.normalized_value)

        # If there are LOLOS candidates, use calculated average; otherwise, fallback to candidate's own normalized score
        avg_score = avg_passed_by_criterion.get(cid, norm_val)

        criteria_data_list.append({
            "code": bc.code,
            "name": bc.name,
            "type": bc.criterion_type,
            "weight": float(bc.frozen_weight),
            "raw_crips_label": label,
            "normalized_score": round(norm_val, 4),
            "avg_passed_score": round(avg_score, 4),
        })

    # 4. Construct anonymous payload (zero PII)
    cutoff = float(result.cutoff_score) if result.cutoff_score is not None else 0.0

    payload: dict[str, Any] = {
        "applicant_code": f"KPM-{eval_obj.id:03d}",
        "rank": result.ranking,
        "quota": batch.quota,
        "status": result.status,
        "final_score": round(float(result.final_score_v), 4),
        "cutoff_score": round(cutoff, 4),
        "criteria_data": criteria_data_list,
    }

    return payload
