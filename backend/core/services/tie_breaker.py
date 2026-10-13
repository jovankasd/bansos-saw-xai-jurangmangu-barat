"""
core/services/tie_breaker.py — 4-Level Hierarchical Tie-Breaker for SAW Engine.

PRD FR-03: When final_score_v (V_i) values are identical at the quota boundary,
resolve deterministically in this priority order:
  Level 1: Highest normalized r_{i, C1} (descending)
  Level 2: Highest normalized r_{i, C2} (descending)
  Level 3: Highest Evaluation.real_dependents_count (descending)
  Level 4: Earliest Evaluation.created_at (ascending), then id ASC

Each candidate dict must have keys:
  evaluation_id, final_score_v, r_c1, r_c2, real_dependents_count,
  created_at, eligibility_status

Returns list[dict] with added keys: ranking, status, tie_break_level, cutoff_score
"""

from __future__ import annotations

from decimal import Decimal
from django.utils import timezone


def _to_decimal(val: Any) -> Decimal:
    if val is None:
        return Decimal("0.0000")
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0.0000")


def resolve_rankings_with_tie_breaker(
    candidates: list[dict[str, Any]],
    quota: int,
) -> list[dict[str, Any]]:
    """
    Sort candidates by 4-level deterministic tie-breaker and assign rankings.

    Args:
        candidates: List of candidate dicts (ELIGIBLE only, pre-filtered from DISQUALIFIED).
        quota: Number of recipients to pass.

    Returns:
        Same list with added/updated keys: ranking, status, tie_break_level, cutoff_score.

    Edge cases:
        - quota <= 0: all candidates receive status=TIDAK_LOLOS
        - quota >= len(candidates): all candidates receive status=LOLOS
    """
    if not candidates:
        return candidates

    epoch_zero = timezone.now()

    # Sort by 4-level tie-breaker key:
    #   key = (-V_i, -r_C1, -r_C2, -real_dependents_count, created_at, evaluation_id)
    # All Decimal values are negated for descending sort.
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            -_to_decimal(c.get("final_score_v")),
            -_to_decimal(c.get("r_c1")),
            -_to_decimal(c.get("r_c2")),
            -(c.get("real_dependents_count") or 0),
            c.get("created_at") or epoch_zero,
            c.get("evaluation_id") or 0,
        ),
    )

    n = len(sorted_candidates)
    effective_quota = max(0, min(quota, n))

    # Determine cutoff_score safely
    if effective_quota == 0:
        # quota <= 0 → no one passes; cutoff = highest score (no one meets it)
        cutoff_score = _to_decimal(sorted_candidates[0].get("final_score_v")) + Decimal("0.0001")
    elif effective_quota >= n:
        # All candidates pass; cutoff = lowest score (everyone meets it)
        cutoff_score = _to_decimal(sorted_candidates[-1].get("final_score_v"))
    else:
        cutoff_score = _to_decimal(sorted_candidates[effective_quota - 1].get("final_score_v"))

    # Determine tie_break_level for each candidate
    def _tie_break_level(prev: dict | None, curr: dict) -> int:
        """Return the level at which `curr` was differentiated from `prev`."""
        if prev is None:
            return 0
        if _to_decimal(prev.get("final_score_v")) != _to_decimal(curr.get("final_score_v")):
            return 0
        if _to_decimal(prev.get("r_c1")) != _to_decimal(curr.get("r_c1")):
            return 1
        if _to_decimal(prev.get("r_c2")) != _to_decimal(curr.get("r_c2")):
            return 2
        if (prev.get("real_dependents_count") or 0) != (curr.get("real_dependents_count") or 0):
            return 3
        return 4

    for i, candidate in enumerate(sorted_candidates):
        rank = i + 1
        candidate["ranking"] = rank
        candidate["cutoff_score"] = cutoff_score

        if rank <= effective_quota:
            candidate["status"] = "LOLOS"
        else:
            candidate["status"] = "TIDAK_LOLOS"

        # Determine tie_break_level: compare with the previous candidate in sorted order
        prev = sorted_candidates[i - 1] if i > 0 else None
        candidate["tie_break_level"] = _tie_break_level(prev, candidate)

    return sorted_candidates
