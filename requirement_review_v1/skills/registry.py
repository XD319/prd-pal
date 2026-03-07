"""Skill registry for requirement_review_v1."""

from __future__ import annotations

from .delivery_planning import IMPLEMENTATION_PLAN_SKILL, TEST_PLAN_GENERATE_SKILL
from .executor import SkillExecutor
from .risk_catalog import RISK_CATALOG_SEARCH_SKILL

_EXECUTOR = SkillExecutor()
_SKILLS = {
    IMPLEMENTATION_PLAN_SKILL.name: IMPLEMENTATION_PLAN_SKILL,
    TEST_PLAN_GENERATE_SKILL.name: TEST_PLAN_GENERATE_SKILL,
    RISK_CATALOG_SEARCH_SKILL.name: RISK_CATALOG_SEARCH_SKILL,
}


def get_skill_spec(name: str):
    return _SKILLS[name]


def get_skill_executor() -> SkillExecutor:
    return _EXECUTOR
