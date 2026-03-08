"""Window A review helpers for gating and requirement normalization."""

from .aggregator import AggregatedReview, AggregatedReviewArtifacts, aggregate_review_results
from .gating import GatingConfig, ReviewModeDecision, decide_review_mode
from .normalizer import (
    NormalizedRequirement,
    build_reviewer_input,
    build_reviewer_inputs,
    normalize_requirement,
)
from .parallel_review_manager import ParallelReviewResult, run_parallel_review, run_parallel_review_async

__all__ = [
    "AggregatedReview",
    "AggregatedReviewArtifacts",
    "GatingConfig",
    "NormalizedRequirement",
    "ParallelReviewResult",
    "ReviewModeDecision",
    "aggregate_review_results",
    "build_reviewer_input",
    "build_reviewer_inputs",
    "decide_review_mode",
    "normalize_requirement",
    "run_parallel_review",
    "run_parallel_review_async",
]
