from pathlib import Path

from fastapi.testclient import TestClient

import requirement_review_v1.server.app as server_app


client = TestClient(server_app.app)


def test_root_serves_frontend_shell() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Requirement Review Studio" in response.text
    assert '<div id="root"></div>' in response.text


def test_frontend_index_is_available_under_site_mount() -> None:
    response = client.get("/site/index.html")

    assert response.status_code == 200
    assert "Requirement Review Studio" in response.text


def test_review_progress_websocket_streams_job_snapshot() -> None:
    run_id = "ws-test-run"
    run_dir = Path("outputs") / run_id
    job = server_app.JobRecord(run_id=run_id, run_dir=run_dir, status="running", current_node="planner")
    job.node_progress["planner"]["status"] = "running"
    job.node_progress["planner"]["runs"] = 1
    server_app._jobs[run_id] = job

    try:
        with client.websocket_connect(f"/ws/review/{run_id}") as websocket:
            payload = websocket.receive_json()

        assert payload["run_id"] == run_id
        assert payload["status"] == "running"
        assert payload["progress"]["current_node"] == "planner"
        assert payload["progress"]["nodes"]["planner"]["status"] == "running"
    finally:
        server_app._jobs.pop(run_id, None)
