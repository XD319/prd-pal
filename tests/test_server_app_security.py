from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from requirement_review_v1.server import app as app_module


def _build_client() -> TestClient:
    return TestClient(app_module.app)


def _reset_state() -> None:
    app_module._jobs.clear()
    app_module._reset_submission_rate_limits()


def test_create_review_accepts_authorized_bearer_request(tmp_path, monkeypatch):
    run_ids = iter(["20260310T020301Z"])
    monkeypatch.setenv("MARRDP_API_AUTH_DISABLED", "false")
    monkeypatch.setenv("MARRDP_API_BEARER_TOKEN", "shared-bearer-token")
    monkeypatch.setenv("MARRDP_API_RATE_LIMIT_DISABLED", "true")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr(app_module, "make_run_id", lambda: next(run_ids))
    monkeypatch.setattr(app_module, "_run_job", AsyncMock(return_value=None))
    _reset_state()

    client = _build_client()
    response = client.post(
        "/api/review",
        json={"prd_text": "# Shared review"},
        headers={"Authorization": "Bearer shared-bearer-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"run_id": "20260310T020301Z"}
    assert "20260310T020301Z" in app_module._jobs
    _reset_state()


def test_create_review_rejects_unauthorized_request(tmp_path, monkeypatch):
    monkeypatch.setenv("MARRDP_API_AUTH_DISABLED", "false")
    monkeypatch.setenv("MARRDP_API_KEY", "shared-api-key")
    monkeypatch.setenv("MARRDP_API_RATE_LIMIT_DISABLED", "true")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr(app_module, "_run_job", AsyncMock(return_value=None))
    _reset_state()

    client = _build_client()
    response = client.post("/api/review", json={"prd_text": "# Shared review"})

    assert response.status_code == 401
    assert response.json()["detail"] == {
        "code": "authentication_required",
        "message": "Provide a valid X-API-Key header or Authorization: Bearer token.",
    }
    assert app_module._jobs == {}
    _reset_state()


def test_create_review_enforces_rate_limit_for_submission_endpoint(tmp_path, monkeypatch):
    run_ids = iter(["20260310T020302Z"])
    monkeypatch.setenv("MARRDP_API_AUTH_DISABLED", "false")
    monkeypatch.setenv("MARRDP_API_KEY", "shared-api-key")
    monkeypatch.setenv("MARRDP_API_RATE_LIMIT_DISABLED", "false")
    monkeypatch.setenv("MARRDP_API_RATE_LIMIT_MAX_REQUESTS", "1")
    monkeypatch.setenv("MARRDP_API_RATE_LIMIT_WINDOW_SEC", "60")
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr(app_module, "make_run_id", lambda: next(run_ids))
    monkeypatch.setattr(app_module, "_run_job", AsyncMock(return_value=None))
    _reset_state()

    client = _build_client()
    first = client.post(
        "/api/review",
        json={"prd_text": "# Shared review"},
        headers={"X-API-Key": "shared-api-key"},
    )
    second = client.post(
        "/api/review",
        json={"prd_text": "# Shared review"},
        headers={"X-API-Key": "shared-api-key"},
    )

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"]
    assert second.json()["detail"]["code"] == "rate_limit_exceeded"
    assert second.json()["detail"]["limit"] == 1
    assert second.json()["detail"]["window_sec"] == 60
    _reset_state()
