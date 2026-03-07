from __future__ import annotations

import json

import pytest

from requirement_review_v1.mcp_server import server as mcp_server
from requirement_review_v1.service import review_service
from requirement_review_v1.service.review_service import ReviewResultSummary


@pytest.mark.asyncio
async def test_review_prd_routes_to_review_service_with_mock(monkeypatch):
    fixed = ReviewResultSummary(
        run_id="20260304T120000Z",
        report_md_path="outputs/20260304T120000Z/report.md",
        report_json_path="outputs/20260304T120000Z/report.json",
        high_risk_ratio=0.25,
        coverage_ratio=0.8,
        revision_round=1,
        status="completed",
        run_trace_path="outputs/20260304T120000Z/run_trace.json",
        delivery_bundle_path="outputs/20260304T120000Z/delivery_bundle.json",
    )

    async def fake_review_prd_text_async(
        prd_text: str,
        *,
        run_id: str | None = None,
        config_overrides: dict[str, object] | None = None,
    ) -> ReviewResultSummary:
        assert prd_text == "mock prd"
        assert run_id is None
        assert isinstance(config_overrides, dict)
        return fixed

    monkeypatch.setattr(review_service, "review_prd_text", lambda *args, **kwargs: fixed)
    monkeypatch.setattr(review_service, "review_prd_text_async", fake_review_prd_text_async)

    result = await mcp_server.review_prd(prd_text="mock prd")

    assert "error" not in result
    assert result["run_id"] == fixed.run_id
    assert result["status"] == "completed"
    assert result["metrics"]["coverage_ratio"] == fixed.coverage_ratio
    assert result["metrics"]["high_risk_ratio"] == fixed.high_risk_ratio
    assert result["metrics"]["revision_round"] == fixed.revision_round
    assert result["artifacts"]["report_md_path"] == fixed.report_md_path
    assert result["artifacts"]["report_json_path"] == fixed.report_json_path
    assert result["artifacts"]["trace_path"] == fixed.run_trace_path
    assert result["artifacts"]["delivery_bundle_path"] == fixed.delivery_bundle_path


@pytest.mark.asyncio
async def test_review_prd_rejects_missing_prd_text_and_path():
    result = await mcp_server.review_prd()

    assert result["status"] == "failed"
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_review_prd_rejects_both_prd_text_and_path():
    result = await mcp_server.review_prd(prd_text="text", prd_path="docs/sample_prd.md")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_review_prd_rejects_invalid_prd_path():
    result = await mcp_server.review_prd(prd_path="docs/not_exists_prd.md")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "PRD_NOT_FOUND"


