from __future__ import annotations

import json
from pathlib import Path

from requirement_review_v1.execution import ExecutionMode, ExecutionTask, ExecutionTaskStatus
from requirement_review_v1.service.execution_service import (
    append_execution_event,
    handoff_to_executor_for_mcp,
    list_execution_tasks_for_mcp,
    update_execution_task_for_mcp,
)


def _write_approved_execution_workspace(tmp_path: Path, run_id: str = "20260308T020304Z") -> tuple[str, Path]:
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
        "created_at": "2026-03-08T02:03:04+00:00",
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
    return bundle_id, run_dir


def test_append_execution_event_adds_log_entry_without_changing_status() -> None:
    task = ExecutionTask(
        task_id="bundle-1:implementation_pack",
        bundle_id="bundle-1",
        source_pack_type="implementation_pack",
        executor_type="codex",
        execution_mode=ExecutionMode.agent_assisted,
        status=ExecutionTaskStatus.pending,
        created_at="2026-03-08T02:03:04+00:00",
        updated_at="2026-03-08T02:03:04+00:00",
    )

    updated = append_execution_event(task, actor="poller", event_type="heartbeat", detail="still running")

    assert updated.status == "pending"
    assert updated.execution_log[-1].event_type == "heartbeat"
    assert updated.execution_log[-1].detail == "still running"
    assert updated.execution_log[-1].actor == "poller"
    assert updated.updated_at != task.updated_at


def test_update_execution_task_for_mcp_persists_tasks_snapshot_and_trace(tmp_path: Path) -> None:
    bundle_id, run_dir = _write_approved_execution_workspace(tmp_path)
    handoff_to_executor_for_mcp(bundle_id=bundle_id, options={"outputs_root": str(tmp_path)})
    task_id = f"{bundle_id}:implementation_pack"

    update_execution_task_for_mcp(
        task_id=task_id,
        status="assigned",
        actor="executor-gateway",
        assigned_to="codex-worker-1",
        detail="claim accepted",
        artifact_paths={"claim_receipt": str(run_dir / "claim.json")},
        options={"outputs_root": str(tmp_path)},
    )
    update_execution_task_for_mcp(
        task_id=task_id,
        status="in_progress",
        actor="codex-worker-1",
        detail="patching auth flow",
        options={"outputs_root": str(tmp_path)},
    )
    update_execution_task_for_mcp(
        task_id=task_id,
        status="waiting_review",
        actor="codex-worker-1",
        detail="checkpoint ready",
        artifact_paths={"diff": str(run_dir / "changes.diff")},
        options={"outputs_root": str(tmp_path)},
    )
    update_execution_task_for_mcp(
        task_id=task_id,
        status="in_progress",
        actor="reviewer",
        detail="resume after checkpoint",
        options={"outputs_root": str(tmp_path)},
    )
    completed = update_execution_task_for_mcp(
        task_id=task_id,
        status="completed",
        actor="codex-worker-1",
        result_summary="implemented and validated",
        artifact_paths={"result_report": str(run_dir / "result.md")},
        options={"outputs_root": str(tmp_path)},
    )

    tasks_payload = json.loads((run_dir / "execution_tasks.json").read_text(encoding="utf-8"))["tasks"]
    updated_task = next(item for item in tasks_payload if item["task_id"] == task_id)
    status_snapshot = json.loads((run_dir / "status_snapshot.json").read_text(encoding="utf-8"))
    trace_payload = json.loads((run_dir / "run_trace.json").read_text(encoding="utf-8"))
    listed = list_execution_tasks_for_mcp(bundle_id=bundle_id, status="completed", options={"outputs_root": str(tmp_path)})

    assert completed["task"]["status"] == "completed"
    assert completed["task"]["result_summary"] == "implemented and validated"
    assert updated_task["metadata"]["artifact_paths"]["claim_receipt"].endswith("claim.json")
    assert updated_task["metadata"]["artifact_paths"]["diff"].endswith("changes.diff")
    assert updated_task["metadata"]["artifact_paths"]["result_report"].endswith("result.md")
    assert status_snapshot["bundle_status"] == "approved"
    assert status_snapshot["execution"]["counts"]["completed"] == 1
    assert status_snapshot["execution"]["last_task_id"] == task_id
    assert status_snapshot["execution"]["last_status"] == "completed"
    assert len(trace_payload["execution_updates"]) == 5
    assert trace_payload["execution_updates"][0]["from_status"] == "pending"
    assert trace_payload["execution_updates"][0]["to_status"] == "assigned"
    assert trace_payload["execution_updates"][-1]["to_status"] == "completed"
    assert listed["count"] == 1
    assert listed["tasks"][0]["task_id"] == task_id
