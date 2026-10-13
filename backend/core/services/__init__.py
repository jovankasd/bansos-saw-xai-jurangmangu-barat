"""
core/services/__init__.py
"""

from core.services.deterministic_fallback import generate_deterministic_fallback
from core.services.sanitizer import build_anonymous_payload
from core.services.saw_engine import (
    calculate_batch_saw,
    freeze_batch_criteria,
    validate_criteria_weights,
)
from core.services.tie_breaker import resolve_rankings_with_tie_breaker
from core.services.xai_explainer import (
    generate_xai_for_evaluation,
    map_explanation_to_public_schema,
    validate_xai_output,
)

__all__ = [
    "validate_criteria_weights",
    "freeze_batch_criteria",
    "calculate_batch_saw",
    "resolve_rankings_with_tie_breaker",
    "build_anonymous_payload",
    "generate_deterministic_fallback",
    "generate_xai_for_evaluation",
    "map_explanation_to_public_schema",
    "validate_xai_output",
]
