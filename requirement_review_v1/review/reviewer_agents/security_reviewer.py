"""Security-focused heuristic reviewer."""

from __future__ import annotations

import asyncio
import re

from ..normalizer import NormalizedRequirement
from .base import ReviewFinding, ReviewerConfig, ReviewerResult, RiskItem, limit_items


_SECURITY_TOPIC_RE = re.compile(r"\b(security|privacy|compliance|audit|pii|payment|encryption|sso|oauth)\b", re.IGNORECASE)


async def review(requirement: NormalizedRequirement, config: ReviewerConfig | None = None) -> ReviewerResult:
    resolved = config or ReviewerConfig()
    findings: list[ReviewFinding] = []
    risks: list[RiskItem] = []
    open_questions: list[str] = []

    joined_risk_text = " ".join(requirement.risk_hints)
    sensitive_scope = bool(_SECURITY_TOPIC_RE.search(requirement.source_text)) or bool(_SECURITY_TOPIC_RE.search(joined_risk_text))

    if sensitive_scope and not requirement.risk_hints:
        findings.append(
            ReviewFinding(
                title="Sensitive scope lacks explicit controls",
                detail="The PRD references security-sensitive behavior but does not state concrete security or compliance constraints.",
                severity="high",
                category="security",
                reviewer="security",
            )
        )

    if sensitive_scope:
        risks.append(
            RiskItem(
                title="Security review gate required",
                detail="Sensitive flows or data handling are implied and should be reviewed before release approval.",
                severity="high",
                category="security",
                mitigation="Add logging, access control, data handling, and rollback expectations to the PRD.",
                reviewer="security",
            )
        )

    if sensitive_scope and not requirement.acceptance_criteria:
        open_questions.append("Which explicit security acceptance checks must pass before release?")

    await asyncio.sleep(0)
    return ReviewerResult(
        reviewer="security",
        findings=limit_items(findings, resolved.top_n_findings),
        open_questions=limit_items(open_questions, resolved.top_n_questions),
        risk_items=limit_items(risks, resolved.top_n_risks),
        summary="Security review completed against sensitive data and release controls.",
    )
