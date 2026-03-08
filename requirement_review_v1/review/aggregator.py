"""Aggregate multi-role reviewer outputs into unified artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .reviewer_agents.base import ReviewerResult, normalize_severity


@dataclass(frozen=True, slots=True)
class AggregatedReviewArtifacts:
    review_report_json: str
    risk_items_json: str
    open_questions_json: str
    review_summary_md: str


@dataclass(frozen=True, slots=True)
class AggregatedReview:
    findings: tuple[dict[str, Any], ...]
    risk_items: tuple[dict[str, Any], ...]
    open_questions: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    reviewer_summaries: tuple[dict[str, str], ...]
    reviewer_count: int
    artifacts: AggregatedReviewArtifacts

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = asdict(self.artifacts)
        return payload


def aggregate_review_results(
    reviewer_results: Iterable[ReviewerResult],
    output_dir: str | Path,
) -> AggregatedReview:
    results = tuple(reviewer_results)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    findings = _aggregate_findings(results)
    risk_items = _aggregate_risks(results)
    open_questions = _aggregate_open_questions(results)
    conflicts = _detect_conflicts(results)
    reviewer_summaries = tuple(
        {"reviewer": result.reviewer, "summary": result.summary}
        for result in results
        if result.summary
    )

    report_payload = {
        "reviewer_count": len(results),
        "findings": findings,
        "risk_items": risk_items,
        "open_questions": open_questions,
        "conflicts": conflicts,
        "reviewer_summaries": list(reviewer_summaries),
    }

    review_report_path = target_dir / "review_report.json"
    risk_items_path = target_dir / "risk_items.json"
    open_questions_path = target_dir / "open_questions.json"
    summary_path = target_dir / "review_summary.md"

    review_report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    risk_items_path.write_text(json.dumps({"risk_items": risk_items}, ensure_ascii=False, indent=2), encoding="utf-8")
    open_questions_path.write_text(json.dumps({"open_questions": open_questions}, ensure_ascii=False, indent=2), encoding="utf-8")
    summary_path.write_text(_render_summary(report_payload), encoding="utf-8")

    artifacts = AggregatedReviewArtifacts(
        review_report_json=str(review_report_path),
        risk_items_json=str(risk_items_path),
        open_questions_json=str(open_questions_path),
        review_summary_md=str(summary_path),
    )
    return AggregatedReview(
        findings=tuple(findings),
        risk_items=tuple(risk_items),
        open_questions=tuple(open_questions),
        conflicts=tuple(conflicts),
        reviewer_summaries=reviewer_summaries,
        reviewer_count=len(results),
        artifacts=artifacts,
    )


def _aggregate_findings(results: tuple[ReviewerResult, ...]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for finding in result.findings:
            key = _normalize_topic_key(finding.title, finding.detail)
            bucket = merged.setdefault(
                key,
                {
                    "title": finding.title,
                    "detail": finding.detail,
                    "severity": normalize_severity(finding.severity),
                    "category": finding.category,
                    "reviewers": [],
                    "requirement_refs": [],
                },
            )
            bucket["severity"] = _max_severity(bucket["severity"], normalize_severity(finding.severity))
            bucket["reviewers"] = _merge_unique(bucket["reviewers"], [result.reviewer or finding.reviewer])
            bucket["requirement_refs"] = _merge_unique(bucket["requirement_refs"], list(finding.requirement_refs))
    return list(merged.values())


def _aggregate_risks(results: tuple[ReviewerResult, ...]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for risk in result.risk_items:
            key = _normalize_topic_key(risk.title, risk.detail)
            bucket = merged.setdefault(
                key,
                {
                    "title": risk.title,
                    "detail": risk.detail,
                    "severity": normalize_severity(risk.severity),
                    "category": risk.category,
                    "mitigation": risk.mitigation,
                    "reviewers": [],
                },
            )
            bucket["severity"] = _max_severity(bucket["severity"], normalize_severity(risk.severity))
            if risk.mitigation and len(risk.mitigation) > len(str(bucket.get("mitigation", ""))):
                bucket["mitigation"] = risk.mitigation
            bucket["reviewers"] = _merge_unique(bucket["reviewers"], [result.reviewer or risk.reviewer])
    return list(merged.values())


def _aggregate_open_questions(results: tuple[ReviewerResult, ...]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for question in result.open_questions:
            key = _normalize_topic_key(question)
            bucket = merged.setdefault(
                key,
                {
                    "question": question,
                    "reviewers": [],
                },
            )
            bucket["reviewers"] = _merge_unique(bucket["reviewers"], [result.reviewer])
    return list(merged.values())


def _detect_conflicts(results: tuple[ReviewerResult, ...]) -> list[dict[str, Any]]:
    topic_map: dict[str, dict[str, Any]] = {}
    for result in results:
        for finding in result.findings:
            key = _normalize_topic_key(finding.title, finding.detail)
            bucket = topic_map.setdefault(
                key,
                {
                    "topic": finding.title,
                    "finding_severities": set(),
                    "risk_severities": set(),
                },
            )
            bucket["finding_severities"].add(normalize_severity(finding.severity))
        for risk in result.risk_items:
            key = _normalize_topic_key(risk.title, risk.detail)
            bucket = topic_map.setdefault(
                key,
                {
                    "topic": risk.title,
                    "finding_severities": set(),
                    "risk_severities": set(),
                },
            )
            bucket["risk_severities"].add(normalize_severity(risk.severity))

    conflicts: list[dict[str, Any]] = []
    for value in topic_map.values():
        finding_levels = sorted(value["finding_severities"])
        risk_levels = sorted(value["risk_severities"])
        if len(finding_levels) > 1:
            conflicts.append(
                {
                    "topic": value["topic"],
                    "finding_severity": ", ".join(finding_levels),
                    "risk_severity": ", ".join(risk_levels) if risk_levels else "",
                    "status": "severity_mismatch",
                }
            )
            continue
        if finding_levels and risk_levels and finding_levels[0] != risk_levels[0]:
            conflicts.append(
                {
                    "topic": value["topic"],
                    "finding_severity": finding_levels[0],
                    "risk_severity": risk_levels[0],
                    "status": "severity_mismatch",
                }
            )
    return conflicts


def _render_summary(report_payload: dict[str, Any]) -> str:
    findings = report_payload.get("findings", []) if isinstance(report_payload.get("findings"), list) else []
    risk_items = report_payload.get("risk_items", []) if isinstance(report_payload.get("risk_items"), list) else []
    open_questions = report_payload.get("open_questions", []) if isinstance(report_payload.get("open_questions"), list) else []
    conflicts = report_payload.get("conflicts", []) if isinstance(report_payload.get("conflicts"), list) else []
    summaries = report_payload.get("reviewer_summaries", []) if isinstance(report_payload.get("reviewer_summaries"), list) else []

    lines = [
        "# Review Summary",
        "",
        f"- Reviewers: {report_payload.get('reviewer_count', 0)}",
        f"- Findings: {len(findings)}",
        f"- Risk Items: {len(risk_items)}",
        f"- Open Questions: {len(open_questions)}",
        f"- Conflicts: {len(conflicts)}",
        "",
        "## Findings",
        "",
    ]
    lines.extend(_bullet_lines([f"[{item['severity']}] {item['title']}" for item in findings], "No findings."))
    lines.extend([
        "",
        "## Risks",
        "",
    ])
    lines.extend(_bullet_lines([f"[{item['severity']}] {item['title']}" for item in risk_items], "No risk items."))
    lines.extend([
        "",
        "## Open Questions",
        "",
    ])
    lines.extend(_bullet_lines([item["question"] for item in open_questions], "No open questions."))
    lines.extend([
        "",
        "## Reviewer Notes",
        "",
    ])
    lines.extend(
        _bullet_lines(
            [f"{item['reviewer']}: {item['summary']}" for item in summaries if item.get("summary")],
            "No reviewer notes.",
        )
    )
    if conflicts:
        lines.extend([
            "",
            "## Conflicts",
            "",
        ])
        lines.extend(
            _bullet_lines(
                [
                    f"{item['topic']}: finding={item['finding_severity']}, risk={item['risk_severity']}"
                    for item in conflicts
                ],
                "No conflicts.",
            )
        )
    return "\n".join(lines).strip() + "\n"


def _bullet_lines(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [f"- {empty_message}"]
    return [f"- {item}" for item in items]


def _normalize_topic_key(*parts: str) -> str:
    text = " ".join(str(part or "") for part in parts).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    seen = {item for item in merged if item}
    for item in incoming:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        merged.append(value)
    return merged


def _max_severity(left: str, right: str) -> str:
    order = {"low": 0, "medium": 1, "high": 2}
    return left if order.get(left, 1) >= order.get(right, 1) else right
