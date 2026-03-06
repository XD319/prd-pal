"""Skill registry for requirement_review_v1."""

from __future__ import annotations

from .executor import SkillExecutor
from .risk_catalog import RISK_CATALOG_SEARCH_SKILL

_EXECUTOR = SkillExecutor()
_SKILLS = {
    RISK_CATALOG_SEARCH_SKILL.name: RISK_CATALOG_SEARCH_SKILL,
}


def get_skill_spec(name: str):
    return _SKILLS[name]


def get_skill_executor() -> SkillExecutor:
    return _EXECUTOR
