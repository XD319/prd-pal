from __future__ import annotations

import json
from pathlib import Path

from requirement_review_v1.packs.delivery_bundle import DeliveryBundle
from requirement_review_v1.service import review_service
from requirement_review_v1.service.review_service import build_delivery_handoff_outputs


def test_build_delivery_handoff_outputs_writes_packs_and_trace(tmp_path):
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260307T010203Z",
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "final_report": "# Requirement Review Report\n\nSummary.",
            "parsed_items": [
                {
                    "id": "REQ-001",
                    "description": "Support OAuth login for campus recruiters",
                    "acceptance_criteria": ["OAuth callback succeeds", "Session is persisted"],
                }
            ],
            "review_results": [
                {
                    "id": "REQ-001",
                    "description": "Support OAuth login for campus recruiters",
                    "is_ambiguous": True,
                    "issues": ["OAuth provider onboarding owner missing"],
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

    assert set(artifact_paths) == {
        "implementation_pack",
        "test_pack",
        "execution_pack",
        "codex_prompt",
        "claude_code_prompt",
        "prd_review_report",
        "open_questions",
        "scope_boundary",
        "tech_design_draft",
        "test_checklist",
        "delivery_bundle",
    }
    for path_str in artifact_paths.values():
        path = Path(path_str)
        assert path.exists()
        if path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(payload, dict)
            assert payload
        else:
            content = path.read_text(encoding="utf-8")
            assert content.startswith("# ")

    bundle_payload = json.loads(Path(artifact_paths["delivery_bundle"]).read_text(encoding="utf-8"))
    bundle = DeliveryBundle.model_validate(bundle_payload)
    assert bundle.status == "draft"
    assert bundle.artifacts.prd_review_report.path.endswith("prd_review_report.md")
    assert bundle.artifacts.execution_pack.path.endswith("execution_pack.json")

    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["pack_builder"]["status"] == "ok"
    assert trace_payload["handoff_renderer"]["status"] == "ok"
    assert trace_payload["bundle_builder"]["status"] == "ok"
    assert trace_payload["bundle_builder"]["output_paths"]["delivery_bundle"].endswith("delivery_bundle.json")

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report_payload["artifacts"]["implementation_pack"].endswith("implementation_pack.json")
    assert report_payload["artifacts"]["delivery_bundle"].endswith("delivery_bundle.json")
    assert report_payload["trace"]["bundle_builder"]["status"] == "ok"


def test_build_delivery_handoff_outputs_is_non_blocking_on_pack_failure(tmp_path):
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260307T010204Z",
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
    assert trace_payload["handoff_renderer"]["status"] == "skipped"
    assert trace_payload["bundle_builder"]["status"] == "failed"


def test_build_delivery_handoff_outputs_keeps_main_result_when_renderer_fails(tmp_path, monkeypatch):
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260307T010205Z",
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "final_report": "# Requirement Review Report\n\nSummary.",
            "parsed_items": [
                {
                    "id": "REQ-001",
                    "description": "Support OAuth login for campus recruiters",
                    "acceptance_criteria": ["OAuth callback succeeds", "Session is persisted"],
                }
            ],
            "review_results": [],
            "tasks": [{"id": "TASK-001", "title": "Implement OAuth login flow", "owner": "BE", "requirement_ids": ["REQ-001"]}],
            "risks": [],
            "implementation_plan": {
                "implementation_steps": ["Inspect auth entrypoints", "Implement OAuth callback"],
                "target_modules": ["backend.auth"],
                "constraints": ["Preserve password login behavior"],
            },
            "test_plan": {
                "test_scope": ["OAuth callback API"],
                "edge_cases": ["Expired OAuth state"],
                "regression_focus": ["Password login"],
            },
            "codex_prompt_handoff": {},
            "claude_code_prompt_handoff": {},
            "trace": {},
        },
    }

    monkeypatch.setattr(review_service, "render_codex_prompt", lambda _pack: (_ for _ in ()).throw(RuntimeError("renderer boom")))

    artifact_paths = build_delivery_handoff_outputs(run_output)

    assert "execution_pack" in artifact_paths
    assert "claude_code_prompt" in artifact_paths
    assert "codex_prompt" not in artifact_paths
    assert "delivery_bundle" in artifact_paths

    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace_payload["pack_builder"]["status"] == "ok"
    assert trace_payload["handoff_renderer"]["status"] == "partial_success"
    assert trace_payload["handoff_render_error"] == "renderer boom"
    assert trace_payload["bundle_builder"]["status"] == "ok"

    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert report_payload["trace"]["handoff_renderer"]["status"] == "partial_success"
    assert report_payload["trace"]["handoff_render_error"] == "renderer boom"
    assert report_payload["trace"]["bundle_builder"]["status"] == "ok"
