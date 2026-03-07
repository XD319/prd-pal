"""Split the combined review output into standalone delivery artifacts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from requirement_review_v1.packs.delivery_bundle import ArtifactRef


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _md_bullets(items: list[str], empty_message: str) -> list[str]:
    if not items:
        return [f"- {empty_message}"]
    return [f"- {item}" for item in items]


class ArtifactSplitter:
    """Split review outputs into independent markdown artifacts."""

    FILE_MAP = {
        "prd_review_report": "prd_review_report.md",
        "open_questions": "open_questions.md",
        "scope_boundary": "scope_boundary.md",
        "tech_design_draft": "tech_design_draft.md",
        "test_checklist": "test_checklist.md",
    }

    def split(self, review_result: dict[str, Any], run_dir: Path) -> dict[str, ArtifactRef]:
        run_dir.mkdir(parents=True, exist_ok=True)
        generated_at = _utc_now_iso()
        artifacts = {
            "prd_review_report": self._build_prd_review_report(review_result),
            "open_questions": self._build_open_questions(review_result),
            "scope_boundary": self._build_scope_boundary(review_result),
            "tech_design_draft": self._build_tech_design_draft(review_result),
            "test_checklist": self._build_test_checklist(review_result),
        }

        refs: dict[str, ArtifactRef] = {}
        for artifact_type, content in artifacts.items():
            path = run_dir / self.FILE_MAP[artifact_type]
            path.write_text(content, encoding="utf-8")
            refs[artifact_type] = ArtifactRef(
                artifact_type=artifact_type,
                path=str(path),
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                generated_at=generated_at,
            )
        return refs

    def _build_prd_review_report(self, review_result: dict[str, Any]) -> str:
        final_report = str(review_result.get("final_report", "") or "").strip()
        lines = [
            "# PRD Review Report",
            "",
            "Source: `result.final_report` from the review workflow.",
            "",
        ]
        if final_report:
            lines.append(final_report)
        else:
            lines.append("_No final report was generated. Use `report.md` as the fallback source._")
        return "\n".join(lines).strip() + "\n"

    def _build_open_questions(self, review_result: dict[str, Any]) -> str:
        review_results = _as_list(review_result.get("review_results"))
        open_items: list[str] = []
        for item in review_results:
            if not isinstance(item, dict):
                continue
            issues = [str(issue) for issue in _as_list(item.get("issues")) if str(issue).strip()]
            if item.get("is_ambiguous") or issues:
                question = str(item.get("description") or item.get("summary") or item.get("id") or "Unknown item")
                open_items.append(f"`{item.get('id', 'unknown')}` {question}")
                open_items.extend([f"  - {issue}" for issue in issues] or ["  - Clarify requirement intent and acceptance criteria."])

        lines = [
            "# Open Questions",
            "",
            "Source: `result.review_results` items marked ambiguous or carrying issues.",
            "",
            "## Questions",
            "",
            *_md_bullets(open_items, "No open questions were detected."),
        ]
        return "\n".join(lines).strip() + "\n"

    def _build_scope_boundary(self, review_result: dict[str, Any]) -> str:
        parsed_items = _as_list(review_result.get("parsed_items"))
        tasks = _as_list(review_result.get("tasks"))
        in_scope = [f"`{item.get('id', 'unknown')}` {item.get('description', '')}".strip() for item in parsed_items if isinstance(item, dict)]
        task_titles = [f"`{task.get('id', 'unknown')}` {task.get('title', '')}".strip() for task in tasks if isinstance(task, dict)]

        lines = [
            "# Scope Boundary",
            "",
            "Source: `result.parsed_items` and `result.tasks`.",
            "",
            "## In Scope Requirements",
            "",
            *_md_bullets(in_scope, "No parsed requirement items were available."),
            "",
            "## Planned Delivery Tasks",
            "",
            *_md_bullets(task_titles, "No delivery tasks were generated."),
            "",
            "## Out of Scope / Pending Clarification",
            "",
            "- Any work not mapped to the reviewed requirements should be treated as out of scope until approved.",
        ]
        return "\n".join(lines).strip() + "\n"

    def _build_tech_design_draft(self, review_result: dict[str, Any]) -> str:
        implementation_plan = _as_dict(review_result.get("implementation_plan"))
        tasks = _as_list(review_result.get("tasks"))
        lines = [
            "# Technical Design Draft",
            "",
            "Source: `result.implementation_plan` and `result.tasks`.",
            "",
            "## Target Modules",
            "",
            *_md_bullets([str(item) for item in _as_list(implementation_plan.get("target_modules"))], "No target modules were generated."),
            "",
            "## Proposed Implementation Steps",
            "",
            *_md_bullets([str(item) for item in _as_list(implementation_plan.get("implementation_steps"))], "No implementation steps were generated."),
            "",
            "## Constraints",
            "",
            *_md_bullets([str(item) for item in _as_list(implementation_plan.get("constraints"))], "No explicit implementation constraints were generated."),
            "",
            "## Delivery Tasks",
            "",
            *_md_bullets(
                [f"`{task.get('id', 'unknown')}` {task.get('title', '')}".strip() for task in tasks if isinstance(task, dict)],
                "No delivery tasks were generated.",
            ),
        ]
        return "\n".join(lines).strip() + "\n"

    def _build_test_checklist(self, review_result: dict[str, Any]) -> str:
        test_plan = _as_dict(review_result.get("test_plan"))
        review_results = _as_list(review_result.get("review_results"))
        issue_checks = [
            f"Resolve review issue for `{item.get('id', 'unknown')}`: {issue}"
            for item in review_results
            if isinstance(item, dict)
            for issue in [str(i) for i in _as_list(item.get("issues")) if str(i).strip()]
        ]
        lines = [
            "# Test Checklist",
            "",
            "Source: `result.test_plan` and unresolved review issues.",
            "",
            "## Test Scope",
            "",
            *_md_bullets([str(item) for item in _as_list(test_plan.get("test_scope"))], "No test scope was generated."),
            "",
            "## Edge Cases",
            "",
            *_md_bullets([str(item) for item in _as_list(test_plan.get("edge_cases"))], "No edge cases were generated."),
            "",
            "## Regression Focus",
            "",
            *_md_bullets([str(item) for item in _as_list(test_plan.get("regression_focus"))], "No regression focus was generated."),
            "",
            "## Review-Driven Checks",
            "",
            *_md_bullets(issue_checks, "No extra review-driven checks were required."),
        ]
        return "\n".join(lines).strip() + "\n"
