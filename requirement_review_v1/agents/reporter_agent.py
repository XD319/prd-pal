"""Reporter agent — LangGraph node that assembles parsed items and review
results into a human-readable Markdown report.

parsed_items + review_results  →  final_report

V1: no LLM call — the report is built by deterministic string concatenation.
"""

from __future__ import annotations

import time
from typing import Any

from ..state import ReviewState

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

# ── markdown builders ─────────────────────────────────────────────────────


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


# ── node function ─────────────────────────────────────────────────────────


async def run(state: ReviewState) -> ReviewState:
    """Assemble *final_report* from *parsed_items* and *review_results*."""
    start = time.time()
    parsed_items: list[dict] = state.get("parsed_items", [])
    review_results: list[dict] = state.get("review_results", [])
    trace: dict[str, Any] = dict(state.get("trace", {}))

    results_by_id = {r["id"]: r for r in review_results if "id" in r}

    parts: list[str] = ["# Requirement Review Report\n"]

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

    # Section 3 — risk summary
    parts.append("\n## 3. Risk Summary\n")
    if review_results:
        parts.append(_build_risk_summary(review_results))
    else:
        parts.append("_No review results to summarize._")

    final_report = "\n".join(parts) + "\n"

    elapsed = round(time.time() - start, 3)
    trace["reporter"] = {
        "elapsed_seconds": elapsed,
        "report_length": len(final_report),
    }

    return {"final_report": final_report, "trace": trace}
