"""Markdown prompt templates for coding-agent handoff."""

from __future__ import annotations

from dataclasses import dataclass


BASE_SECTION_ORDER = (
    "Goal",
    "Project Context",
    "Required Changes",
    "Constraints",
    "Acceptance Criteria",
    "Testing Requirements",
    "Output Expectations",
)


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Static metadata that shapes a rendered handoff prompt."""

    agent_name: str
    role_summary: str
    output_hint: str
    section_order: tuple[str, ...] = BASE_SECTION_ORDER


CODEX_PROMPT_TEMPLATE = PromptTemplate(
    agent_name="Codex",
    role_summary="Use the execution pack as the source of truth and implement the smallest complete change set.",
    output_hint="Return a concise implementation summary, the files changed, and the tests or checks you ran.",
)


CLAUDE_CODE_PROMPT_TEMPLATE = PromptTemplate(
    agent_name="Claude Code",
    role_summary="Use the execution pack as the source of truth and focus on delivery validation, safety checks, and test completeness.",
    output_hint="Return a concise validation summary, remaining risks, and the tests or checks you ran.",
)
