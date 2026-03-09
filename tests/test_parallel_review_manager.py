import json

import pytest

from requirement_review_v1.review.parallel_review_manager import run_parallel_review_async


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
    assert review_result["meta"] == {
        "review_mode": "parallel_review",
        "reviewers_completed": ["product", "engineering", "qa", "security"],
        "reviewers_failed": [],
    }
    assert len(review_result["risk_items"]) >= 1
    assert all("finding_id" in item for item in review_result["findings"])
    assert all("source_reviewer" in item for item in review_result["findings"])
    assert all("suggested_action" in item for item in review_result["findings"])
    assert all("assignee" in item for item in review_result["findings"])
    assert "Security review gate required" in json.dumps(review_result, ensure_ascii=False)
