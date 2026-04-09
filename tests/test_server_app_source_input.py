from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from requirement_review_v1.monitoring import read_audit_events
from requirement_review_v1.server import app as app_module


def _build_client() -> TestClient:
    return TestClient(app_module.app)


@pytest.mark.asyncio
async def test_create_review_keeps_legacy_prd_path_compatible(tmp_path, monkeypatch):
    prd_file = tmp_path / "legacy_prd.md"
    prd_file.write_text("# Legacy PRD", encoding="utf-8")
    captured: dict[str, object] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None, mode=None, llm_options=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
        captured["mode"] = mode
        captured["llm_options"] = llm_options
        job.status = "completed"

    monkeypatch.setattr(app_module, "_run_job", fake_run_job)
    monkeypatch.setattr(app_module, "make_run_id", lambda: "20260308T020301Z")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    result = await app_module.create_review(app_module.ReviewCreateRequest(prd_path=str(prd_file)))
    job = app_module._jobs[result["run_id"]]
    await job.task

    assert result["run_id"] == "20260308T020301Z"
    assert captured["prd_text"] is None
    assert captured["prd_path"] == str(prd_file.resolve())
    assert captured["source"] is None
    assert captured["mode"] is None
    assert captured["llm_options"] == {}
    app_module._jobs.clear()


@pytest.mark.asyncio
async def test_create_review_prioritizes_source_over_legacy_fields(tmp_path, monkeypatch):
    source_file = tmp_path / "source_prd.md"
    source_file.write_text("# Source PRD", encoding="utf-8")
    captured: dict[str, object] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None, mode=None, llm_options=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
        captured["mode"] = mode
        captured["llm_options"] = llm_options
        job.status = "completed"

    monkeypatch.setattr(app_module, "_run_job", fake_run_job)
    monkeypatch.setattr(app_module, "make_run_id", lambda: "20260308T020302Z")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    payload = app_module.ReviewCreateRequest(
        source=str(source_file),
        prd_text="ignored text",
        prd_path=str(source_file),
    )
    result = await app_module.create_review(payload)
    job = app_module._jobs[result["run_id"]]
    await job.task

    assert result["run_id"] == "20260308T020302Z"
    assert captured["prd_text"] is None
    assert captured["prd_path"] is None
    assert captured["source"] == str(source_file)
    assert captured["mode"] is None
    assert captured["llm_options"] == {}
    app_module._jobs.clear()


@pytest.mark.asyncio
async def test_create_review_forwards_runtime_llm_options(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None, mode=None, llm_options=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
        captured["mode"] = mode
        captured["llm_options"] = llm_options
        job.status = "completed"

    monkeypatch.setattr(app_module, "_run_job", fake_run_job)
    monkeypatch.setattr(app_module, "make_run_id", lambda: "20260308T020304Z")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    payload = app_module.ReviewCreateRequest(
        prd_text="# Test PRD",
        smart_llm="deepseek:deepseek-chat",
        temperature=0.1,
        reasoning_effort="low",
        llm_kwargs={"max_retries": 1},
    )
    result = await app_module.create_review(payload)
    job = app_module._jobs[result["run_id"]]
    await job.task

    assert result["run_id"] == "20260308T020304Z"
    assert captured["prd_text"] == "# Test PRD"
    assert captured["llm_options"] == {
        "smart_llm": "deepseek:deepseek-chat",
        "temperature": 0.1,
        "reasoning_effort": "low",
        "llm_kwargs": {"max_retries": 1},
    }
    app_module._jobs.clear()


@pytest.mark.asyncio
async def test_get_review_status_keeps_legacy_report_paths_for_completed_run(tmp_path, monkeypatch):
    run_id = "20260308T020303Z"
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "report.md").write_text("# Report", encoding="utf-8")
    (run_dir / "report.json").write_text("{}", encoding="utf-8")
    (run_dir / "run_trace.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    result = await app_module.get_review_status(run_id)

    assert result["run_id"] == run_id
    assert result["status"] == "completed"
    assert result["report_paths"] == {
        "report_md": str(run_dir / "report.md"),
        "report_json": str(run_dir / "report.json"),
        "run_trace": str(run_dir / "run_trace.json"),
    }
    app_module._jobs.clear()


def test_feishu_submit_successfully_reuses_review_submission(tmp_path, monkeypatch):
    captured: dict[str, object] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None, mode=None, llm_options=None, audit_context=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
        captured["mode"] = mode
        captured["llm_options"] = llm_options
        captured["audit_context"] = audit_context
        job.status = "completed"

    monkeypatch.setenv("MARRDP_FEISHU_SIGNATURE_DISABLED", "true")
    monkeypatch.setattr(app_module, "_run_job", fake_run_job)
    monkeypatch.setattr(app_module, "make_run_id", lambda: "20260308T020305Z")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = _build_client()
    response = client.post(
        "/api/feishu/submit",
        json={
            "source": "feishu://docx/doc-token",
            "mode": "quick",
            "open_id": "ou_test_user",
            "tenant_key": "tenant-test",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"run_id": "20260308T020305Z"}
    assert captured["prd_text"] is None
    assert captured["prd_path"] is None
    assert captured["source"] == "feishu://docx/doc-token"
    assert captured["mode"] == "quick"
    assert captured["llm_options"] == {}
    assert captured["audit_context"] == {
        "source": "feishu",
        "tool_name": "feishu.submit",
        "actor": "ou_test_user",
        "client_metadata": {
            "trigger_source": "feishu",
            "open_id": "ou_test_user",
            "tenant_key": "tenant-test",
        },
    }
    entry_context = json.loads((tmp_path / "20260308T020305Z" / "entry_context.json").read_text(encoding="utf-8"))
    assert entry_context == {
        "source_origin": "feishu",
        "entry_mode": "plugin",
        "submitter_open_id": "ou_test_user",
        "tenant_key": "tenant-test",
        "trigger_source": "feishu",
        "submitted_by": "ou_test_user",
        "tool_name": "feishu.submit",
        "created_at": entry_context["created_at"],
    }
    submission_events = read_audit_events(tmp_path / "20260308T020305Z")
    assert submission_events[0]["operation"] == "review_submission"
    assert submission_events[0]["actor"] == "ou_test_user"
    assert submission_events[0]["source"] == "feishu"
    assert submission_events[0]["details"]["source_origin"] == "feishu"
    assert submission_events[0]["details"]["entry_mode"] == "plugin"
    app_module._jobs.clear()


def test_feishu_submit_rejects_invalid_payload(monkeypatch):
    monkeypatch.setenv("MARRDP_FEISHU_SIGNATURE_DISABLED", "true")
    app_module._jobs.clear()

    client = _build_client()
    response = client.post("/api/feishu/submit", json={"mode": "quick"})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "request_validation_error"
