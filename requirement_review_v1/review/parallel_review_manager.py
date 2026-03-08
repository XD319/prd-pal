"""Run multi-role reviewer agents and aggregate their outputs."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .aggregator import aggregate_review_results
from .normalizer import NormalizedRequirement, build_reviewer_inputs, normalize_requirement
from .reviewer_agents import ReviewerConfig, review_engineering, review_product, review_qa, review_security


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
) -> ParallelReviewResult:
    return asyncio.run(
        run_parallel_review_async(
            prd_text,
            output_dir,
            reviewer_config=reviewer_config,
        )
    )


async def run_parallel_review_async(
    prd_text: str,
    output_dir: str | Path,
    *,
    reviewer_config: ReviewerConfig | None = None,
) -> ParallelReviewResult:
    normalized = normalize_requirement(prd_text)
    reviewer_inputs = {
        "product": normalized.for_reviewer("general"),
        "engineering": normalized.for_reviewer("architecture"),
        "qa": normalized.for_reviewer("qa"),
        "security": normalized.for_reviewer("security"),
    }
    results = await asyncio.gather(
        review_product(normalized, config=reviewer_config),
        review_engineering(normalized, config=reviewer_config),
        review_qa(normalized, config=reviewer_config),
        review_security(normalized, config=reviewer_config),
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
