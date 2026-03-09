import asyncio
import json

import pytest

from requirement_review_v1.review import parallel_review_manager as manager
from requirement_review_v1.review.parallel_review_manager import run_parallel_review_async
from requirement_review_v1.review.reviewer_agents.base import ReviewerResult, RiskItem


_MANUAL_REVIEW_TEXT = "\u9700\u4eba\u5de5\u8865\u5ba1"


@pytest.mark.asyncio
async def test_parallel_review_manager_runs_reviewers_and_writes_outputs(tmp_path):
    prd_text = """
# Recruiter profile export

Allow admin users to export recruiter profiles to a CSV file. This touches FE, BE, QA, and Security.

## Modules
- `admin-portal`
- `profile-service`
- `audit-service`

## Scenarios
- Admin exports a filtered list of recruiter profiles.
- The backend retries an external audit webhook when delivery fails.

## Acceptance Criteria
- Export completes within the admin portal flow.
- Each export writes an audit record.
- Rollback guidance exists for malformed exports.
"""

    result = await run_parallel_review_async(prd_text, tmp_path)

    assert result.normalized_requirement["summary"]
    assert set(result.reviewer_inputs) == {"product", "engineering", "qa", "security"}
    assert len(result.reviewer_results) == 4

    reviewers = {item["reviewer"] for item in result.reviewer_results}
    assert reviewers == {"product", "engineering", "qa", "security"}

    aggregated = result.aggregated
    artifacts = aggregated["artifacts"]
    assert (tmp_path / "review_result.json").exists()
    assert (tmp_path / "review_report.md").exists()
    assert (tmp_path / "review_report.json").exists()
    assert (tmp_path / "risk_items.json").exists()
    assert (tmp_path / "open_questions.json").exists()
    assert (tmp_path / "review_summary.md").exists()
    assert artifacts["review_result_json"].endswith("review_result.json")
    assert artifacts["review_report_md"].endswith("review_report.md")
    assert artifacts["review_report_json"].endswith("review_report.json")

    review_result = json.loads((tmp_path / "review_result.json").read_text(encoding="utf-8"))
    legacy_report = json.loads((tmp_path / "review_report.json").read_text(encoding="utf-8"))
    assert review_result == legacy_report
    assert review_result["reviewer_count"] == 4
    assert review_result["partial_review"] is False
    assert review_result["reviewers_completed"] == ["product", "engineering", "qa", "security"]
    assert review_result["reviewers_failed"] == []
    assert review_result["meta"] == {
        "review_mode": "parallel_review",
        "partial_review": False,
        "reviewers_completed": ["product", "engineering", "qa", "security"],
        "reviewers_failed": [],
        "manual_review_required": False,
        "manual_review_message": "",
    }
    assert len(review_result["risk_items"]) >= 1
    assert all("finding_id" in item for item in review_result["findings"])
    assert all("source_reviewer" in item for item in review_result["findings"])
    assert all("suggested_action" in item for item in review_result["findings"])
    assert all("assignee" in item for item in review_result["findings"])
    assert "Security review gate required" in json.dumps(review_result, ensure_ascii=False)


@pytest.mark.asyncio
async def test_parallel_review_manager_returns_partial_results_for_timeout_and_error(monkeypatch, tmp_path):
    async def fake_product(_requirement, config=None):
        return ReviewerResult(reviewer="product", summary="Product completed.")

    async def slow_engineering(_requirement, config=None):
        await asyncio.sleep(0.05)
        return ReviewerResult(reviewer="engineering", summary="Engineering completed.")

    async def broken_qa(_requirement, config=None):
        raise RuntimeError("qa boom")

    async def fake_security(_requirement, config=None):
        return ReviewerResult(
            reviewer="security",
            risk_items=(
                RiskItem(
                    title="Security gate required",
                    detail="Sensitive export requires explicit release approval.",
                    severity="high",
                    category="security",
                    mitigation="Add manual release approval.",
                    reviewer="security",
                ),
            ),
            summary="Security completed.",
        )

    monkeypatch.setattr(
        manager,
        "_REVIEWER_FUNCTIONS",
        {
            "product": fake_product,
            "engineering": slow_engineering,
            "qa": broken_qa,
            "security": fake_security,
        },
    )

    result = await run_parallel_review_async(
        "Sensitive export PRD",
        tmp_path,
        reviewer_timeouts={"product": 1.0, "engineering": 0.01, "qa": 1.0, "security": 1.0},
    )

    reviewer_results = {item["reviewer"]: item for item in result.reviewer_results}
    assert reviewer_results["product"]["status"] == "completed"
    assert reviewer_results["security"]["status"] == "completed"
    assert reviewer_results["engineering"]["status"] == "timeout"
    assert reviewer_results["engineering"]["error_message"] == "timed out after 0.0s"
    assert reviewer_results["engineering"]["findings"] == []
    assert reviewer_results["engineering"]["open_questions"] == []
    assert reviewer_results["engineering"]["risk_items"] == []
    assert reviewer_results["qa"]["status"] == "error"
    assert reviewer_results["qa"]["error_message"] == "qa boom"
    assert reviewer_results["qa"]["findings"] == []
    assert reviewer_results["qa"]["open_questions"] == []
    assert reviewer_results["qa"]["risk_items"] == []

    aggregated = result.aggregated
    assert aggregated["partial_review"] is True
    assert aggregated["reviewers_completed"] == ("product", "security")
    assert aggregated["reviewers_failed"] == (
        {"reviewer": "engineering", "status": "timeout", "reason": "timed out after 0.0s"},
        {"reviewer": "qa", "status": "error", "reason": "qa boom"},
    )
    assert aggregated["meta"]["partial_review"] is True
    assert aggregated["meta"]["manual_review_required"] is True
    assert _MANUAL_REVIEW_TEXT in aggregated["meta"]["manual_review_message"]

    summary_text = (tmp_path / "review_summary.md").read_text(encoding="utf-8")
    report_text = (tmp_path / "review_report.md").read_text(encoding="utf-8")
    assert _MANUAL_REVIEW_TEXT in summary_text
    assert _MANUAL_REVIEW_TEXT in report_text
