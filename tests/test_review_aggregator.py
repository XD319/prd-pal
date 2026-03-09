import json

from requirement_review_v1.review.aggregator import aggregate_review_results
from requirement_review_v1.review.reviewer_agents.base import ReviewFinding, ReviewerResult, RiskItem


def _reviewer_results() -> list[ReviewerResult]:
    return [
        ReviewerResult(
            reviewer="product",
            findings=(
                ReviewFinding(
                    title="Security review gate required",
                    detail="Sensitive flows need a release gate.",
                    severity="medium",
                    category="security",
                    reviewer="product",
                ),
            ),
            open_questions=("Who approves the final release gate?",),
            summary="Product summary.",
        ),
        ReviewerResult(
            reviewer="security",
            findings=(
                ReviewFinding(
                    title="Security review gate required",
                    detail="Sensitive flows need a release gate.",
                    severity="high",
                    category="security",
                    reviewer="security",
                ),
            ),
            open_questions=("Who approves the final release gate?",),
            risk_items=(
                RiskItem(
                    title="Security review gate required",
                    detail="Sensitive flows need a release gate.",
                    severity="high",
                    category="security",
                    mitigation="Add a formal approval step.",
                    reviewer="security",
                ),
            ),
            summary="Security summary.",
        ),
        ReviewerResult(
            reviewer="qa",
            summary="QA reviewer timed out.",
            status="failed",
            error_message="timeout",
        ),
    ]


def test_aggregate_review_results_writes_new_schema_and_legacy_aliases(tmp_path):
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    aggregated = aggregate_review_results(_reviewer_results(), first_output)
    aggregated_again = aggregate_review_results(_reviewer_results(), second_output)

    assert aggregated.reviewer_count == 3
    assert aggregated.meta == {
        "review_mode": "parallel_review",
        "reviewers_completed": ["product", "security"],
        "reviewers_failed": [{"reviewer": "qa", "status": "failed", "reason": "timeout"}],
    }

    assert len(aggregated.findings) == 1
    finding = aggregated.findings[0]
    assert finding["finding_id"] == aggregated_again.findings[0]["finding_id"]
    assert finding["severity"] == "high"
    assert finding["source_reviewer"] == "product"
    assert finding["reviewers"] == ["product", "security"]
    assert finding["description"] == "Sensitive flows need a release gate."
    assert finding["suggested_action"] == "Add explicit security, compliance, and release-control expectations to the PRD."
    assert finding["assignee"] == "security"

    assert len(aggregated.open_questions) == 1
    assert aggregated.open_questions[0]["reviewers"] == ["product", "security"]
    assert len(aggregated.risk_items) == 1
    assert len(aggregated.conflicts) == 1
    assert aggregated.conflicts[0]["status"] == "severity_mismatch"

    review_result_payload = json.loads((first_output / "review_result.json").read_text(encoding="utf-8"))
    legacy_report_payload = json.loads((first_output / "review_report.json").read_text(encoding="utf-8"))
    risk_payload = json.loads((first_output / "risk_items.json").read_text(encoding="utf-8"))
    question_payload = json.loads((first_output / "open_questions.json").read_text(encoding="utf-8"))
    review_report_text = (first_output / "review_report.md").read_text(encoding="utf-8")
    summary_text = (first_output / "review_summary.md").read_text(encoding="utf-8")

    assert review_result_payload == legacy_report_payload
    assert review_result_payload["meta"]["review_mode"] == "parallel_review"
    assert review_result_payload["findings"][0]["finding_id"] == finding["finding_id"]
    assert len(risk_payload["risk_items"]) == 1
    assert len(question_payload["open_questions"]) == 1
    assert "# Review Report" in review_report_text
    assert finding["finding_id"] in review_report_text
    assert "# Review Summary" in summary_text
    assert "Security review gate required" in summary_text

    artifacts = aggregated.artifacts
    assert artifacts.review_result_json.endswith("review_result.json")
    assert artifacts.review_report_md.endswith("review_report.md")
    assert artifacts.review_report_json.endswith("review_report.json")
    assert artifacts.review_summary_md.endswith("review_summary.md")
