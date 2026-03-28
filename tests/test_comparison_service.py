from __future__ import annotations

import json

from fastapi.testclient import TestClient

from requirement_review_v1.server import app as app_module
from requirement_review_v1.service.comparison_service import compare_runs, get_run_stats_summary, get_trend_data


def _write_report(tmp_path, run_id: str, payload: dict) -> None:
    run_dir = tmp_path / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_compare_runs_identifies_added_removed_and_changed_findings(tmp_path):
    _write_report(
        tmp_path,
        "20260309T010203Z",
        {
            "run_id": "20260309T010203Z",
            "created_at": "2026-03-09T01:02:03+00:00",
            "metrics": {"coverage_ratio": 0.80, "risk_score": 5.0},
            "parallel_review_meta": {"duration_ms": 1000},
            "parallel_review": {
                "findings": [
                    {"requirement_id": "REQ-001", "title": "Missing acceptance criteria", "severity": "high", "category": "clarity"},
                    {"requirement_id": "REQ-002", "title": "Test plan incomplete", "severity": "medium", "category": "testability"},
                ],
                "risk_items": [
                    {"id": "R-1", "title": "Rate limit gap", "description": "No rate limit defined", "severity": "high"},
                ],
                "open_questions": [
                    {"question": "Who owns rollout approval?"},
                    {"question": "What is the fallback path?"},
                ],
            },
        },
    )
    _write_report(
        tmp_path,
        "20260310T010203Z",
        {
            "run_id": "20260310T010203Z",
            "created_at": "2026-03-10T01:02:03+00:00",
            "metrics": {"coverage_ratio": 0.90, "risk_score": 3.0},
            "parallel_review_meta": {"duration_ms": 2000},
            "parallel_review": {
                "findings": [
                    {"requirement_id": "REQ-001", "title": "Missing measurable acceptance criteria", "severity": "high", "category": "clarity"},
                    {"requirement_id": "REQ-003", "title": "Audit logging unspecified", "severity": "medium", "category": "compliance"},
                ],
                "risk_items": [
                    {"id": "R-1", "title": "Rate limit gap", "description": "No rate limit defined", "severity": "medium"},
                    {"id": "R-2", "title": "Rollback gap", "description": "Rollback path not documented", "severity": "medium"},
                ],
                "open_questions": [
                    {"question": "Who owns rollout approval?"},
                    {"question": "How should rollback be validated?"},
                ],
            },
        },
    )

    result = compare_runs("20260309T010203Z", "20260310T010203Z", outputs_root=str(tmp_path))

    statuses = {item.requirement_id: item.status for item in result.findings}
    assert statuses["REQ-001"] == "changed"
    assert statuses["REQ-002"] == "removed"
    assert statuses["REQ-003"] == "added"
    assert result.metrics["coverage"].delta == 10.0
    assert result.metrics["risk_score"].delta == -2.0
    assert result.metrics["finding_count"].delta == 0.0
    assert len(result.open_questions.added) == 1
    assert len(result.open_questions.resolved) == 1
    assert result.summary["risks_added"] == 1
    assert result.summary["risks_changed"] == 1


def test_get_trend_data_returns_descending_time_series(tmp_path):
    _write_report(
        tmp_path,
        "20260308T010203Z",
        {
            "metrics": {"coverage_ratio": 0.70, "risk_score": 8.0},
            "parallel_review": {
                "findings": [{"requirement_id": "REQ-001", "severity": "high"}],
            },
        },
    )
    _write_report(
        tmp_path,
        "20260310T010203Z",
        {
            "metrics": {"coverage_ratio": 0.95, "risk_score": 2.0},
            "parallel_review": {
                "findings": [
                    {"requirement_id": "REQ-001", "severity": "high"},
                    {"requirement_id": "REQ-002", "severity": "medium"},
                ],
            },
        },
    )
    _write_report(
        tmp_path,
        "20260309T010203Z",
        {
            "metrics": {"coverage_ratio": 0.80, "risk_score": 5.0},
            "parallel_review": {
                "findings": [{"requirement_id": "REQ-001", "severity": "medium"}],
            },
        },
    )

    trend = get_trend_data(outputs_root=str(tmp_path), limit=3)

    assert [point.run_id for point in trend.points] == [
        "20260310T010203Z",
        "20260309T010203Z",
        "20260308T010203Z",
    ]
    assert trend.points[0].total_findings == 2
    assert trend.points[0].high_severity_count == 1
    assert trend.points[0].coverage_pct == 95.0


