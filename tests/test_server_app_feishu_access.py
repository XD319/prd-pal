from __future__ import annotations

import json

from fastapi.testclient import TestClient

from requirement_review_v1.server import app as app_module


def _build_client() -> TestClient:
    return TestClient(app_module.app)


def _write_feishu_run_fixture(tmp_path, run_id: str, *, submitter_open_id: str = "ou_owner", tenant_key: str = "tenant-a") -> None:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True)
    report_payload = {
        "run_id": run_id,
        "mode": "quick",
        "review_mode": "quick",
        "trace": {"reviewer": {"status": "ok"}},
    }
    (run_dir / "report.md").write_text("# Review Report", encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "run_trace.json").write_text("{}", encoding="utf-8")
    (run_dir / "entry_context.json").write_text(
        json.dumps(
            {
                "source_origin": "feishu",
                "entry_mode": "plugin",
                "submitter_open_id": submitter_open_id,
                "tenant_key": tenant_key,
                "trigger_source": "feishu",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_get_review_result_allows_matching_feishu_context(tmp_path, monkeypatch):
    run_id = "20260409T120001Z"
    _write_feishu_run_fixture(tmp_path, run_id)
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = _build_client()
    response = client.get(f"/api/review/{run_id}/result?open_id=ou_owner&tenant_key=tenant-a")

    assert response.status_code == 200
    assert response.json()["run_id"] == run_id


def test_get_review_result_rejects_mismatched_feishu_context(tmp_path, monkeypatch):
    run_id = "20260409T120002Z"
    _write_feishu_run_fixture(tmp_path, run_id)
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()

    client = _build_client()
    response = client.get(f"/api/review/{run_id}/result?open_id=ou_other&tenant_key=tenant-a")

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "code": "run_access_denied",
        "message": "This run is not accessible to the current Feishu user.",
    }
