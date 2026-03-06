from fastapi.testclient import TestClient

from requirement_review_v1.server.app import app


client = TestClient(app)


def test_root_serves_frontend_shell() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Requirement Review Studio" in response.text
    assert '<div id="root"></div>' in response.text


def test_frontend_index_is_available_under_site_mount() -> None:
    response = client.get("/site/index.html")

    assert response.status_code == 200
    assert "Requirement Review Studio" in response.text