def test_trend_and_stats_handle_empty_and_single_run_boundaries(tmp_path):
    empty_trend = get_trend_data(outputs_root=str(tmp_path), limit=20)
    empty_stats = get_run_stats_summary(outputs_root=str(tmp_path))

    assert empty_trend.count == 0
    assert empty_trend.points == []
    assert empty_stats.total_runs == 0
    assert empty_stats.average_findings == 0.0
    assert empty_stats.average_review_duration_ms == 0.0

    _write_report(
        tmp_path,
        "20260311T010203Z",
        {
            "metrics": {"coverage_ratio": 0.88, "risk_score": 4.0},
            "parallel_review_meta": {"duration_ms": 1500},
            "parallel_review": {
                "findings": [
                    {"requirement_id": "REQ-001", "severity": "high", "category": "clarity"},
                    {"requirement_id": "REQ-002", "severity": "medium", "category": "clarity"},
                    {"requirement_id": "REQ-003", "severity": "medium", "category": "testability"},
                ],
            },
        },
    )

    single_trend = get_trend_data(outputs_root=str(tmp_path), limit=20)
    single_stats = get_run_stats_summary(outputs_root=str(tmp_path))

    assert single_trend.count == 1
    assert single_trend.points[0].run_id == "20260311T010203Z"
    assert single_stats.total_runs == 1
    assert single_stats.average_findings == 3.0
    assert single_stats.average_review_duration_ms == 1500.0
    assert single_stats.top_issue_types[0].issue_type == "clarity"
    assert single_stats.top_issue_types[0].count == 2


def test_compare_trends_and_stats_api_endpoints(tmp_path, monkeypatch):
    _write_report(
        tmp_path,
        "20260309T010203Z",
        {
            "metrics": {"coverage_ratio": 0.75, "risk_score": 6.0},
            "parallel_review_meta": {"duration_ms": 1200},
            "parallel_review": {
                "findings": [{"requirement_id": "REQ-001", "title": "Gap A", "severity": "high", "category": "clarity"}],
                "risk_items": [{"id": "R-1", "title": "Risk A", "description": "Legacy risk"}],
                "open_questions": [{"question": "Question A?"}],
            },
        },
    )
    _write_report(
        tmp_path,
        "20260310T010203Z",
        {
            "metrics": {"coverage_ratio": 0.85, "risk_score": 4.0},
            "parallel_review_meta": {"duration_ms": 1800},
            "parallel_review": {
                "findings": [
                    {"requirement_id": "REQ-001", "title": "Gap A updated", "severity": "high", "category": "clarity"},
                    {"requirement_id": "REQ-002", "title": "Gap B", "severity": "medium", "category": "testability"},
                ],
                "risk_items": [{"id": "R-1", "title": "Risk A", "description": "Legacy risk updated"}],
                "open_questions": [{"question": "Question B?"}],
            },
        },
    )

    monkeypatch.setattr(app_module, "OUTPUTS_ROOT", tmp_path)
    app_module._jobs.clear()
    client = TestClient(app_module.app)

    compare_response = client.get("/api/compare", params={"run_a": "20260309T010203Z", "run_b": "20260310T010203Z"})
    trends_response = client.get("/api/trends", params={"limit": 20})
    stats_response = client.get("/api/stats")

    assert compare_response.status_code == 200
    compare_payload = compare_response.json()
    assert compare_payload["run_a"] == "20260309T010203Z"
    assert compare_payload["run_b"] == "20260310T010203Z"
    assert any(item["status"] == "added" and item["requirement_id"] == "REQ-002" for item in compare_payload["findings"])

    assert trends_response.status_code == 200
    trends_payload = trends_response.json()
    assert trends_payload["count"] == 2
    assert isinstance(trends_payload["points"], list)

    assert stats_response.status_code == 200
    stats_payload = stats_response.json()
    assert stats_payload["total_runs"] == 2
    assert stats_payload["average_review_duration_ms"] == 1500.0
    app_module._jobs.clear()
