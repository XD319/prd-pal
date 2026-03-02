"""Schema for the **reviewer** agent output.

Field names match the JSON contract defined in ``prompts.REVIEWER_SYSTEM_PROMPT``
and consumed by ``agents/reviewer_agent.py`` and ``agents/reporter_agent.py``.
"""

from pydantic import BaseModel

from .base import NormalizedBool, SafeStrList


# ── sub-models ────────────────────────────────────────────────────────────


class ReviewResult(BaseModel):
    """Per-requirement quality assessment."""

    id: str
    is_clear: NormalizedBool = True
    is_testable: NormalizedBool = True
    is_ambiguous: NormalizedBool = False
    issues: SafeStrList = []
    suggestions: str = ""


class PlanReview(BaseModel):
    """Top-level plan quality comments."""

    coverage: str = ""
    milestones: str = ""
    estimation: str = ""


# ── top-level output ──────────────────────────────────────────────────────


class ReviewerOutput(BaseModel):
    """Wrapper returned by the reviewer LLM call.

    ``{"review_results": [...], "plan_review": {...}}``
    """

    review_results: list[ReviewResult] = []
    plan_review: PlanReview = PlanReview()


def validate_reviewer_output(data: dict) -> ReviewerOutput:
    """Validate and coerce a raw dict into a :class:`ReviewerOutput`."""
    return ReviewerOutput.model_validate(data)


# ── minimal example ───────────────────────────────────────────────────────
# validate_reviewer_output({
#     "review_results": [
#         {
#             "id": "REQ-001",
#             "is_clear": "true",        # string → True via normalize_bool
#             "is_testable": True,
#             "is_ambiguous": "false",    # string → False via normalize_bool
#             "issues": ["Vague term: 'user-friendly'"],
#             "suggestions": "Replace with measurable UX criteria"
#         },
#         {
#             "id": "REQ-002",
#             "is_clear": True,
#             "is_testable": False,
#             "is_ambiguous": False,
#             "issues": None,             # safe_list → []
#             "suggestions": ""
#         }
#     ],
#     "plan_review": {
#         "coverage": "REQ-003 has no matching task",
#         "milestones": "All critical tasks covered",
#         "estimation": "Buffer looks reasonable at 17%"
#     }
# })
