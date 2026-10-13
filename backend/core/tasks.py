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
) -> dict[str, Any]:
    """
    Process XAI narratives for all ELIGIBLE evaluations in a batch.

    Pipeline:
      1. Verify batch is in 'Calculated' or 'Narrated' status.
      2. Iterate through all ELIGIBLE evaluations and generate narratives (via Gemini or Fallback).
      3. Verify that all ELIGIBLE candidates now have non-empty ai_narrative.
      4. If and only if all are narrated, transition batch.status to 'Narrated' and log audit trail.

    Args:
        batch_id: Primary key of the SelectionBatch.
        gemini_client: Optional Gemini client mock or instance.

    Returns:
        dict: Summary of task execution {batch_id, status, total_eligible, narrated_count, all_narrated}.

    Raises:
        ValidationError: If batch status is not 'Calculated' (e.g. Draft, Approved, Published).
        SelectionBatch.DoesNotExist: If batch_id does not exist.
    """
    batch = SelectionBatch.objects.get(pk=batch_id)

    valid_statuses = (SelectionBatch.Status.CALCULATED, SelectionBatch.Status.NARRATED)
    if batch.status not in valid_statuses:
        raise ValidationError(
            f"Hanya batch berstatus 'Calculated' yang dapat diproses XAI. Status saat ini: '{batch.status}'.",
            code="invalid_batch_status_for_xai",
        )

    eligible_evals = list(
        Evaluation.objects.filter(
            batch=batch,
            eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
        ).order_by("id")
    )

    total_eligible = len(eligible_evals)
    if total_eligible == 0:
        logger.warning("Batch #%d tidak memiliki kandidat ELIGIBLE untuk diproses XAI.", batch.id)
        return {
            "batch_id": batch.id,
            "status": batch.status,
            "total_eligible": 0,
            "narrated_count": 0,
            "all_narrated": False,
        }

    # Generate narrative for each candidate
    for eval_obj in eligible_evals:
        try:
            generate_xai_for_evaluation(
                eval_obj.id,
                gemini_client=gemini_client,
                backoff_seconds=0.0 if gemini_client is not None else 1.0,
            )
        except Exception as exc:
            logger.error("Error generating XAI for evaluation #%d: %s", eval_obj.id, exc)

    # Verify that all ELIGIBLE evaluations have a non-empty narrative
    narrated_count = SelectionResult.objects.filter(
        evaluation__batch=batch,
        evaluation__eligibility_status=Evaluation.EligibilityStatus.ELIGIBLE,
    ).exclude(ai_narrative="").count()

    all_narrated = (narrated_count == total_eligible)

    if all_narrated:
        with transaction.atomic():
            batch.status = SelectionBatch.Status.NARRATED
            batch.save(update_fields=["status", "updated_at"])

            AuditLog.objects.create(
                batch=batch,
                action=AuditLog.Action.XAI_GENERATED,
                performed_by="system",
                detail=f"XAI narasi selesai untuk seluruh {narrated_count} kandidat ELIGIBLE. Batch -> Narrated.",
            )
            logger.info("Batch #%d berhasil ditransisikan ke status 'Narrated'.", batch.id)
    else:
        logger.warning(
            "Batch #%d memiliki %d/%d narasi selesai. Status batch tidak ditransisikan ke 'Narrated'.",
            batch.id,
            narrated_count,
            total_eligible,
        )

    return {
        "batch_id": batch.id,
        "status": batch.status,
        "total_eligible": total_eligible,
        "narrated_count": narrated_count,
        "all_narrated": all_narrated,
    }
