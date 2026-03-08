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
    assert (tmp_path / "review_report.json").exists()
    assert (tmp_path / "risk_items.json").exists()
    assert (tmp_path / "open_questions.json").exists()
    assert (tmp_path / "review_summary.md").exists()
    assert artifacts["review_report_json"].endswith("review_report.json")

    review_report = json.loads((tmp_path / "review_report.json").read_text(encoding="utf-8"))
    assert review_report["reviewer_count"] == 4
    assert len(review_report["risk_items"]) >= 1
    assert "Security review gate required" in json.dumps(review_report, ensure_ascii=False)
