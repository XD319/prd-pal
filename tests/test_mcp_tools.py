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
        prd_text: str | None = None,
        *,
        prd_path: str | None = None,
        source: str | None = None,
        run_id: str | None = None,
        config_overrides: dict[str, object] | None = None,
    ) -> ReviewResultSummary:
        assert prd_text == "mock prd"
        assert prd_path is None
        assert source is None
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


@pytest.mark.asyncio
async def test_review_prd_supports_local_source_and_persists_source_metadata(tmp_path, monkeypatch):
    source_path = tmp_path / "sample_prd.md"
    source_path.write_text("# Campus Recruitment PRD\n\nEnable recruiter login.", encoding="utf-8")
    fixed_run_id = "20260308T010203Z"

    async def fake_run_review(
        requirement_doc: str,
        *,
        run_id: str | None = None,
        outputs_root: str | None = None,
        progress_hook=None,
    ) -> dict[str, object]:
        assert requirement_doc == source_path.read_text(encoding="utf-8")
        assert str(outputs_root) == str(tmp_path)
        assert progress_hook is None

        resolved_run_id = run_id or fixed_run_id
        run_dir = tmp_path / resolved_run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        result = {
            "final_report": "# Requirement Review Report\n\nSummary.",
            "parsed_items": [
                {
                    "id": "REQ-001",
                    "description": "Enable recruiter login",
                    "acceptance_criteria": ["Login succeeds"],
                }
            ],
            "review_results": [
                {
                    "id": "REQ-001",
                    "description": "Enable recruiter login",
                    "is_ambiguous": False,
                    "issues": [],
                }
            ],
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Implement recruiter login",
                    "owner": "BE",
                    "requirement_ids": ["REQ-001"],
                }
            ],
            "risks": [
                {
                    "id": "RISK-001",
                    "description": "Auth regression",
                    "impact": "low",
                    "mitigation": "Run auth regression tests",
                }
            ],
            "implementation_plan": {
                "implementation_steps": ["Update auth flow"],
                "target_modules": ["backend.auth"],
                "constraints": [],
            },
            "test_plan": {
                "test_scope": ["Recruiter login API"],
                "edge_cases": [],
                "regression_focus": ["Auth regression"],
            },
            "codex_prompt_handoff": {
                "agent_prompt": "Implement the login change.",
                "recommended_execution_order": ["Review auth flow", "Apply patch"],
                "non_goals": [],
                "validation_checklist": ["Run auth tests"],
            },
            "claude_code_prompt_handoff": {
                "agent_prompt": "Validate the login change.",
                "recommended_execution_order": ["Inspect diff", "Run tests"],
                "non_goals": [],
                "validation_checklist": ["Regression covered"],
            },
            "metrics": {"coverage_ratio": 1.0},
            "high_risk_ratio": 0.0,
            "revision_round": 0,
            "trace": {},
        }
        report_paths = {
            "report_md": str(run_dir / "report.md"),
            "report_json": str(run_dir / "report.json"),
            "run_trace": str(run_dir / "run_trace.json"),
        }
        (run_dir / "report.md").write_text(result["final_report"], encoding="utf-8")
        (run_dir / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (run_dir / "run_trace.json").write_text(json.dumps(result["trace"], ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "run_id": resolved_run_id,
            "run_dir": str(run_dir),
            "result": result,
            "report_paths": report_paths,
        }

    monkeypatch.setattr(review_service, "run_review", fake_run_review)

    result = await mcp_server.review_prd(source=str(source_path), options={"outputs_root": str(tmp_path)})

    assert "error" not in result
    assert result["run_id"] == fixed_run_id
    report_payload = json.loads((tmp_path / fixed_run_id / "report.json").read_text(encoding="utf-8"))
    trace_payload = json.loads((tmp_path / fixed_run_id / "run_trace.json").read_text(encoding="utf-8"))
    bundle_payload = json.loads((tmp_path / fixed_run_id / "delivery_bundle.json").read_text(encoding="utf-8"))
    assert report_payload["source_metadata"]["mime_type"] == "text/markdown"
    assert trace_payload["source_metadata"]["extra"]["extension"] == ".md"
    assert bundle_payload["metadata"]["source_metadata"]["size_bytes"] == source_path.stat().st_size


@pytest.mark.asyncio
async def test_review_prd_feishu_source_returns_not_implemented(tmp_path):
    result = await mcp_server.review_prd(source="feishu://wiki/space/doc-token", options={"outputs_root": str(tmp_path)})

    assert result["status"] == "failed"
    assert result["error"]["code"] == "NOT_IMPLEMENTED"
    assert "Feishu connector fetching is not implemented" in result["error"]["message"]


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

    approval_records_payload = json.loads((run_dir / "approval_records.json").read_text(encoding="utf-8"))
    snapshot_payload = json.loads((run_dir / "status_snapshot.json").read_text(encoding="utf-8"))

    assert "error" not in result
    assert result["status"] == "approved"
    assert len(result["approval_history"]) == 1
    assert result["approval_records_path"] == str(run_dir / "approval_records.json")
    assert result["status_snapshot_path"] == str(run_dir / "status_snapshot.json")
    assert result["status_snapshot"]["bundle_status"] == "approved"
    assert approval_records_payload["approval_records"][0]["action"] == "approve"
    assert approval_records_payload["approval_records"][0]["from_bundle_status"] == "draft"
    assert approval_records_payload["approval_records"][0]["to_bundle_status"] == "approved"
    assert approval_records_payload["approval_records"][0]["workspace_status"] == "confirmed"
    assert approval_records_payload["approval_records"][0]["reviewer"] == "alice"
    assert snapshot_payload["run_id"] == run_id
    assert snapshot_payload["bundle_id"] == f"bundle-{run_id}"
    assert snapshot_payload["bundle_status"] == "approved"
    assert snapshot_payload["workspace_status"] == "confirmed"


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
    original_approval_records = {
        "approval_records": [
            {
                "record_id": "approval-existing",
                "run_id": run_id,
                "bundle_id": f"bundle-{run_id}",
                "timestamp": "2026-03-07T12:00:00+00:00",
                "action": "approve",
                "from_bundle_status": "draft",
                "to_bundle_status": "approved",
                "workspace_status": "confirmed",
                "reviewer": "alice",
                "comment": "Approved",
            }
        ]
    }
    original_snapshot = {
        "run_id": run_id,
        "bundle_id": f"bundle-{run_id}",
        "bundle_status": "approved",
        "workspace_status": "confirmed",
        "updated_at": "2026-03-07T12:00:00+00:00",
    }
    (run_dir / "delivery_bundle.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "approval_records.json").write_text(json.dumps(original_approval_records, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "status_snapshot.json").write_text(json.dumps(original_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    result = mcp_server.approve_handoff(
        bundle_id=f"bundle-{run_id}",
        action="reset_to_draft",
        reviewer="alice",
        comment="Reopen",
        options={"outputs_root": str(tmp_path)},
    )

    reloaded_bundle = json.loads((run_dir / "delivery_bundle.json").read_text(encoding="utf-8"))
    approval_records_payload = json.loads((run_dir / "approval_records.json").read_text(encoding="utf-8"))
    snapshot_payload = json.loads((run_dir / "status_snapshot.json").read_text(encoding="utf-8"))

    assert result["error"]["code"] == "invalid_input"
    assert reloaded_bundle["status"] == "approved"
    assert approval_records_payload == original_approval_records
    assert snapshot_payload == original_snapshot


def _write_review_workspace_fixture(tmp_path, run_id: str = "20260307T010205Z") -> str:
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
    return f"bundle-{run_id}"


def test_get_review_workspace_by_run_id_returns_workspace_state(tmp_path):
    run_id = "20260304T010206Z"
    bundle_id = _write_review_workspace_fixture(tmp_path, run_id=run_id)

    result = mcp_server.get_review_workspace(run_id=run_id, options={"outputs_root": str(tmp_path)})

    assert "error" not in result
    assert result["run_id"] == run_id
    assert result["bundle"]["bundle_id"] == bundle_id
    assert result["bundle"]["status"] == "approved"
    assert len(result["approval_history"]) == 1
    assert len(result["approval_records"]) == 1
    assert result["approval_records"][0]["action"] == "approve"
    assert result["status_snapshot"]["bundle_status"] == "approved"
    assert result["status_snapshot"]["workspace_status"] == "confirmed"
    assert result["paths"]["approval_records_path"].endswith("approval_records.json")


def test_get_review_workspace_by_bundle_id_returns_workspace_state(tmp_path):
    run_id = "20260304T010207Z"
    bundle_id = _write_review_workspace_fixture(tmp_path, run_id=run_id)

    result = mcp_server.get_review_workspace(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})

    assert "error" not in result
    assert result["run_id"] == run_id
    assert result["bundle"]["bundle_id"] == bundle_id
    assert result["approval_history"][0]["to_status"] == "approved"
    assert result["approval_records"][0]["bundle_id"] == bundle_id
    assert result["status_snapshot"]["run_id"] == run_id


def test_get_review_workspace_missing_files_returns_error(tmp_path):
    run_id = "20260304T010208Z"
    bundle_id = _write_review_workspace_fixture(tmp_path, run_id=run_id)
    (tmp_path / run_id / "status_snapshot.json").unlink()

    result = mcp_server.get_review_workspace(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "not_found"
    assert "status_snapshot.json" in result["error"]["message"]


def _write_approved_bundle_fixture(tmp_path, run_id: str = "20260307T010206Z") -> str:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "implementation_pack.json").write_text(
        json.dumps({"pack_type": "implementation_pack", "task_id": "TASK-001", "title": "Implement login"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "test_pack.json").write_text(
        json.dumps({"pack_type": "test_pack", "task_id": "TASK-001", "title": "Test login"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "execution_pack.json").write_text(
        json.dumps({"risk_pack": [{"id": "RISK-001", "level": "low"}]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (run_dir / "report.json").write_text(
        json.dumps(
            {
                "parsed_items": [{"id": "REQ-001", "description": "Support login"}],
                "review_results": [{"id": "REQ-001", "issues": ["Clarify SSO provider"]}],
                "tasks": [{"id": "TASK-001", "title": "Implement login", "requirement_ids": ["REQ-001"]}],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
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
        "metadata": {"source_report_paths": {"report_json": str(run_dir / "report.json")}},
    }
    (run_dir / "delivery_bundle.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle_payload["bundle_id"]


@pytest.mark.asyncio
async def test_handoff_to_executor_creates_persisted_tasks_and_traceability(tmp_path):
    bundle_id = _write_approved_bundle_fixture(tmp_path)

    result = await mcp_server.handoff_to_executor(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})

    assert "error" not in result
    assert result["status"] == "routed"
    assert result["task_count"] == 2
    assert (tmp_path / "20260307T010206Z" / "execution_tasks.json").exists()
    assert (tmp_path / "20260307T010206Z" / "traceability_map.json").exists()


@pytest.mark.asyncio
async def test_get_execution_status_returns_bundle_tasks_and_task_lookup(tmp_path):
    bundle_id = _write_approved_bundle_fixture(tmp_path)
    run_dir = tmp_path / "20260307T010206Z"
    await mcp_server.handoff_to_executor(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})

    by_bundle = mcp_server.get_execution_status(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})
    by_task = mcp_server.get_execution_status(
        task_id="bundle-20260307T010206Z:implementation_pack",
        options={"outputs_root": str(tmp_path)},
    )

    assert by_bundle["task_count"] == 2
    assert by_bundle["tasks"][0]["bundle_id"] == bundle_id
    assert by_task["task"]["task_id"] == "bundle-20260307T010206Z:implementation_pack"
    assert by_task["traceability"]["counts"]["total"] == 1
    assert (run_dir / "execution_tasks.json").exists()


@pytest.mark.asyncio
async def test_get_traceability_supports_bundle_and_requirement_queries(tmp_path):
    bundle_id = _write_approved_bundle_fixture(tmp_path)
    await mcp_server.handoff_to_executor(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})

    by_bundle = mcp_server.get_traceability(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})
    by_requirement = mcp_server.get_traceability(requirement_id="REQ-001", options={"outputs_root": str(tmp_path)})

    assert by_bundle["bundle_id"] == bundle_id
    assert by_bundle["counts"]["full"] >= 1
    assert by_requirement["count"] >= 1
    assert by_requirement["links"][0]["requirement_id"] == "REQ-001"
