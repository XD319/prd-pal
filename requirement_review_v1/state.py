from __future__ import annotations

from typing import Any, TypedDict


class ParsedItemState(TypedDict):
    """State shape aligned with ``schemas.ParsedItem``."""

    id: str
    description: str
    acceptance_criteria: list[str]


class TaskState(TypedDict):
    """State shape aligned with ``schemas.Task``."""

    id: str
    title: str
    owner: str
    requirement_ids: list[str]
    depends_on: list[str]
    estimate_days: float


class MilestoneState(TypedDict):
    """State shape aligned with ``schemas.Milestone``."""

    id: str
    title: str
    includes: list[str]
    target_days: float


DependencyState = TypedDict(
    "DependencyState",
    {"from": str, "to": str, "type": str},
)
"""State shape aligned with planner dependency output."""


class EstimationState(TypedDict):
    """State shape aligned with ``schemas.Estimation``."""

    total_days: float
    buffer_days: float


class RiskItemState(TypedDict):
    """State shape aligned with ``schemas.RiskItem``."""

    id: str
    description: str
    impact: str
    mitigation: str
    buffer_days: float
    evidence_ids: list[str]
    evidence_snippets: list[str]


class ReviewResultItemState(TypedDict):
    """State shape aligned with ``schemas.ReviewResultItem``."""

    id: str
    is_clear: bool
    is_testable: bool
    is_ambiguous: bool
    issues: list[str]
    suggestions: str


class PlanReviewState(TypedDict):
    """State shape aligned with ``schemas.PlanReview``."""

    coverage: str
    milestones: str
    estimation: str


class ReviewState(TypedDict, total=False):
    """LangGraph state for the requirement-review workflow.

    `total=False` makes every field optional so that LangGraph can
    do partial updates without requiring all keys on every node return.
    """

    # ── core review fields ────────────────────────────────────────
    requirement_doc: str
    run_dir: str
    parsed_items: list[ParsedItemState]
    review_results: list[ReviewResultItemState]
    final_report: str
    trace: dict[str, Any]

    # ── delivery-planning fields ──────────────────────────────────
    tasks: list[TaskState]
    milestones: list[MilestoneState]
    dependencies: list[DependencyState]
    estimation: EstimationState
    risks: list[RiskItemState]
    plan_review: PlanReviewState
    metrics: dict[str, Any]
    revision_round: int
    high_risk_ratio: float
    routing_reason: str
    parser_prompt_version: str


def create_initial_state(requirement_doc: str) -> ReviewState:
    """Build the seed state that kicks off the graph."""
    return ReviewState(
        requirement_doc=requirement_doc,
        parsed_items=[],
        review_results=[],
        final_report="",
        trace={},
        tasks=[],
        milestones=[],
        dependencies=[],
        estimation={},
        risks=[],
        plan_review={},
        metrics={},
        revision_round=0,
        high_risk_ratio=0.0,
        routing_reason="",
        parser_prompt_version="v1.1",
    )
