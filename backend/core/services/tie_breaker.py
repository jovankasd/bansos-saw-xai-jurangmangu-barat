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
from typing import Any


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
        - quota == 0: all candidates receive status=TIDAK_LOLOS
        - quota >= len(candidates): all candidates receive status=LOLOS
    """
    if not candidates:
        return candidates

    # Sort by 4-level tie-breaker key:
    #   key = (-V_i, -r_C1, -r_C2, -real_dependents_count, created_at, evaluation_id)
    # All Decimal values are negated for descending sort.
    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            -c["final_score_v"],
            -c["r_c1"],
            -c["r_c2"],
            -c["real_dependents_count"],
            c["created_at"],
            c["evaluation_id"],
        ),
    )

    n = len(sorted_candidates)
    effective_quota = min(quota, n)

    # Determine cutoff_score safely
    if effective_quota == 0:
        # quota == 0 → no one passes; cutoff = highest score (no one meets it)
        cutoff_score = sorted_candidates[0]["final_score_v"] + Decimal("0.0001")
    elif effective_quota >= n:
        # All candidates pass; cutoff = lowest score (everyone meets it)
        cutoff_score = sorted_candidates[-1]["final_score_v"]
    else:
        cutoff_score = sorted_candidates[effective_quota - 1]["final_score_v"]

    # Determine tie_break_level for each candidate
    # A candidate needs a tie_break_level > 0 if there is another candidate with the same V_i
    # and they fall at the boundary (i.e., without tie-breaking the result could differ).
    # For simplicity and correctness: detect ties in V_i globally, then annotate
    # the level at which the ordering was decided for each candidate.

    def _tie_break_level(prev: dict, curr: dict) -> int:
        """Return the level at which `curr` was differentiated from `prev`."""
        if prev is None:
            return 0
        if prev["final_score_v"] != curr["final_score_v"]:
            return 0
        if prev["r_c1"] != curr["r_c1"]:
            return 1
        if prev["r_c2"] != curr["r_c2"]:
            return 2
        if prev["real_dependents_count"] != curr["real_dependents_count"]:
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
