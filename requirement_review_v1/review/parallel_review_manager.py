"""Run multi-role reviewer agents and aggregate their outputs."""

from __future__ import annotations

import asyncio
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

from .aggregator import aggregate_review_results
from .gating import ReviewModeDecision
from .normalizer import NormalizedRequirement, build_reviewer_inputs, normalize_requirement
from .reviewer_agents import ReviewerConfig, ReviewerResult, review_engineering, review_product, review_qa, review_security

_DEFAULT_REVIEWER_TIMEOUT_SECONDS = 30.0
_REVIEWER_ORDER = ("product", "engineering", "qa", "security")
_REVIEWER_FUNCTIONS: dict[str, Callable[..., Awaitable[ReviewerResult]]] = {
    "product": review_product,
    "engineering": review_engineering,
    "qa": review_qa,
    "security": review_security,
}
_SECURITY_SIGNAL_RE = re.compile(r"\b(security|privacy|compliance|audit|pii|payment|encryption|sso|oauth)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ParallelReviewResult:
    normalized_requirement: dict[str, Any]
    reviewer_inputs: dict[str, str]
    reviewer_results: tuple[dict[str, Any], ...]
    aggregated: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReviewerSelection:
    reviewers_used: tuple[str, ...]
    reviewers_skipped: tuple[dict[str, str], ...]
    reasons: tuple[str, ...]


def run_parallel_review(
    prd_text: str,
    output_dir: str | Path,
    *,
    reviewer_config: ReviewerConfig | None = None,
    reviewer_timeouts: Mapping[str, float] | None = None,
    gating_decision: ReviewModeDecision | None = None,
) -> ParallelReviewResult:
    return asyncio.run(
        run_parallel_review_async(
            prd_text,
            output_dir,
            reviewer_config=reviewer_config,
            reviewer_timeouts=reviewer_timeouts,
            gating_decision=gating_decision,
        )
    )


async def run_parallel_review_async(
    prd_text: str,
    output_dir: str | Path,
    *,
    reviewer_config: ReviewerConfig | None = None,
    reviewer_timeouts: Mapping[str, float] | None = None,
    gating_decision: ReviewModeDecision | None = None,
) -> ParallelReviewResult:
    normalized = normalize_requirement(prd_text)
    selection = select_reviewers(normalized)
    reviewer_inputs = {
        "product": normalized.for_reviewer("general"),
        "engineering": normalized.for_reviewer("architecture"),
        "qa": normalized.for_reviewer("qa"),
        "security": normalized.for_reviewer("security"),
    }
    resolved_timeouts = _resolve_reviewer_timeouts(reviewer_timeouts)
    results = await asyncio.gather(
        *(
            _run_reviewer_with_resilience(
                reviewer,
                normalized,
                reviewer_config=reviewer_config,
                timeout_seconds=resolved_timeouts[reviewer],
            )
            for reviewer in selection.reviewers_used
        )
    )
    aggregated = aggregate_review_results(
        results,
        output_dir,
        selected_mode="full",
        gating_decision=asdict(gating_decision) if gating_decision else {},
        gating_reasons=selection.reasons,
        reviewers_used=selection.reviewers_used,
        reviewers_skipped=selection.reviewers_skipped,
        normalized_requirement=_normalized_requirement_dict(normalized),
    )
    return ParallelReviewResult(
        normalized_requirement=_normalized_requirement_dict(normalized),
        reviewer_inputs={reviewer: reviewer_inputs[reviewer] for reviewer in selection.reviewers_used},
        reviewer_results=tuple(result.to_dict() for result in results),
        aggregated=aggregated.to_dict(),
    )


def select_reviewers(requirement: NormalizedRequirement) -> ReviewerSelection:
    reviewers_used: list[str] = []
    reviewers_skipped: list[dict[str, str]] = []
    reasons: list[str] = []

    if requirement.scenarios or requirement.acceptance_criteria or requirement.summary != "Requirement summary unavailable.":
        reviewers_used.append("product")
        reasons.append("product enabled because user-facing scope or acceptance context exists")
    else:
        reviewers_skipped.append({"reviewer": "product", "reason": "missing scenario and acceptance context"})

    if requirement.modules or requirement.dependency_hints or len(requirement.roles) >= 3:
        reviewers_used.append("engineering")
        reasons.append("engineering enabled because modules, dependencies, or cross-team handoffs were detected")
    else:
        reviewers_skipped.append({"reviewer": "engineering", "reason": "no module or integration complexity detected"})

    if requirement.acceptance_criteria or requirement.scenarios or requirement.risk_hints:
        reviewers_used.append("qa")
        reasons.append("qa enabled because validation scope or risk paths were detected")
    else:
        reviewers_skipped.append({"reviewer": "qa", "reason": "no acceptance, scenario, or risk coverage detected"})

    security_sensitive = bool(_SECURITY_SIGNAL_RE.search(requirement.source_text)) or bool(requirement.risk_hints)
    if security_sensitive:
        reviewers_used.append("security")
        reasons.append("security enabled because sensitive data, compliance, or release-control signals were detected")
    else:
        reviewers_skipped.append({"reviewer": "security", "reason": "no security-sensitive scope was detected"})

    if not reviewers_used:
        reviewers_used.append("product")
        reasons.append("product enabled as a safe fallback reviewer")
        reviewers_skipped = [item for item in reviewers_skipped if item.get("reviewer") != "product"]

    return ReviewerSelection(
        reviewers_used=tuple(reviewers_used),
        reviewers_skipped=tuple(reviewers_skipped),
        reasons=tuple(reasons),
    )


def _normalized_requirement_dict(requirement: NormalizedRequirement) -> dict[str, Any]:
    payload = asdict(requirement)
    payload["reviewer_inputs"] = build_reviewer_inputs(requirement)
    return payload


def _resolve_reviewer_timeouts(reviewer_timeouts: Mapping[str, float] | None) -> dict[str, float]:
    resolved = {reviewer: _DEFAULT_REVIEWER_TIMEOUT_SECONDS for reviewer in _REVIEWER_ORDER}
    if reviewer_timeouts is None:
        return resolved

    for reviewer in _REVIEWER_ORDER:
        raw_timeout = reviewer_timeouts.get(reviewer)
        if raw_timeout is None:
            continue
        resolved[reviewer] = float(raw_timeout)
    return resolved


async def _run_reviewer_with_resilience(
    reviewer: str,
    requirement: NormalizedRequirement,
    *,
    reviewer_config: ReviewerConfig | None,
    timeout_seconds: float,
) -> ReviewerResult:
    review_fn = _REVIEWER_FUNCTIONS[reviewer]

    try:
        if timeout_seconds > 0:
            return await asyncio.wait_for(
                review_fn(requirement, config=reviewer_config),
                timeout=timeout_seconds,
            )
        return await review_fn(requirement, config=reviewer_config)
    except TimeoutError:
        reason = f"timed out after {timeout_seconds:.1f}s"
        return _partial_reviewer_result(reviewer, status="timeout", reason=reason)
    except Exception as exc:
        reason = str(exc).strip() or exc.__class__.__name__
        return _partial_reviewer_result(reviewer, status="error", reason=reason)


def _partial_reviewer_result(reviewer: str, *, status: str, reason: str) -> ReviewerResult:
    normalized_reason = str(reason or "").strip() or status
    return ReviewerResult(
        reviewer=reviewer,
        findings=(),
        open_questions=(),
        risk_items=(),
        summary=f"{reviewer.title()} reviewer {status}: {normalized_reason}.",
        status=status,
        error_message=normalized_reason,
    )
