"""Shared result models for heuristic reviewer agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class ReviewFinding:
    title: str
    detail: str
    severity: str = "medium"
    category: str = "general"
    requirement_refs: tuple[str, ...] = ()
    reviewer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class RiskItem:
    title: str
    detail: str
    severity: str = "medium"
    category: str = "delivery"
    mitigation: str = ""
    reviewer: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ReviewerResult:
    reviewer: str
    findings: tuple[ReviewFinding, ...] = ()
    open_questions: tuple[str, ...] = ()
    risk_items: tuple[RiskItem, ...] = ()
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "reviewer": self.reviewer,
            "findings": [item.to_dict() for item in self.findings],
            "open_questions": list(self.open_questions),
            "risk_items": [item.to_dict() for item in self.risk_items],
            "summary": self.summary,
        }


@dataclass(frozen=True, slots=True)
class ReviewerConfig:
    top_n_findings: int = 3
    top_n_questions: int = 3
    top_n_risks: int = 3


def normalize_severity(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"critical", "blocker", "sev1", "high"}:
        return "high"
    if normalized in {"low", "minor", "sev3"}:
        return "low"
    return "medium"


def limit_items(items: list[Any], limit: int) -> tuple[Any, ...]:
    return tuple(items[: max(int(limit or 0), 0)])
