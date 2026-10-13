"""
core/tasks.py — Asynchronous Worker Tasks for Bansos SAW+XAI.

PRD References:
  - FR-04: Background job processing for Gemini Flash XAI.
  - Section 6: State machine progression (Calculated -> Narrated).
  - Transition guard: Batch status transitions to "Narrated" ONLY when ALL eligible candidates have narratives.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import AuditLog, Evaluation, SelectionBatch, SelectionResult
from core.services.xai_explainer import generate_xai_for_evaluation

logger = logging.getLogger(__name__)


def process_batch_xai_task(
    batch_id: int,
    gemini_client: Any = None,
    evaluation_id: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """
    Process XAI narratives for ELIGIBLE evaluations in a batch (PRD Section 10.4).

    Pipeline:
      1. Verify batch is in 'Calculated' or 'Narrated' status.
      2. If evaluation_id is given, process only that candidate (e.g. ?evaluation_id=45).
      3. Otherwise, iterate through ELIGIBLE candidates. If candidate already has
         ai_narrative and not force, skip re-generation (idempotent resume).
      4. Verify narrative completion status across all ELIGIBLE candidates.
      5. Under database row lock (select_for_update), transition batch.status to 'Narrated'
         if and only if 100% of ELIGIBLE candidates have narratives.

    Args:
        batch_id: Primary key of the SelectionBatch.
        gemini_client: Optional Gemini client mock or instance.
        evaluation_id: Optional PK to process a single evaluation only.
        force: If True, re-generates narrative even if one already exists.

    Returns:
        dict: Summary of task execution:
              {batch_id, status, total_eligible, narrated_count, all_narrated, gemini_success, fallback_used}.

    Raises:
        ValidationError: If batch status is not 'Calculated'/'Narrated' or evaluation_id is invalid.
        SelectionBatch.DoesNotExist: If batch_id does not exist.
    """
    batch = SelectionBatch.objects.get(pk=batch_id)

    valid_statuses = (SelectionBatch.Status.CALCULATED, SelectionBatch.Status.NARRATED)
    if batch.status not in valid_statuses:
        raise ValidationError(
            f"Hanya batch berstatus 'Calculated' yang dapat diproses XAI. Status saat ini: '{batch.status}'.",
            code="invalid_batch_status_for_xai",
        )

    all_eligible_evals = list(
        Evaluation.objects.filter(
            batch=batch,
            eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
        ).order_by("id")
    )

    total_eligible = len(all_eligible_evals)
    if total_eligible == 0:
        logger.warning("Batch #%d tidak memiliki kandidat ELIGIBLE untuk diproses XAI.", batch.id)
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "total_eligible": 0,
            "narrated_count": 0,
            "all_narrated": False,
            "gemini_success": 0,
            "fallback_used": 0,
        }

    # Determine subset to process
    if evaluation_id is not None:
        target_eval = Evaluation.objects.filter(
            pk=evaluation_id,
            batch=batch,
            eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
        ).first()
        if not target_eval:
            raise ValidationError(
                f"Evaluasi #{evaluation_id} tidak ditemukan sebagai kandidat ELIGIBLE pada Batch #{batch.id}.",
                code="invalid_target_evaluation",
            )
        evals_to_process = [target_eval]
    else:
        evals_to_process = all_eligible_evals

    # Generate narratives
    for eval_obj in evals_to_process:
        # Check if already narrated
        existing_result = getattr(eval_obj, "result", None)
        if existing_result and existing_result.ai_narrative and not force:
            logger.debug("Evaluasi #%d sudah memiliki narasi; melewatinya (force=False).", eval_obj.id)
            continue

        try:
            generate_xai_for_evaluation(
                eval_obj.id,
                gemini_client=gemini_client,
                backoff_seconds=0.0 if gemini_client is not None else 1.0,
            )
        except Exception as exc:
            logger.error("Error generating XAI for evaluation #%d: %s", eval_obj.id, exc)

    # Compute progress & metrics across all eligible candidates in the batch
    results = SelectionResult.objects.filter(
        evaluation__batch=batch,
        evaluation__eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
    ).exclude(ai_narrative="")

    narrated_count = results.count()
    gemini_success = results.filter(
        explanation_source__in=[SelectionResult.ExplanationSource.GEMINI, SelectionResult.ExplanationSource.GEMINI_API]
    ).count()
    fallback_used = results.filter(
        explanation_source=SelectionResult.ExplanationSource.DETERMINISTIC_FALLBACK
    ).count()

    all_narrated = (narrated_count == total_eligible)

    # State transition under transaction lock to prevent race conditions
    with transaction.atomic():
        batch_locked = SelectionBatch.objects.select_for_update().get(pk=batch.id)
        if all_narrated:
            if batch_locked.status != SelectionBatch.Status.NARRATED:
                batch_locked.status = SelectionBatch.Status.NARRATED
                batch_locked.save(update_fields=["status", "updated_at"])

                AuditLog.objects.create(
                    batch=batch_locked,
                    action=AuditLog.Action.XAI_GENERATED,
                    performed_by="system",
                    detail=f"XAI narasi selesai untuk seluruh {narrated_count} kandidat ELIGIBLE. Batch -> Narrated.",
                )
                logger.info("Batch #%d berhasil ditransisikan ke status 'Narrated'.", batch_locked.id)
        else:
            logger.warning(
                "Batch #%d memiliki %d/%d narasi selesai. Status batch tetap '%s'.",
                batch_locked.id,
                narrated_count,
                total_eligible,
                batch_locked.status,
            )
        current_status = batch_locked.status

    return {
        "batch_id": batch.id,
        "status": current_status,
        "total_eligible": total_eligible,
        "narrated_count": narrated_count,
        "all_narrated": all_narrated,
        "gemini_success": gemini_success,
        "fallback_used": fallback_used,
    }
