"""Window A review helpers for gating and requirement normalization."""

from .gating import GatingConfig, ReviewModeDecision, decide_review_mode
from .normalizer import (
    NormalizedRequirement,
    build_reviewer_input,
    build_reviewer_inputs,
    normalize_requirement,
)

__all__ = [
    "GatingConfig",
    "NormalizedRequirement",
    "ReviewModeDecision",
    "build_reviewer_input",
    "build_reviewer_inputs",
    "decide_review_mode",
    "normalize_requirement",
]
