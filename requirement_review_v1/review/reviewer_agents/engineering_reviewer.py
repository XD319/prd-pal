"""Engineering-focused heuristic reviewer."""

from __future__ import annotations

import asyncio

from ..normalizer import NormalizedRequirement
from .base import ReviewFinding, ReviewerConfig, ReviewerResult, RiskItem, limit_items


async def review(requirement: NormalizedRequirement, config: ReviewerConfig | None = None) -> ReviewerResult:
    resolved = config or ReviewerConfig()
    findings: list[ReviewFinding] = []
    risks: list[RiskItem] = []
    open_questions: list[str] = []

    if requirement.dependency_hints and not requirement.modules:
        findings.append(
            ReviewFinding(
                title="Dependencies lack implementation boundaries",
                detail="The PRD implies integrations or shared dependencies but does not name impacted modules.",
                severity="medium",
                category="architecture",
                reviewer="engineering",
            )
        )

    if len(requirement.dependency_hints) >= 2:
        risks.append(
            RiskItem(
                title="Cross-system sequencing risk",
                detail="Multiple dependency hints suggest implementation order and ownership could drift.",
                severity="high",
                category="integration",
                mitigation="Define system boundaries, contract owners, and rollout order before build starts.",
                reviewer="engineering",
            )
        )

    if requirement.roles and len(requirement.roles) >= 4:
        open_questions.append("Which engineering team owns each module and integration boundary?")

    await asyncio.sleep(0)
    return ReviewerResult(
        reviewer="engineering",
        findings=limit_items(findings, resolved.top_n_findings),
        open_questions=limit_items(open_questions, resolved.top_n_questions),
        risk_items=limit_items(risks, resolved.top_n_risks),
        summary="Engineering review completed against module and dependency complexity.",
    )
