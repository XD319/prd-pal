"""Product-focused heuristic reviewer."""

from __future__ import annotations

import asyncio

from ..normalizer import NormalizedRequirement
from .base import ReviewFinding, ReviewerConfig, ReviewerResult, limit_items


async def review(requirement: NormalizedRequirement, config: ReviewerConfig | None = None) -> ReviewerResult:
    resolved = config or ReviewerConfig()
    findings: list[ReviewFinding] = []
    open_questions: list[str] = []

    if not requirement.scenarios:
        findings.append(
            ReviewFinding(
                title="User scenarios are missing",
                detail="The PRD does not describe concrete user scenarios or business flows.",
                severity="high",
                category="scope",
                reviewer="product",
            )
        )

    if not requirement.acceptance_criteria:
        findings.append(
            ReviewFinding(
                title="Acceptance criteria are incomplete",
                detail="The PRD lacks testable acceptance criteria for product sign-off.",
                severity="high",
                category="acceptance",
                reviewer="product",
            )
        )

    if requirement.summary == "Requirement summary unavailable.":
        open_questions.append("What is the concise product goal and success outcome for this PRD?")

    if requirement.scenarios and not requirement.roles:
        open_questions.append("Which user roles or operators own the described scenarios?")

    await asyncio.sleep(0)
    return ReviewerResult(
        reviewer="product",
        findings=limit_items(findings, resolved.top_n_findings),
        open_questions=limit_items(open_questions, resolved.top_n_questions),
        risk_items=(),
        summary="Product review completed against scenarios and acceptance coverage.",
    )
