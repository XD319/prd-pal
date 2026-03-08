"""Heuristic routing for single-review vs parallel-review mode."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .normalizer import normalize_requirement


@dataclass(frozen=True, slots=True)
class GatingConfig:
    """Thresholds used to choose between single and parallel review."""

    length_threshold_chars: int = 1800
    module_threshold: int = 3
    role_threshold: int = 3
    risk_keyword_threshold: int = 3
    cross_system_threshold: int = 1
    parallel_score_threshold: int = 2
    risk_keywords: tuple[str, ...] = (
        "security",
        "privacy",
        "compliance",
        "audit",
        "migration",
        "rollback",
        "payment",
        "billing",
        "pii",
        "encryption",
        "latency",
        "performance",
        "idempotent",
        "rate limit",
        "timeout",
    )
    cross_system_keywords: tuple[str, ...] = (
        "integration",
        "upstream",
        "downstream",
        "third-party",
        "third party",
        "external",
        "webhook",
        "event bus",
        "queue",
        "shared service",
        "cross-system",
        "cross system",
        "microservice",
        "api gateway",
        "legacy system",
    )


@dataclass(frozen=True, slots=True)
class ReviewModeDecision:
    """Decision payload for Window A review routing."""

    mode: Literal["single_review", "parallel_review"]
    complexity_score: int
    reasons: tuple[str, ...] = field(default_factory=tuple)
    length_chars: int = 0
    module_count: int = 0
    role_count: int = 0
    risk_keyword_hits: int = 0
    cross_system_hits: int = 0


def decide_review_mode(prd_text: str, config: GatingConfig | None = None) -> ReviewModeDecision:
    """Choose the cheaper single route unless the PRD shows enough complexity."""

    resolved_config = config or GatingConfig()
    normalized = normalize_requirement(prd_text)
    text = normalized.source_text

    length_chars = len(text)
    module_count = len(normalized.modules)
    role_count = len(normalized.roles)
    risk_keyword_hits = _count_keyword_hits(text, resolved_config.risk_keywords)
    cross_system_hits = max(
        _count_keyword_hits(text, resolved_config.cross_system_keywords),
        len(normalized.dependency_hints),
    )

    reasons: list[str] = []
    complexity_score = 0

    if length_chars >= resolved_config.length_threshold_chars:
        complexity_score += 1
        reasons.append(f"length_chars={length_chars} exceeds {resolved_config.length_threshold_chars}")

    if module_count >= resolved_config.module_threshold:
        complexity_score += 1
        reasons.append(f"module_count={module_count} exceeds {resolved_config.module_threshold}")

    if role_count >= resolved_config.role_threshold:
        complexity_score += 1
        reasons.append(f"role_count={role_count} exceeds {resolved_config.role_threshold}")

    if risk_keyword_hits >= resolved_config.risk_keyword_threshold:
        complexity_score += 1
        reasons.append(
            f"risk_keyword_hits={risk_keyword_hits} exceeds {resolved_config.risk_keyword_threshold}"
        )

    if cross_system_hits >= resolved_config.cross_system_threshold:
        complexity_score += 1
        reasons.append(
            f"cross_system_hits={cross_system_hits} exceeds {resolved_config.cross_system_threshold}"
        )

    mode: Literal["single_review", "parallel_review"] = "single_review"
    if (
        complexity_score >= resolved_config.parallel_score_threshold
        or risk_keyword_hits >= resolved_config.risk_keyword_threshold
    ):
        mode = "parallel_review"

    if not reasons:
        reasons.append("complexity signals stayed below parallel thresholds")

    return ReviewModeDecision(
        mode=mode,
        complexity_score=complexity_score,
        reasons=tuple(reasons),
        length_chars=length_chars,
        module_count=module_count,
        role_count=role_count,
        risk_keyword_hits=risk_keyword_hits,
        cross_system_hits=cross_system_hits,
    )


def _count_keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    lowered = str(text or "").casefold()
    hits = 0
    for keyword in keywords:
        if not keyword:
            continue
        pattern = r"\b" + re.escape(keyword.casefold()).replace(r"\ ", r"[\s-]+") + r"\b"
        if re.search(pattern, lowered):
            hits += 1
    return hits
