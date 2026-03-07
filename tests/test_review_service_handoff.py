from __future__ import annotations

import json
from pathlib import Path

from requirement_review_v1.service.review_service import build_delivery_handoff_outputs


def test_build_delivery_handoff_outputs_writes_packs_and_trace(tmp_path):
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "parsed_items": [
                {
                    "id": "REQ-001",
                    "description": "Support OAuth login for campus recruiters",
                    "acceptance_criteria": ["OAuth callback succeeds", "Session is persisted"],
                }
            ],
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Implement OAuth login flow",
                    "owner": "BE",
                    "requirement_ids": ["REQ-001"],
                }
            ],
            "risks": [
                {
                    "id": "RISK-001",
                    "description": "Existing login flow may regress",
                    "impact": "high",
                    "mitigation": "Run focused auth regression tests",
                    "owner": "qa",
                }
            ],
            "implementation_plan": {
                "implementation_steps": ["Inspect auth entrypoints", "Implement OAuth callback"],
                "target_modules": ["backend.auth", "frontend.login"],
                "constraints": ["Preserve password login behavior"],
            },
            "test_plan": {
                "test_scope": ["OAuth callback API", "Recruiter login page"],
                "edge_cases": ["Expired OAuth state"],
                "regression_focus": ["Password login"],
            },
            "codex_prompt_handoff": {
                "agent_prompt": "Implement the auth changes, then run focused backend and frontend tests.",
                "recommended_execution_order": ["Review auth flow", "Apply backend changes"],
                "non_goals": ["Do not redesign account settings"],
                "validation_checklist": ["Acceptance criteria mapped to tests"],
            },
            "claude_code_prompt_handoff": {
                "agent_prompt": "Verify the implementation with edge-case and regression coverage.",
                "recommended_execution_order": ["Review changed files", "Run regression suite"],
                "non_goals": ["Do not broaden test scope beyond auth"],
                "validation_checklist": ["OAuth edge cases covered"],
            },
            "trace": {},
        },
    }

    artifact_paths = build_delivery_handoff_outputs(run_output)

    assert set(artifact_paths) == {"implementation_pack", "test_pack", "execution_pack"}
    for path_str in artifact_paths.values():
        path = Path(path_str)
        assert path.exists()
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        assert payload

    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["pack_builder"]["status"] == "ok"
    assert trace_payload["pack_builder"]["non_blocking"] is True
    assert trace_payload["pack_builder"]["packs"]["implementation_pack"]["status"] == "ok"
    assert trace_payload["pack_builder"]["packs"]["test_pack"]["duration_ms"] >= 0
    assert trace_payload["pack_builder"]["packs"]["execution_pack"]["duration_ms"] >= 0

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report_payload["artifacts"]["implementation_pack"].endswith("implementation_pack.json")
    assert report_payload["trace"]["pack_builder"]["status"] == "ok"


def test_build_delivery_handoff_outputs_is_non_blocking_on_pack_failure(tmp_path):
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "parsed_items": [{"id": "REQ-001", "description": "Broken payload", "acceptance_criteria": []}],
            "tasks": "invalid",
            "risks": [],
            "implementation_plan": {},
            "test_plan": {},
            "codex_prompt_handoff": {},
            "claude_code_prompt_handoff": {},
            "trace": {},
        },
    }

    artifact_paths = build_delivery_handoff_outputs(run_output)

    assert artifact_paths == {}
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["pack_builder"]["status"] == "failed"
    assert trace_payload["pack_builder"]["non_blocking"] is True
    assert trace_payload["pack_builder"]["packs"]["implementation_pack"]["status"] == "error"
    assert trace_payload["pack_builder"]["packs"]["test_pack"]["status"] == "error"
    assert trace_payload["pack_builder"]["packs"]["execution_pack"]["status"] == "error"
