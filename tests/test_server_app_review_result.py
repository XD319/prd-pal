from __future__ import annotations

import json

from fastapi.testclient import TestClient

from requirement_review_v1.server import app as app_module


def test_get_review_result_returns_parsed_report_and_stable_artifacts(tmp_path, monkeypatch):
    run_id = "20260309T010203Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    report_payload = {
        "run_id": run_id,
        "schema_version": "v1.1",
        "trace": {"reviewer": {"status": "ok"}},
    }
    (run_dir / "report.md").write_text("# Review Report", encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run_trace.json").write_text("{}", encoding="utf-8")
    (run_dir / "review_report.json").write_text("{}", encoding="utf-8")
    (run_dir / "risk_items.json").write_text("{}", encoding="utf-8")
    (run_dir / "open_questions.json").write_text("{}", encoding="utf-8")
    (run_dir / "review_summary.md").write_text("# Review Summary", encoding="utf-8")

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get(f"/api/review/{run_id}/result")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "run_id": run_id,
        "status": "completed",
        "result": report_payload,
        "artifact_paths": {
            "report_md": str(run_dir / "report.md"),
            "report_json": str(run_dir / "report.json"),
            "run_trace": str(run_dir / "run_trace.json"),
            "review_report_json": str(run_dir / "review_report.json"),
            "risk_items_json": str(run_dir / "risk_items.json"),
            "open_questions_json": str(run_dir / "open_questions.json"),
            "review_summary_md": str(run_dir / "review_summary.md"),
        },
    }
    app_module._jobs.clear()


def test_get_review_result_returns_404_for_missing_run(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get("/api/review/20260309T010204Z/result")

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "run_not_found",
        "message": "run_id not found: 20260309T010204Z",
    }
    app_module._jobs.clear()


def test_get_review_result_returns_409_when_report_is_not_ready(tmp_path, monkeypatch):
    run_id = "20260309T010205Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()
    job = app_module.JobRecord(run_id=run_id, run_dir=run_dir, status="running", current_node="planner")
    job.node_progress["planner"]["status"] = "running"
    app_module._jobs[run_id] = job

    client = TestClient(app_module.app)
    response = client.get(f"/api/review/{run_id}/result")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "result_not_ready"
    assert detail["message"] == f"report.json not ready for run_id={run_id}"
    assert detail["run_id"] == run_id
    assert detail["status"] == "running"
    assert detail["progress"]["current_node"] == "planner"
    app_module._jobs.clear()
