from __future__ import annotations

import json
from pathlib import Path

from requirement_review_v1.connectors.schemas import SourceMetadata
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


def test_build_delivery_handoff_outputs_preserves_source_metadata(tmp_path):
    source_metadata = SourceMetadata(
        mime_type="text/markdown",
        encoding="utf-8",
        size_bytes=128,
        extra={"extension": ".md"},
    ).model_dump(mode="python")
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(
        json.dumps({"trace": {}, "source_metadata": source_metadata}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    trace_path.write_text(json.dumps({"source_metadata": source_metadata}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260307T010206Z",
        "source_metadata": source_metadata,
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "final_report": "# Requirement Review Report\n\nSummary.",
            "parsed_items": [
                {
                    "id": "REQ-001",
                    "description": "Support source ingestion",
                    "acceptance_criteria": ["Source metadata is persisted"],
                }
            ],
            "review_results": [
                {
                    "id": "REQ-001",
                    "description": "Support source ingestion",
                    "is_ambiguous": False,
                    "issues": [],
                }
            ],
            "tasks": [
                {
                    "id": "TASK-001",
                    "title": "Persist source metadata",
                    "owner": "BE",
                    "requirement_ids": ["REQ-001"],
                }
            ],
            "risks": [],
            "implementation_plan": {
                "implementation_steps": ["Write metadata to artifacts"],
                "target_modules": ["service.review_service"],
                "constraints": [],
            },
            "test_plan": {
                "test_scope": ["Connector metadata persistence"],
                "edge_cases": [],
                "regression_focus": [],
            },
            "codex_prompt_handoff": {
                "agent_prompt": "Persist source metadata.",
                "recommended_execution_order": ["Write metadata", "Run tests"],
                "non_goals": [],
                "validation_checklist": ["Artifacts include metadata"],
            },
            "claude_code_prompt_handoff": {
                "agent_prompt": "Validate source metadata persistence.",
                "recommended_execution_order": ["Inspect artifacts", "Run tests"],
                "non_goals": [],
                "validation_checklist": ["Metadata preserved"],
            },
            "trace": {},
        },
    }

    artifact_paths = build_delivery_handoff_outputs(run_output)

    bundle_payload = json.loads(Path(artifact_paths["delivery_bundle"]).read_text(encoding="utf-8"))
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert bundle_payload["metadata"]["source_metadata"] == source_metadata
    assert trace_payload["source_metadata"] == source_metadata
    assert report_payload["source_metadata"] == source_metadata


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


def test_build_delivery_handoff_outputs_persists_parallel_review_meta(tmp_path):
    parallel_review_meta = {
        "default_mode": "parallel_review",
        "selected_mode": "parallel_review",
        "parallel_triggered": True,
        "review_mode": "parallel_review",
        "partial_review": True,
        "manual_review_required": True,
        "manual_review_message": "\u9700\u4eba\u5de5\u8865\u5ba1\uff1a\u5b58\u5728\u9ad8\u98ce\u9669\u95ee\u9898\uff0c\u4e14\u4ee5\u4e0b reviewer \u7f3a\u5931\u6216\u5931\u8d25\uff1aqa (timeout: timed out after 30.0s)",
        "reviewer_count": 4,
        "reviewers_completed": ["product", "engineering", "security"],
        "reviewers_failed": [{"reviewer": "qa", "status": "timeout", "reason": "timed out after 30.0s"}],
        "open_questions_count": 2,
        "risk_items_count": 1,
        "artifact_paths": {
            "review_result_json": str(tmp_path / "review_result.json"),
            "review_report_md": str(tmp_path / "review_report.md"),
            "review_report_json": str(tmp_path / "review_report.json"),
        },
    }
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260307T010207Z",
        "report_paths": {
            "report_json": str(report_json_path),
            "run_trace": str(trace_path),
        },
        "result": {
            "final_report": "# Requirement Review Report\n\nSummary.",
            "parsed_items": [{"id": "REQ-001", "description": "Use parallel review", "acceptance_criteria": ["Done"]}],
            "review_results": [{"id": "REQ-001", "is_clear": True, "is_testable": True, "is_ambiguous": False, "issues": [], "suggestions": ""}],
            "tasks": [{"id": "TASK-001", "title": "Implement review", "owner": "BE", "requirement_ids": ["REQ-001"]}],
            "risks": [],
            "implementation_plan": {"implementation_steps": ["Implement"], "target_modules": ["workflow"], "constraints": []},
            "test_plan": {"test_scope": ["workflow"], "edge_cases": [], "regression_focus": []},
            "codex_prompt_handoff": {"agent_prompt": "Implement", "recommended_execution_order": [], "non_goals": [], "validation_checklist": []},
            "claude_code_prompt_handoff": {"agent_prompt": "Verify", "recommended_execution_order": [], "non_goals": [], "validation_checklist": []},
            "parallel-review_meta": parallel_review_meta,
            "trace": {},
        },
    }

    artifact_paths = build_delivery_handoff_outputs(run_output)

    bundle_payload = json.loads(Path(artifact_paths["delivery_bundle"]).read_text(encoding="utf-8"))
    trace_payload = json.loads(trace_path.read_text(encoding="utf-8"))
    report_payload = json.loads(report_json_path.read_text(encoding="utf-8"))
    assert bundle_payload["metadata"]["parallel-review_meta"] == parallel_review_meta
    assert trace_payload["parallel-review_meta"] == parallel_review_meta
    assert report_payload["parallel-review_meta"] == parallel_review_meta
    assert report_payload["parallel-review_meta"]["artifact_paths"]["review_result_json"].endswith("review_result.json")
