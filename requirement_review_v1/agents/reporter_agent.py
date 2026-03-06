"""Reporter agent — LangGraph node that assembles parsed items, review
results, and delivery plan into a human-readable Markdown report.

parsed_items + review_results + tasks/milestones/estimation + plan_review
  →  final_report

V1: no LLM call — the report is built by deterministic string concatenation.
"""

from __future__ import annotations

from typing import Any

from ..metrics import compute_requirement_coverage
from ..state import ReviewState, plan_from_state
from ..utils.trace import trace_start

# ── risk helpers ──────────────────────────────────────────────────────────

_RISK_HIGH = "High"
_RISK_MEDIUM = "Medium"
_RISK_LOW = "Low"


def _risk_level(result: dict) -> str:
    """Derive a risk level from the three boolean review dimensions.

    Flags counted: *not* clear, *not* testable, *is* ambiguous.
    0 flags → Low, 1 → Medium, 2-3 → High.
    """
    flags = sum([
        not result.get("is_clear", True),
        not result.get("is_testable", True),
        result.get("is_ambiguous", False),
    ])
    if flags >= 2:
        return _RISK_HIGH
    if flags == 1:
        return _RISK_MEDIUM
    return _RISK_LOW


_RISK_EMOJI = {_RISK_HIGH: "🔴", _RISK_MEDIUM: "🟡", _RISK_LOW: "🟢"}

# ── markdown builders — requirements ─────────────────────────────────────


def _build_requirement_table(items: list[dict]) -> str:
    rows = ["| ID | Description | Acceptance Criteria |", "|----|-------------|---------------------|"]
    for item in items:
        rid = item.get("id", "-")
        desc = item.get("description", "-")
        criteria = item.get("acceptance_criteria", [])
        criteria_str = "; ".join(criteria) if criteria else "-"
        rows.append(f"| {rid} | {desc} | {criteria_str} |")
    return "\n".join(rows)


def _build_detail_sections(
    items: list[dict],
    results_by_id: dict[str, dict],
) -> str:
    sections: list[str] = []
    for item in items:
        rid = item.get("id", "-")
        desc = item.get("description", "-")
        result = results_by_id.get(rid, {})

        clear = "✅ Yes" if result.get("is_clear", True) else "❌ No"
        testable = "✅ Yes" if result.get("is_testable", True) else "❌ No"
        ambiguous = "❌ Yes" if result.get("is_ambiguous", False) else "✅ No"

        issues = result.get("issues", [])
        issues_str = "\n".join(f"  - {i}" for i in issues) if issues else "  None"

        suggestions = result.get("suggestions", "") or "None"
        risk = _risk_level(result)
        emoji = _RISK_EMOJI[risk]

        sections.append(
            f"### {rid} — {desc}\n"
            f"\n"
            f"- **Clear:** {clear}\n"
            f"- **Testable:** {testable}\n"
            f"- **Ambiguous:** {ambiguous}\n"
            f"- **Issues:**\n{issues_str}\n"
            f"- **Suggestions:** {suggestions}\n"
            f"- **Risk Level:** {emoji} {risk}"
        )
    return "\n\n".join(sections)


def _build_risk_summary(results: list[dict]) -> str:
    counts = {_RISK_HIGH: 0, _RISK_MEDIUM: 0, _RISK_LOW: 0}
    for r in results:
        counts[_risk_level(r)] += 1
    total = len(results) or 1

    rows = ["| Risk Level | Count | Percentage |", "|------------|-------|------------|"]
    for level in (_RISK_HIGH, _RISK_MEDIUM, _RISK_LOW):
        emoji = _RISK_EMOJI[level]
        pct = round(counts[level] / total * 100)
        rows.append(f"| {emoji} {level} | {counts[level]} | {pct}% |")
    return "\n".join(rows)


# ── markdown builders — delivery plan ────────────────────────────────────


def _build_task_table(tasks: list[dict]) -> str:
    rows = [
        "| ID | Title | Owner | Requirement IDs | Dependencies | Est. Days |",
        "|----|-------|-------|-----------------|--------------|-----------|",
    ]
    for t in tasks:
        tid = t.get("id", "-")
        title = t.get("title", "-")
        owner = t.get("owner", "-")
        requirement_ids = ", ".join(t.get("requirement_ids", [])) or "—"
        deps = ", ".join(t.get("depends_on", [])) or "—"
        days = t.get("estimate_days", "-")
        rows.append(f"| {tid} | {title} | {owner} | {requirement_ids} | {deps} | {days} |")
    return "\n".join(rows)


def _build_milestone_table(milestones: list[dict]) -> str:
    rows = [
        "| ID | Title | Tasks | Target Days |",
        "|----|-------|-------|-------------|",
    ]
    for m in milestones:
        mid = m.get("id", "-")
        title = m.get("title", "-")
        includes = ", ".join(m.get("includes", [])) or "—"
        target = m.get("target_days", "-")
        rows.append(f"| {mid} | {title} | {includes} | {target} |")
    return "\n".join(rows)


def _build_estimation_summary(estimation: dict) -> str:
    total = estimation.get("total_days", "?")
    buffer = estimation.get("buffer_days", "?")
    return (
        f"- **Total estimated days:** {total}\n"
        f"- **Buffer days:** {buffer}\n"
        f"- **Grand total:** {total + buffer if isinstance(total, (int, float)) and isinstance(buffer, (int, float)) else '?'}"
    )


