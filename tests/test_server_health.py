from __future__ import annotations

from fastapi.testclient import TestClient

from prd_pal.server import app as app_module


def test_health_endpoint_returns_healthy_payload() -> None:
    with TestClient(app_module.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "status": "healthy",
        "service": "requirement-review-v1",
    }


def test_ready_endpoint_checks_startup_and_outputs_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)

    with TestClient(app_module.app) as client:
        response = client.get("/ready")

    payload = response.json()
    assert response.status_code == 200
    assert payload["ok"] is True
    assert payload["status"] == "ready"
    assert payload["checks"]["startup_completed"] is True
    assert payload["checks"]["outputs_root_writable"] is True

