from __future__ import annotations

from typing import Dict, List, TypedDict


class ReviewState(TypedDict, total=False):
    """LangGraph state for the requirement-review workflow.

    `total=False` makes every field optional so that LangGraph can
    do partial updates without requiring all keys on every node return.
    """

    # ── core review fields ────────────────────────────────────────
    requirement_doc: str
    run_dir: str
    parsed_items: List[dict]
    review_results: List[dict]
    final_report: str
    trace: dict

    # ── delivery-planning fields ──────────────────────────────────
    tasks: List[dict]
    milestones: List[dict]
    dependencies: List[dict]
    estimation: Dict[str, object]


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
    )
