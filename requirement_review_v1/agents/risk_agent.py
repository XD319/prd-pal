"""Compatibility wrapper for the reusable risk-analysis subflow."""

from __future__ import annotations

from ..state import ReviewState
from ..subflows.risk_analysis import run_risk_analysis_from_review_state


async def run(state: ReviewState) -> ReviewState:
    """Backward-compatible entrypoint for the risk-analysis subflow."""

    return await run_risk_analysis_from_review_state(state)
