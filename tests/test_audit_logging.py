from __future__ import annotations

import json
from pathlib import Path

import pytest

from requirement_review_v1.mcp_server import server as mcp_server
from requirement_review_v1.monitoring import read_audit_events
from requirement_review_v1.service import review_service


@pytest.mark.asyncio
async def test_review_prd_writes_review_and_bundle_generation_audit_events(tmp_path: Path, monkeypatch) -> None:
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

    result = await mcp_server.review_prd(
        source=str(source_path),
        options={
            "outputs_root": str(tmp_path),
            "client_metadata": {"session_id": "sess-1"},
        },
    )

    assert "error" not in result
    events = read_audit_events(tmp_path / fixed_run_id)
    assert [event["operation"] for event in events] == ["review", "bundle_generation"]

    review_event, bundle_event = events
    assert review_event["run_id"] == fixed_run_id
    assert review_event["source"] == "mcp"
    assert review_event["client_metadata"]["session_id"] == "sess-1"
    assert review_event["details"]["tool_name"] == "review_prd"
    assert review_event["details"]["requirement_source"] == "source"
    assert review_event["retry"]["state"] == "not_needed"

    assert bundle_event["status"] == "ok"
    assert bundle_event["details"]["tool_name"] == "review_prd"
    assert bundle_event["details"]["component_statuses"]["bundle_builder"] == "ok"
    assert bundle_event["details"]["delivery_bundle_path"].endswith("delivery_bundle.json")


def _write_draft_bundle_fixture(tmp_path: Path, run_id: str = "20260308T030405Z") -> tuple[str, Path]:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    implementation_pack = {
        "pack_type": "implementation_pack",
        "task_id": "TASK-001",
        "title": "Implement login",
        "summary": "Support recruiter login safely.",
        "context": "Repository auth flow context.",
        "target_modules": ["backend.auth"],
        "implementation_steps": ["Inspect auth flow", "Implement login change"],
        "constraints": ["Do not break existing auth flow"],
        "acceptance_criteria": ["Login succeeds"],
        "recommended_skills": ["pytest"],
        "agent_handoff": {
            "primary_agent": "codex",
            "supporting_agents": ["claude_code"],
            "goals": ["Implement login"],
            "expected_output": "Small safe auth patch",
        },
    }
    test_pack = {
        "pack_type": "test_pack",
        "task_id": "TASK-001",
        "title": "Test login",
        "summary": "Validate recruiter login flow.",
        "test_scope": ["Login API"],
        "edge_cases": ["Invalid credentials"],
        "acceptance_criteria": ["Regression covered"],
        "agent_handoff": {
            "primary_agent": "claude_code",
            "supporting_agents": ["codex"],
            "goals": ["Run auth checks"],
            "expected_output": "Validation summary",
        },
    }
    execution_pack = {
        "pack_type": "execution_pack",
        "pack_version": "1.0",
        "implementation_pack": implementation_pack,
        "test_pack": test_pack,
        "risk_pack": [{"id": "RISK-001", "summary": "Auth regression", "level": "low"}],
        "handoff_strategy": "sequential",
    }

    (run_dir / "implementation_pack.json").write_text(json.dumps(implementation_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "test_pack.json").write_text(json.dumps(test_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "execution_pack.json").write_text(json.dumps(execution_pack, ensure_ascii=False, indent=2), encoding="utf-8")
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

    bundle_id = f"bundle-{run_id}"
    bundle_payload = {
        "bundle_id": bundle_id,
        "bundle_version": "1.0",
        "created_at": "2026-03-08T03:04:05+00:00",
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
        "metadata": {"source_report_paths": {"report_json": str(run_dir / "report.json")}},
    }
    (run_dir / "delivery_bundle.json").write_text(json.dumps(bundle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return bundle_id, run_dir


@pytest.mark.asyncio
async def test_workflow_tools_write_approval_handoff_and_execution_update_audit_events(tmp_path: Path) -> None:
    bundle_id, run_dir = _write_draft_bundle_fixture(tmp_path)
    options = {
        "outputs_root": str(tmp_path),
        "client_metadata": {"request_id": "req-1"},
    }

    approval = mcp_server.approve_handoff(
        bundle_id=bundle_id,
        action="approve",
        reviewer="alice",
        comment="ship it",
        options=options,
    )
    handoff = await mcp_server.handoff_to_executor(bundle_id=bundle_id, options=options)
    update = mcp_server.update_execution_task(
        task_id=f"{bundle_id}:implementation_pack",
        status="assigned",
        actor="executor-gateway",
        assigned_to="codex-worker-1",
        detail="claimed",
        options=options,
    )

    assert "error" not in approval
    assert "error" not in handoff
    assert "error" not in update

    events = read_audit_events(run_dir)
    assert [event["operation"] for event in events] == ["approval", "handoff", "execution_update"]

    approval_event, handoff_event, update_event = events
    assert approval_event["status"] == "approved"
    assert approval_event["actor"] == "alice"
    assert approval_event["client_metadata"]["request_id"] == "req-1"
    assert approval_event["details"]["action"] == "approve"

    assert handoff_event["status"] == "routed"
    assert handoff_event["details"]["tool_name"] == "handoff_to_executor"
    assert handoff_event["details"]["task_count"] == 2

    assert update_event["status"] == "assigned"
    assert update_event["actor"] == "executor-gateway"
    assert update_event["details"]["to_status"] == "assigned"
    assert update_event["details"]["assigned_to"] == "codex-worker-1"
    assert update_event["retry"]["state"] == "not_needed"