def test_get_report_rejects_invalid_run_id_via_tool_handler(tmp_path):
    result = mcp_server.get_report(run_id="../escape", options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "invalid_run_id"


def test_get_report_returns_not_found_via_tool_handler(tmp_path):
    result = mcp_server.get_report(run_id="20260304T010203Z", options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "not_found"


@pytest.mark.asyncio
async def test_generate_delivery_bundle_success(tmp_path):
    run_id = "20260304T010203Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    report_payload = {
        "final_report": "# Report\n\nSummary.",
        "parsed_items": [{"id": "REQ-001", "description": "Support login", "acceptance_criteria": []}],
        "review_results": [{"id": "REQ-001", "description": "Support login", "is_ambiguous": True, "issues": ["Clarify SSO provider"]}],
        "tasks": [{"id": "TASK-001", "title": "Implement login"}],
        "implementation_plan": {"target_modules": ["backend.auth"], "implementation_steps": ["Implement login"], "constraints": []},
        "test_plan": {"test_scope": ["Login API"], "edge_cases": [], "regression_focus": []},
        "trace": {},
    }
    (run_dir / "report.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "report.md").write_text("# Report", encoding="utf-8")
    for filename in ("implementation_pack.json", "test_pack.json", "execution_pack.json"):
        (run_dir / filename).write_text("{}", encoding="utf-8")

    result = await mcp_server.generate_delivery_bundle(run_id=run_id, options={"outputs_root": str(tmp_path)})

    assert "error" not in result
    assert result["bundle_id"] == f"bundle-{run_id}"
    assert result["status"] == "draft"
    assert (run_dir / "delivery_bundle.json").exists()


@pytest.mark.asyncio
async def test_generate_delivery_bundle_missing_run_returns_error(tmp_path):
    result = await mcp_server.generate_delivery_bundle(run_id="20260304T010203Z", options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "not_found"


def test_approve_handoff_success(tmp_path):
    run_id = "20260304T010204Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    bundle_payload = {
        "bundle_id": f"bundle-{run_id}",
        "bundle_version": "1.0",
        "created_at": "2026-03-07T12:00:00+00:00",
        "status": "draft",
        "source_run_id": run_id,
        "artifacts": {
            "prd_review_report": {"artifact_type": "prd_review_report", "path": str(run_dir / "prd_review_report.md")},
            "open_questions": {"artifact_type": "open_questions", "path": str(run_dir / "open_questions.md")},
            "scope_boundary": {"artifact_type": "scope_boundary", "path": str(run_dir / "scope_boundary.md")},
            "tech_design_draft": {"artifact_type": "tech_design_draft", "path": str(run_dir / "tech_design_draft.md")},
            "test_checklist": {"artifact_type": "test_checklist", "path": str(run_dir / "test_checklist.md")},
            "implementation_pack": {"artifact_type": "implementation_pack", "path": str(run_dir / "implementation_pack.json")},
            "test_pack": {"artifact_type": "test_pack", "path": str(run_dir / "test_pack.json")},
            "execution_pack": {"artifact_type": "execution_pack", "path": str(run_dir / "execution_pack.json")},
        },
        "approval_history": [],
        "metadata": {},
    }
    (run_dir / "delivery_bundle.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = mcp_server.approve_handoff(
        bundle_id=f"bundle-{run_id}",
        action="approve",
        reviewer="alice",
        comment="Ready",
        options={"outputs_root": str(tmp_path)},
    )

    assert "error" not in result
    assert result["status"] == "approved"
    assert len(result["approval_history"]) == 1


def test_approve_handoff_invalid_transition_returns_error(tmp_path):
    run_id = "20260304T010205Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    bundle_payload = {
        "bundle_id": f"bundle-{run_id}",
        "bundle_version": "1.0",
        "created_at": "2026-03-07T12:00:00+00:00",
        "status": "approved",
        "source_run_id": run_id,
        "artifacts": {
            "prd_review_report": {"artifact_type": "prd_review_report", "path": str(run_dir / "prd_review_report.md")},
            "open_questions": {"artifact_type": "open_questions", "path": str(run_dir / "open_questions.md")},
            "scope_boundary": {"artifact_type": "scope_boundary", "path": str(run_dir / "scope_boundary.md")},
            "tech_design_draft": {"artifact_type": "tech_design_draft", "path": str(run_dir / "tech_design_draft.md")},
            "test_checklist": {"artifact_type": "test_checklist", "path": str(run_dir / "test_checklist.md")},
            "implementation_pack": {"artifact_type": "implementation_pack", "path": str(run_dir / "implementation_pack.json")},
            "test_pack": {"artifact_type": "test_pack", "path": str(run_dir / "test_pack.json")},
            "execution_pack": {"artifact_type": "execution_pack", "path": str(run_dir / "execution_pack.json")},
        },
        "approval_history": [],
        "metadata": {},
    }
    (run_dir / "delivery_bundle.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    result = mcp_server.approve_handoff(
        bundle_id=f"bundle-{run_id}",
        action="reset_to_draft",
        reviewer="alice",
        comment="Reopen",
        options={"outputs_root": str(tmp_path)},
    )

    assert result["error"]["code"] == "invalid_input"
