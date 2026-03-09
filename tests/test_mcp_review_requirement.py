from __future__ import annotations

import json

import pytest

from requirement_review_v1.service import review_service
from requirement_review_v1.service.review_service import ReviewResultSummary


@pytest.mark.asyncio
async def test_review_requirement_for_mcp_async_prefers_parallel_review_payload(tmp_path, monkeypatch):
    run_id = "20260309T010203Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    report_json_path = run_dir / "report.json"
    run_trace_path = run_dir / "run_trace.json"
    review_result_json_path = run_dir / "review_result.json"

    report_payload = {
        "review_mode": "parallel_review",
        "parallel-review_meta": {
            "selected_mode": "parallel_review",
            "review_mode": "parallel_review",
            "artifact_paths": {"review_result_json": str(review_result_json_path)},
        },
        "parallel_review": {
            "findings": [
                {
                    "finding_id": "finding-123",
                    "title": "Security review gate required",
                    "detail": "Sensitive export path lacks owner sign-off.",
                    "severity": "high",
                    "category": "security",
                    "reviewers": ["security"],
                }
            ],
            "open_questions": [
                {
                    "question": "Who approves the export flow before release?",
                    "reviewers": ["product"],
                }
            ],
            "risk_items": [
                {
                    "title": "Security review gate required",
                    "detail": "Sensitive export path lacks owner sign-off.",
                    "severity": "high",
                    "category": "security",
                    "mitigation": "Assign an approver before release.",
                }
            ],
            "conflicts": [
                {
                    "conflict_id": "conflict-123",
                    "type": "release_ok_vs_approval_blocker",
                    "summary": "Release readiness conflicts with missing approval gate.",
                }
            ],
            "artifacts": {"review_result_json": str(review_result_json_path)},
        },
    }
    report_json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    run_trace_path.write_text("{}", encoding="utf-8")
    review_result_json_path.write_text(json.dumps({"ok": True}, ensure_ascii=False, indent=2), encoding="utf-8")

    fixed = ReviewResultSummary(
        run_id=run_id,
        report_md_path=str(run_dir / "report.md"),
        report_json_path=str(report_json_path),
        high_risk_ratio=0.5,
        coverage_ratio=0.8,
        revision_round=1,
        status="completed",
        run_trace_path=str(run_trace_path),
    )

    async def fake_review_prd_text_async(
        prd_text: str | None = None,
        *,
        prd_path: str | None = None,
        source: str | None = None,
        run_id: str | None = None,
        config_overrides: dict[str, object] | None = None,
    ) -> ReviewResultSummary:
        assert prd_text == "Complex export PRD"
        assert prd_path is None
        assert source is None
        assert run_id is None
        assert isinstance(config_overrides, dict)
        return fixed

    monkeypatch.setattr(review_service, "review_prd_text_async", fake_review_prd_text_async)

    result = await review_service.review_requirement_for_mcp_async(
        prd_text="Complex export PRD",
        prd_path=None,
        source=None,
        options={"outputs_root": str(tmp_path), "review_mode_override": "parallel_review"},
    )

    assert result["review_id"] == run_id
    assert result["run_id"] == run_id
    assert result["review_mode"] == "parallel_review"
    assert result["report_path"] == str(review_result_json_path)
    assert result["findings"][0]["finding_id"] == "finding-123"
    assert result["open_questions"][0]["question"].startswith("Who approves")
    assert result["risk_items"][0]["mitigation"] == "Assign an approver before release."
    assert result["conflicts"][0]["conflict_id"] == "conflict-123"

