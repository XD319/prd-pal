from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from prd_pal.server import app as app_module


def _utc_timestamp(year: int, month: int, day: int, hour: int, minute: int, second: int = 0) -> float:
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc).timestamp()


def test_list_runs_returns_empty_when_outputs_directory_has_no_runs(tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get("/api/runs")

    assert response.status_code == 200
    assert response.json() == {"count": 0, "runs": []}
    app_module._jobs.clear()


def test_list_runs_returns_completed_run_with_artifact_flags(tmp_path, monkeypatch):
    run_id = "20260309T010203Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    report_md = run_dir / "report.md"
    report_json = run_dir / "report.json"
    run_trace = run_dir / "run_trace.json"
    report_md.write_text("# Report", encoding="utf-8")
    report_json.write_text("{}", encoding="utf-8")
    run_trace.write_text("{}", encoding="utf-8")

    older_ts = _utc_timestamp(2026, 3, 9, 1, 3, 0)
    latest_ts = _utc_timestamp(2026, 3, 9, 1, 5, 0)
    os.utime(run_dir, (older_ts, older_ts))
    os.utime(report_md, (older_ts, older_ts))
    os.utime(run_trace, (older_ts, older_ts))
    os.utime(report_json, (latest_ts, latest_ts))

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["runs"] == [
        {
            "run_id": run_id,
            "status": "completed",
            "created_at": "2026-03-09T01:02:03+00:00",
            "updated_at": "2026-03-09T01:05:00+00:00",
            "artifact_presence": {
                "report_md": True,
                "report_json": True,
                "run_trace": True,
                "review_report_json": False,
                "risk_items_json": False,
                "open_questions_json": False,
                "review_summary_md": False,
            },
        }
    ]
    app_module._jobs.clear()


def test_list_runs_returns_in_progress_run_from_active_job_state(tmp_path, monkeypatch):
    run_id = "20260309T020304Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_trace.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()
    app_module._jobs[run_id] = app_module.JobRecord(
        run_id=run_id,
        run_dir=run_dir,
        status="running",
        created_at="2026-03-09T02:03:04+00:00",
        updated_at="2026-03-09T02:04:30+00:00",
        current_node="planner",
    )

    client = TestClient(app_module.app)
    response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["runs"] == [
        {
            "run_id": run_id,
            "status": "running",
            "created_at": "2026-03-09T02:03:04+00:00",
            "updated_at": "2026-03-09T02:04:30+00:00",
            "artifact_presence": {
                "report_md": False,
                "report_json": False,
                "run_trace": True,
                "review_report_json": False,
                "risk_items_json": False,
                "open_questions_json": False,
                "review_summary_md": False,
            },
        }
    ]
    app_module._jobs.clear()


def test_list_runs_returns_most_recent_runs_first(tmp_path, monkeypatch):
    older_run = tmp_path / "20260309T020304Z"
    newer_run = tmp_path / "20260309T030405Z"
    older_run.mkdir(parents=True)
    newer_run.mkdir(parents=True)
    (older_run / "report.json").write_text("{}", encoding="utf-8")
    (newer_run / "report.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = TestClient(app_module.app)
    response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload["runs"]] == ["20260309T030405Z", "20260309T020304Z"]
    app_module._jobs.clear()
