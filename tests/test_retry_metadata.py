from __future__ import annotations

import json

from requirement_review_v1.monitoring import build_retry_metadata, retry_metadata_for_status
from requirement_review_v1.service.review_service import build_delivery_handoff_outputs


def test_retry_metadata_for_status_captures_failure_and_blocked_dependency() -> None:
    failed = retry_metadata_for_status(status="failed", non_blocking=True, error_message="renderer boom")
    blocked = retry_metadata_for_status(status="skipped", non_blocking=True, error_message="execution_pack_path_missing")
    exhausted = build_retry_metadata(retryable=True, attempt=3, max_attempts=3, last_error="still failing")

    assert failed["retryable"] is True
    assert failed["state"] == "available"
    assert failed["recommended_action"] == "manual_retry"
    assert failed["last_error"] == "renderer boom"

    assert blocked["retryable"] is True
    assert blocked["state"] == "blocked"
    assert blocked["recommended_action"] == "retry_after_dependency_recovery"

    assert exhausted["state"] == "exhausted"
    assert exhausted["recommended_action"] == "escalate"


def test_build_delivery_handoff_outputs_persists_retry_metadata_for_non_blocking_steps(tmp_path) -> None:
    report_json_path = tmp_path / "report.json"
    trace_path = tmp_path / "run_trace.json"
    report_json_path.write_text(json.dumps({"trace": {}}, ensure_ascii=False, indent=2), encoding="utf-8")
    trace_path.write_text(json.dumps({}, ensure_ascii=False, indent=2), encoding="utf-8")

    run_output = {
        "run_dir": str(tmp_path),
        "run_id": "20260308T040506Z",
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

    assert trace_payload["pack_builder"]["retry"]["retryable"] is True
    assert trace_payload["pack_builder"]["retry"]["state"] == "available"
    assert trace_payload["pack_builder"]["packs"]["implementation_pack"]["retry"]["retryable"] is True

    assert trace_payload["handoff_renderer"]["retry"]["retryable"] is True
    assert trace_payload["handoff_renderer"]["retry"]["state"] == "blocked"

    assert trace_payload["bundle_builder"]["retry"]["retryable"] is True
    assert trace_payload["bundle_builder"]["retry"]["state"] == "available"
