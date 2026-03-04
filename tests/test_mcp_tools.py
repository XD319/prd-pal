from __future__ import annotations

import pytest

from requirement_review_v1.mcp_server import server as mcp_server
from requirement_review_v1.service import review_service
from requirement_review_v1.service.review_service import ReviewResultSummary


@pytest.mark.asyncio
async def test_review_prd_routes_to_review_service_with_mock(monkeypatch):
    fixed = ReviewResultSummary(
        run_id="20260304T120000Z",
        report_md_path="outputs/20260304T120000Z/report.md",
        report_json_path="outputs/20260304T120000Z/report.json",
        high_risk_ratio=0.25,
        coverage_ratio=0.8,
        revision_round=1,
        status="completed",
        run_trace_path="outputs/20260304T120000Z/run_trace.json",
    )

    async def fake_review_prd_text_async(
        prd_text: str,
        *,
        run_id: str | None = None,
        config_overrides: dict[str, object] | None = None,
    ) -> ReviewResultSummary:
        assert prd_text == "mock prd"
        assert run_id is None
        assert isinstance(config_overrides, dict)
        return fixed

    monkeypatch.setattr(review_service, "review_prd_text", lambda *args, **kwargs: fixed)
    monkeypatch.setattr(review_service, "review_prd_text_async", fake_review_prd_text_async)

    result = await mcp_server.review_prd(prd_text="mock prd")

    assert "error" not in result
    assert result["run_id"] == fixed.run_id
    assert result["status"] == "completed"
    assert result["metrics"]["coverage_ratio"] == fixed.coverage_ratio
    assert result["metrics"]["high_risk_ratio"] == fixed.high_risk_ratio
    assert result["metrics"]["revision_round"] == fixed.revision_round
    assert result["artifacts"]["report_md_path"] == fixed.report_md_path
    assert result["artifacts"]["report_json_path"] == fixed.report_json_path
    assert result["artifacts"]["trace_path"] == fixed.run_trace_path


@pytest.mark.asyncio
async def test_review_prd_rejects_missing_prd_text_and_path():
    result = await mcp_server.review_prd()

    assert result["status"] == "failed"
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_review_prd_rejects_both_prd_text_and_path():
    result = await mcp_server.review_prd(prd_text="text", prd_path="docs/sample_prd.md")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_review_prd_rejects_invalid_prd_path():
    result = await mcp_server.review_prd(prd_path="docs/not_exists_prd.md")

    assert result["status"] == "failed"
    assert result["error"]["code"] == "PRD_NOT_FOUND"


def test_get_report_rejects_invalid_run_id_via_tool_handler(tmp_path):
    result = mcp_server.get_report(run_id="../escape", options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "invalid_run_id"


def test_get_report_returns_not_found_via_tool_handler(tmp_path):
    result = mcp_server.get_report(run_id="20260304T010203Z", options={"outputs_root": str(tmp_path)})

    assert result["error"]["code"] == "not_found"
