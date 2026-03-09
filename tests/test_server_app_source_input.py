from __future__ import annotations

import pytest

from requirement_review_v1.server import app as app_module


@pytest.mark.asyncio
async def test_create_review_keeps_legacy_prd_path_compatible(tmp_path, monkeypatch):
    prd_file = tmp_path / "legacy_prd.md"
    prd_file.write_text("# Legacy PRD", encoding="utf-8")
    captured: dict[str, str | None] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
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
    app_module._jobs.clear()


@pytest.mark.asyncio
async def test_create_review_prioritizes_source_over_legacy_fields(tmp_path, monkeypatch):
    source_file = tmp_path / "source_prd.md"
    source_file.write_text("# Source PRD", encoding="utf-8")
    captured: dict[str, str | None] = {}

    async def fake_run_job(job, *, prd_text=None, prd_path=None, source=None):
        captured["prd_text"] = prd_text
        captured["prd_path"] = prd_path
        captured["source"] = source
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
