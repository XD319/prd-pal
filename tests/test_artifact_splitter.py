from __future__ import annotations

from pathlib import Path

from requirement_review_v1.packs.artifact_splitter import ArtifactSplitter


def _review_result() -> dict:
    return {
        "final_report": "# Requirement Review Report\n\nSummary body.",
        "parsed_items": [
            {"id": "REQ-001", "description": "Support OAuth login"},
            {"id": "REQ-002", "description": "Add audit trail"},
        ],
        "review_results": [
            {"id": "REQ-001", "description": "Support OAuth login", "is_ambiguous": True, "issues": ["OAuth provider list is missing"]},
            {"id": "REQ-002", "description": "Add audit trail", "is_ambiguous": False, "issues": []},
        ],
        "tasks": [
            {"id": "TASK-001", "title": "Implement OAuth callback"},
            {"id": "TASK-002", "title": "Add audit log persistence"},
        ],
        "implementation_plan": {
            "target_modules": ["backend.auth", "frontend.login"],
            "implementation_steps": ["Review current login flow", "Implement callback handler"],
            "constraints": ["Preserve existing password login"],
        },
        "test_plan": {
            "test_scope": ["OAuth callback API"],
            "edge_cases": ["Expired OAuth state"],
            "regression_focus": ["Password login"],
        },
    }


def test_artifact_splitter_generates_expected_markdown_files(tmp_path: Path):
    refs = ArtifactSplitter().split(_review_result(), tmp_path)

    assert set(refs) == {
        "prd_review_report",
        "open_questions",
        "scope_boundary",
        "tech_design_draft",
        "test_checklist",
    }
    for ref in refs.values():
        path = Path(ref.path)
        assert path.exists()
        assert path.parent == tmp_path
        assert ref.content_hash

    assert "# PRD Review Report" in (tmp_path / "prd_review_report.md").read_text(encoding="utf-8")
    assert "# Open Questions" in (tmp_path / "open_questions.md").read_text(encoding="utf-8")
    assert "OAuth provider list is missing" in (tmp_path / "open_questions.md").read_text(encoding="utf-8")
    assert "# Scope Boundary" in (tmp_path / "scope_boundary.md").read_text(encoding="utf-8")
    assert "# Technical Design Draft" in (tmp_path / "tech_design_draft.md").read_text(encoding="utf-8")
    assert "# Test Checklist" in (tmp_path / "test_checklist.md").read_text(encoding="utf-8")


def test_artifact_splitter_degrades_gracefully_on_empty_input(tmp_path: Path):
    refs = ArtifactSplitter().split({}, tmp_path)

    assert len(refs) == 5
    assert "No open questions were detected." in (tmp_path / "open_questions.md").read_text(encoding="utf-8")
    assert "No implementation steps were generated." in (tmp_path / "tech_design_draft.md").read_text(encoding="utf-8")


def test_artifact_splitter_returns_correct_paths(tmp_path: Path):
    refs = ArtifactSplitter().split(_review_result(), tmp_path)

    assert refs["prd_review_report"].path == str(tmp_path / "prd_review_report.md")
    assert refs["test_checklist"].path == str(tmp_path / "test_checklist.md")
