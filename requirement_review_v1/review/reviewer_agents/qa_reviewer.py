"""QA-focused heuristic reviewer."""

from __future__ import annotations

import asyncio

from ..normalizer import NormalizedRequirement
from .base import ReviewFinding, ReviewerConfig, ReviewerResult, RiskItem, limit_items


async def review(requirement: NormalizedRequirement, config: ReviewerConfig | None = None) -> ReviewerResult:
    resolved = config or ReviewerConfig()
    findings: list[ReviewFinding] = []
    risks: list[RiskItem] = []
    open_questions: list[str] = []

    if not requirement.acceptance_criteria:
        findings.append(
            ReviewFinding(
                title="Test oracle is missing",
                detail="QA cannot derive pass/fail expectations because acceptance criteria are absent.",
                severity="high",
                category="testability",
                reviewer="qa",
            )
        )

    if requirement.risk_hints and len(requirement.acceptance_criteria) < len(requirement.risk_hints):
        findings.append(
            ReviewFinding(
                title="Edge-case coverage looks thin",
                detail="The PRD mentions risk-heavy behavior but acceptance coverage is thinner than the risk surface.",
                severity="medium",
                category="testability",
                reviewer="qa",
            )
        )

    if requirement.risk_hints:
        risks.append(
            RiskItem(
                title="Regression scope may be underestimated",
                detail="Risk-related scenarios imply extra negative-path and regression testing.",
                severity="medium",
                category="quality",
                mitigation="Add explicit failure-path, rollback, and regression checks to the acceptance criteria.",
                reviewer="qa",
            )
        )

    if requirement.scenarios and not requirement.acceptance_criteria:
        open_questions.append("How should each scenario be validated end-to-end in UAT or regression testing?")

    await asyncio.sleep(0)
    return ReviewerResult(
        reviewer="qa",
        findings=limit_items(findings, resolved.top_n_findings),
        open_questions=limit_items(open_questions, resolved.top_n_questions),
        risk_items=limit_items(risks, resolved.top_n_risks),
        summary="QA review completed against acceptance and regression coverage.",
    )