def _build_plan_review_section(plan_review: dict) -> str:
    if not plan_review:
        return "_No plan review comments available._"
    lines: list[str] = []
    for key in ("coverage", "milestones", "estimation"):
        comment = plan_review.get(key, "")
        if comment:
            label = key.replace("_", " ").title()
            lines.append(f"- **{label}:** {comment}")
    return "\n".join(lines) if lines else "_No plan review comments available._"


# ── markdown builders — delivery risks ────────────────────────────────────

_IMPACT_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def _md_cell(value: Any) -> str:
    text = str(value if value is not None else "")
    return text.replace("|", "\\|").replace("\n", "<br>")


def _build_risk_register(risks: list[dict]) -> str:
    rows = [
        "| ID | Description | Impact | Mitigation | Buffer Days | Evidence IDs | Evidence |",
        "|----|-------------|--------|------------|-------------|--------------|----------|",
    ]
    for r in risks:
        rid = r.get("id", "-")
        desc = r.get("description", "-")
        impact = r.get("impact", "-")
        emoji = _IMPACT_EMOJI.get(impact, "⚪")
        mitigation = r.get("mitigation", "-")
        buf = r.get("buffer_days", 0)
        evidence_ids = ", ".join(r.get("evidence_ids", [])) or "—"
        evidence_snippets = " / ".join(r.get("evidence_snippets", [])) or "—"
        rows.append(
            f"| {_md_cell(rid)} | {_md_cell(desc)} | {_md_cell(f'{emoji} {impact}')} "
            f"| {_md_cell(mitigation)} | {_md_cell(buf)} | {_md_cell(evidence_ids)} "
            f"| {_md_cell(evidence_snippets)} |"
        )
    return "\n".join(rows)


# ── node function ─────────────────────────────────────────────────────────

_AGENT = "reporter"


async def run(state: ReviewState) -> ReviewState:
    """Assemble *final_report* from all state fields."""
    parsed_items: list[dict] = state.get("parsed_items", [])
    review_results: list[dict] = state.get("review_results", [])
    plan = plan_from_state(state)
    tasks: list[dict] = plan.get("tasks", [])
    milestones: list[dict] = plan.get("milestones", [])
    estimation: dict = plan.get("estimation", {})
    risks: list[dict] = state.get("risks", [])
    plan_review: dict = state.get("plan_review", {})
    trace: dict[str, Any] = dict(state.get("trace", {}))

    input_chars = sum(len(str(v)) for v in (
        parsed_items, review_results, tasks, milestones, estimation,
        risks, plan_review,
    ))
    span = trace_start(_AGENT, model="none", input_chars=input_chars)

    results_by_id = {r["id"]: r for r in review_results if "id" in r}
    metrics = compute_requirement_coverage(parsed_items, tasks)

    parts: list[str] = ["# Requirement Review Report\n"]
    ratio = metrics.get("coverage_ratio", 0.0)
    req_to_tasks = metrics.get("requirement_to_tasks", {})
    uncovered = metrics.get("uncovered_requirements", [])

    covered_count = sum(1 for task_ids in req_to_tasks.values() if task_ids)
    total_count = len(req_to_tasks)
    parts.append(
        f"**Coverage:** {ratio:.2%} ({covered_count}/{total_count} requirements covered)"
    )
    if uncovered:
        parts.append(f"**Uncovered:** {', '.join(uncovered)}")
    parts.append("")

    # Section 1 — requirement list
    parts.append("## 1. Requirement List\n")
    if parsed_items:
        parts.append(_build_requirement_table(parsed_items))
    else:
        parts.append("_No requirement items were parsed._")

    # Section 2 — per-item review
    parts.append("\n## 2. Review Details\n")
    if parsed_items and review_results:
        parts.append(_build_detail_sections(parsed_items, results_by_id))
    else:
        parts.append("_No review results available._")

    # Section 3 — requirement quality risk summary
    parts.append("\n## 3. Risk Summary\n")
    if review_results:
        parts.append(_build_risk_summary(review_results))
    else:
        parts.append("_No review results to summarize._")

    # Section 4 — delivery plan
    parts.append("\n## 4. Delivery Plan\n")

    parts.append("### 4.1 Task Breakdown\n")
    if tasks:
        parts.append(_build_task_table(tasks))
    else:
        parts.append("_No tasks generated._")

    parts.append("\n### 4.2 Milestones\n")
    if milestones:
        parts.append(_build_milestone_table(milestones))
    else:
        parts.append("_No milestones generated._")

    parts.append("\n### 4.3 Estimation\n")
    if estimation:
        parts.append(_build_estimation_summary(estimation))
    else:
        parts.append("_No estimation available._")

    # Section 5 — delivery risk register
    parts.append("\n## 5. Delivery Risk Register\n")
    if risks:
        parts.append(_build_risk_register(risks))
    else:
        parts.append("_No delivery risks identified._")

    # Section 6 — plan review
    parts.append("\n## 6. Plan Review\n")
    parts.append(_build_plan_review_section(plan_review))

    final_report = "\n".join(parts) + "\n"

    trace[_AGENT] = span.end(status="ok", output_chars=len(final_report))

    return {"final_report": final_report, "metrics": metrics, "trace": trace}
