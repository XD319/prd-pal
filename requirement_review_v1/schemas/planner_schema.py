"""Schema for the **planner** agent output.

Field names match the JSON contract defined in ``prompts.PLANNER_SYSTEM_PROMPT``
and consumed by ``agents/planner_agent.py``.
"""

from pydantic import BaseModel, ConfigDict, Field

from .base import SafeStrList


# ── sub-models ────────────────────────────────────────────────────────────


class Task(BaseModel):
    """An atomic work item in the delivery plan."""

    id: str
    title: str = ""
    owner: str = ""
    requirement_ids: list[str] = []
    depends_on: SafeStrList = []
    estimate_days: float = 0


class Milestone(BaseModel):
    """A delivery checkpoint grouping related tasks."""

    id: str
    title: str = ""
    includes: SafeStrList = []
    target_days: float = 0


class Dependency(BaseModel):
    """An explicit edge between two tasks (``from`` → ``to``)."""

    model_config = ConfigDict(populate_by_name=True)

    from_task: str = Field(alias="from", default="")
    to: str = ""
    type: str = "blocked_by"


class Estimation(BaseModel):
    """Overall effort summary."""

    total_days: float = 0
    buffer_days: float = 0


# ── top-level output ──────────────────────────────────────────────────────


class PlannerOutput(BaseModel):
    """Wrapper returned by the planner LLM call.

    ``{"tasks": [...], "milestones": [...], "dependencies": [...], "estimation": {...}}``
    """

    tasks: list[Task] = []
    milestones: list[Milestone] = []
    dependencies: list[Dependency] = []
    estimation: Estimation = Field(default_factory=Estimation)


def validate_planner_output(data: dict) -> PlannerOutput:
    """Validate and coerce a raw dict into a :class:`PlannerOutput`."""
    return PlannerOutput.model_validate(data)


# ── minimal example ───────────────────────────────────────────────────────
# validate_planner_output({
#     "tasks": [
#         {"id": "T-1", "title": "Design API", "owner": "BE",
#          "requirement_ids": ["REQ-001"], "depends_on": [], "estimate_days": 3}
#     ],
#     "milestones": [
#         {"id": "M-1", "title": "API Ready", "includes": ["T-1"],
#          "target_days": 5}
#     ],
#     "dependencies": [
#         {"from": "T-2", "to": "T-1", "type": "blocked_by"}
#     ],
#     "estimation": {"total_days": 10, "buffer_days": 2}
# })
