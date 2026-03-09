"""Run multi-role reviewer agents and aggregate their outputs."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping

from .aggregator import aggregate_review_results
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


@dataclass(frozen=True, slots=True)
class ParallelReviewResult:
    normalized_requirement: dict[str, Any]
    reviewer_inputs: dict[str, str]
    reviewer_results: tuple[dict[str, Any], ...]
    aggregated: dict[str, Any]


def run_parallel_review(
    prd_text: str,
    output_dir: str | Path,
    *,
    reviewer_config: ReviewerConfig | None = None,
    reviewer_timeouts: Mapping[str, float] | None = None,
) -> ParallelReviewResult:
    return asyncio.run(
        run_parallel_review_async(
            prd_text,
            output_dir,
            reviewer_config=reviewer_config,
            reviewer_timeouts=reviewer_timeouts,
        )
    )


async def run_parallel_review_async(
    prd_text: str,
    output_dir: str | Path,
    *,
    reviewer_config: ReviewerConfig | None = None,
    reviewer_timeouts: Mapping[str, float] | None = None,
) -> ParallelReviewResult:
    normalized = normalize_requirement(prd_text)
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
            for reviewer in _REVIEWER_ORDER
        )
    )
    aggregated = aggregate_review_results(results, output_dir)
    return ParallelReviewResult(
        normalized_requirement=_normalized_requirement_dict(normalized),
        reviewer_inputs=reviewer_inputs,
        reviewer_results=tuple(result.to_dict() for result in results),
        aggregated=aggregated.to_dict(),
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
