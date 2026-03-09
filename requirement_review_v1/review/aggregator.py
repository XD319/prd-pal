"""Aggregate multi-role reviewer outputs into unified artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .reviewer_agents.base import ReviewFinding, ReviewerResult, normalize_severity


@dataclass(frozen=True, slots=True)
class AggregatedReviewArtifacts:
    review_result_json: str
    review_report_md: str
    risk_items_json: str
    open_questions_json: str
    review_report_json: str
    review_summary_md: str


@dataclass(frozen=True, slots=True)
class AggregatedReview:
    findings: tuple[dict[str, Any], ...]
    risk_items: tuple[dict[str, Any], ...]
    open_questions: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    reviewer_summaries: tuple[dict[str, str], ...]
    partial_review: bool
    reviewers_completed: tuple[str, ...]
    reviewers_failed: tuple[dict[str, str], ...]
    reviewer_count: int
    meta: dict[str, Any]
    artifacts: AggregatedReviewArtifacts

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["artifacts"] = asdict(self.artifacts)
        payload["meta"] = dict(self.meta)
        return payload


def aggregate_review_results(
    reviewer_results: Iterable[ReviewerResult],
    output_dir: str | Path,
) -> AggregatedReview:
    results = tuple(reviewer_results)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    meta = _build_review_meta(results)
    findings = _aggregate_findings(results)
    risk_items = _aggregate_risks(results)
    open_questions = _aggregate_open_questions(results)
    conflicts = _detect_conflicts(results)
    reviewer_summaries = tuple(
        {"reviewer": result.reviewer, "summary": result.summary}
        for result in results
        if result.summary
    )
    partial_review = bool(meta.get("partial_review", False))
    reviewers_completed = list(meta.get("reviewers_completed", []) or [])
    reviewers_failed = list(meta.get("reviewers_failed", []) or [])
    manual_review_message = _build_manual_review_message(
        partial_review=partial_review,
        reviewers_failed=reviewers_failed,
        findings=findings,
        risk_items=risk_items,
    )
    meta = {
        **meta,
        "manual_review_required": bool(manual_review_message),
        "manual_review_message": manual_review_message,
    }

    report_payload = {
        "reviewer_count": len(results),
        "partial_review": partial_review,
        "reviewers_completed": reviewers_completed,
        "reviewers_failed": reviewers_failed,
        "manual_review_required": bool(manual_review_message),
        "manual_review_message": manual_review_message,
        "meta": meta,
        "findings": findings,
        "risk_items": risk_items,
        "open_questions": open_questions,
        "conflicts": conflicts,
        "reviewer_summaries": list(reviewer_summaries),
    }

    review_result_path = target_dir / "review_result.json"
    review_report_path = target_dir / "review_report.md"
    legacy_review_report_path = target_dir / "review_report.json"
    risk_items_path = target_dir / "risk_items.json"
    open_questions_path = target_dir / "open_questions.json"
    legacy_summary_path = target_dir / "review_summary.md"

    report_json = json.dumps(report_payload, ensure_ascii=False, indent=2)
    review_result_path.write_text(report_json, encoding="utf-8")
    legacy_review_report_path.write_text(report_json, encoding="utf-8")
    risk_items_path.write_text(json.dumps({"risk_items": risk_items}, ensure_ascii=False, indent=2), encoding="utf-8")
    open_questions_path.write_text(json.dumps({"open_questions": open_questions}, ensure_ascii=False, indent=2), encoding="utf-8")
    review_report_path.write_text(_render_review_report(report_payload), encoding="utf-8")
    legacy_summary_path.write_text(_render_summary(report_payload), encoding="utf-8")

    artifacts = AggregatedReviewArtifacts(
        review_result_json=str(review_result_path),
        review_report_md=str(review_report_path),
        risk_items_json=str(risk_items_path),
        open_questions_json=str(open_questions_path),
        review_report_json=str(legacy_review_report_path),
        review_summary_md=str(legacy_summary_path),
    )
    return AggregatedReview(
        findings=tuple(findings),
        risk_items=tuple(risk_items),
        open_questions=tuple(open_questions),
        conflicts=tuple(conflicts),
        reviewer_summaries=reviewer_summaries,
        partial_review=partial_review,
        reviewers_completed=tuple(reviewers_completed),
        reviewers_failed=tuple(reviewers_failed),
        reviewer_count=len(results),
        meta=meta,
        artifacts=artifacts,
    )


def _build_review_meta(results: tuple[ReviewerResult, ...]) -> dict[str, Any]:
    reviewers_completed: list[str] = []
    reviewers_failed: list[dict[str, str]] = []

    for result in results:
        reviewer = str(result.reviewer or "").strip()
        if not reviewer:
            continue
        status = str(result.status or "completed").strip().lower() or "completed"
        if status in {"completed", "ok", "success"}:
            reviewers_completed = _merge_unique(reviewers_completed, [reviewer])
            continue
        reviewers_failed.append(
            {
                "reviewer": reviewer,
                "status": status,
                "reason": str(result.error_message or "").strip(),
            }
        )

    return {
        "review_mode": "parallel_review",
        "partial_review": bool(reviewers_failed),
        "reviewers_completed": reviewers_completed,
        "reviewers_failed": reviewers_failed,
    }


def _aggregate_findings(results: tuple[ReviewerResult, ...]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for result in results:
        for finding in result.findings:
            key = _normalize_topic_key(finding.category, finding.title, finding.detail)
            source_reviewer = _resolve_source_reviewer(result.reviewer, finding.reviewer)
            default_suggested_action = _resolve_suggested_action(finding)
            default_assignee = _resolve_assignee(finding, source_reviewer)
            bucket = merged.setdefault(
                key,
                {
                    "finding_id": _build_finding_id(finding.category, finding.title, finding.detail),
                    "title": finding.title,
                    "detail": finding.detail,
                    "description": finding.detail,
                    "severity": normalize_severity(finding.severity),
                    "category": finding.category,
                    "source_reviewer": source_reviewer,
                    "suggested_action": str(finding.suggested_action or "").strip() or default_suggested_action,
                    "assignee": str(finding.assignee or "").strip() or default_assignee,
                    "reviewers": [],
                    "requirement_refs": [],
                },
            )
            bucket["severity"] = _max_severity(bucket["severity"], normalize_severity(finding.severity))
            bucket["reviewers"] = _merge_unique(bucket["reviewers"], [source_reviewer])
            bucket["requirement_refs"] = _merge_unique(bucket["requirement_refs"], list(finding.requirement_refs))
            incoming_action = str(finding.suggested_action or "").strip() or default_suggested_action
            if len(incoming_action) > len(str(bucket.get("suggested_action", ""))):
                bucket["suggested_action"] = incoming_action
            if not str(bucket.get("assignee", "")).strip():
                bucket["assignee"] = str(finding.assignee or "").strip() or default_assignee
            if not str(bucket.get("source_reviewer", "")).strip():
                bucket["source_reviewer"] = source_reviewer
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


def _render_review_report(report_payload: dict[str, Any]) -> str:
    findings = report_payload.get("findings", []) if isinstance(report_payload.get("findings"), list) else []
    risk_items = report_payload.get("risk_items", []) if isinstance(report_payload.get("risk_items"), list) else []
    open_questions = report_payload.get("open_questions", []) if isinstance(report_payload.get("open_questions"), list) else []
    conflicts = report_payload.get("conflicts", []) if isinstance(report_payload.get("conflicts"), list) else []
    summaries = report_payload.get("reviewer_summaries", []) if isinstance(report_payload.get("reviewer_summaries"), list) else []
    meta = report_payload.get("meta", {}) if isinstance(report_payload.get("meta"), dict) else {}

    completed = ", ".join(meta.get("reviewers_completed", []) or []) or "none"
    failed = _format_failed_reviewers(meta.get("reviewers_failed", []))
    manual_review_message = str(meta.get("manual_review_message", "") or "").strip()
    lines = [
        "# Review Report",
        "",
        "## Meta",
        "",
        f"- Review mode: {meta.get('review_mode', 'parallel_review')}",
        f"- Partial review: {'yes' if meta.get('partial_review') else 'no'}",
        f"- Reviewers completed: {completed}",
        f"- Reviewers failed: {failed}",
        f"- Findings: {len(findings)}",
        f"- Risk Items: {len(risk_items)}",
        f"- Open Questions: {len(open_questions)}",
        f"- Conflicts: {len(conflicts)}",
    ]
    if manual_review_message:
        lines.extend([
            f"- Follow-up: {manual_review_message}",
        ])
    lines.extend([
        "",
        "## Findings",
        "",
    ])
    lines.extend(_finding_lines(findings))
    lines.extend([
        "",
        "## Risks",
        "",
    ])
    lines.extend(_bullet_lines([f"[{item['severity']}] {item['title']} -> {item.get('mitigation', '')}".strip() for item in risk_items], "No risk items."))
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


def _render_summary(report_payload: dict[str, Any]) -> str:
    findings = report_payload.get("findings", []) if isinstance(report_payload.get("findings"), list) else []
    risk_items = report_payload.get("risk_items", []) if isinstance(report_payload.get("risk_items"), list) else []
    open_questions = report_payload.get("open_questions", []) if isinstance(report_payload.get("open_questions"), list) else []
    conflicts = report_payload.get("conflicts", []) if isinstance(report_payload.get("conflicts"), list) else []
    summaries = report_payload.get("reviewer_summaries", []) if isinstance(report_payload.get("reviewer_summaries"), list) else []
    meta = report_payload.get("meta", {}) if isinstance(report_payload.get("meta"), dict) else {}

    manual_review_message = str(meta.get("manual_review_message", "") or "").strip()
    lines = [
        "# Review Summary",
        "",
        f"- Review mode: {meta.get('review_mode', 'parallel_review')}",
        f"- Reviewers: {report_payload.get('reviewer_count', 0)}",
        f"- Partial review: {'yes' if meta.get('partial_review') else 'no'}",
        f"- Findings: {len(findings)}",
        f"- Risk Items: {len(risk_items)}",
        f"- Open Questions: {len(open_questions)}",
        f"- Conflicts: {len(conflicts)}",
    ]
    if manual_review_message:
        lines.extend([
            f"- Follow-up: {manual_review_message}",
        ])
    lines.extend([
        "",
        "## Findings",
        "",
    ])
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


def _finding_lines(items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["- No findings."]

    lines: list[str] = []
    for item in items:
        source_reviewer = str(item.get("source_reviewer", "") or "unknown")
        lines.extend(
            [
                f"- [{item.get('severity', 'medium')}] {item.get('finding_id', 'finding')} {item.get('title', 'Finding')}",
                f"  - Description: {item.get('description', item.get('detail', ''))}",
                f"  - Category: {item.get('category', 'general')}",
                f"  - Source reviewer: {source_reviewer}",
                f"  - Suggested action: {item.get('suggested_action', '') or 'Clarify the requirement and define an owner.'}",
                f"  - Assignee: {item.get('assignee', '') or source_reviewer}",
            ]
        )
    return lines


def _format_failed_reviewers(items: Any) -> str:
    if not isinstance(items, list) or not items:
        return "none"

    parts: list[str] = []
    for item in items:
        if isinstance(item, dict):
            reviewer = str(item.get("reviewer", "") or "unknown")
            status = str(item.get("status", "failed") or "failed")
            reason = str(item.get("reason", "") or "").strip()
            if reason:
                parts.append(f"{reviewer} ({status}: {reason})")
            else:
                parts.append(f"{reviewer} ({status})")
        else:
            parts.append(str(item))
    return ", ".join(parts) or "none"


def _build_manual_review_message(
    *,
    partial_review: bool,
    reviewers_failed: list[dict[str, str]],
    findings: list[dict[str, Any]],
    risk_items: list[dict[str, Any]],
) -> str:
    if not partial_review or not reviewers_failed:
        return ""

    has_high_risk = any(
        str(item.get("severity", "")).strip().lower() == "high"
        for item in [*findings, *risk_items]
        if isinstance(item, dict)
    )
    if not has_high_risk:
        return ""

    failed_reviewers = _format_failed_reviewers(reviewers_failed)
    return f"需人工补审：存在高风险问题，且以下 reviewer 缺失或失败：{failed_reviewers}"


def _build_finding_id(category: str, title: str, detail: str) -> str:
    normalized = _normalize_topic_key(category, title, detail)
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"finding-{digest}"


def _resolve_source_reviewer(result_reviewer: str, finding_reviewer: str) -> str:
    reviewer = str(result_reviewer or finding_reviewer or "").strip()
    return reviewer or "unknown"


def _resolve_suggested_action(finding: ReviewFinding) -> str:
    explicit = str(finding.suggested_action or "").strip()
    if explicit:
        return explicit

    category = str(finding.category or "").strip().lower()
    suggestions = {
        "scope": "Add concrete user scenarios and business flows to the PRD before implementation starts.",
        "acceptance": "Add explicit, testable acceptance criteria that product and QA can sign off on.",
        "architecture": "Document impacted modules, integration boundaries, and ownership before build starts.",
        "testability": "Expand pass/fail criteria and edge-case coverage so QA can validate the requirement.",
        "security": "Add explicit security, compliance, and release-control expectations to the PRD.",
    }
    return suggestions.get(category, "Clarify the finding and capture a concrete follow-up action in the PRD.")


def _resolve_assignee(finding: ReviewFinding, source_reviewer: str) -> str:
    explicit = str(finding.assignee or "").strip()
    if explicit:
        return explicit

    category = str(finding.category or "").strip().lower()
    default_assignees = {
        "scope": "product",
        "acceptance": "product",
        "architecture": "engineering",
        "integration": "engineering",
        "testability": "qa",
        "quality": "qa",
        "security": "security",
    }
    return default_assignees.get(category, str(source_reviewer or "product").strip() or "product")


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
