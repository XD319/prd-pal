import json

from requirement_review_v1.review.aggregator import aggregate_review_results
from requirement_review_v1.review.reviewer_agents.base import ReviewFinding, ReviewerResult, RiskItem


def test_aggregate_review_results_dedupes_and_marks_conflicts(tmp_path):
    reviewer_results = [
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
    ]

    aggregated = aggregate_review_results(reviewer_results, tmp_path)

    assert aggregated.reviewer_count == 2
    assert len(aggregated.findings) == 1
    assert aggregated.findings[0]["severity"] == "high"
    assert aggregated.findings[0]["reviewers"] == ["product", "security"]
    assert len(aggregated.open_questions) == 1
    assert aggregated.open_questions[0]["reviewers"] == ["product", "security"]
    assert len(aggregated.risk_items) == 1
    assert len(aggregated.conflicts) == 1
    assert aggregated.conflicts[0]["status"] == "severity_mismatch"

    report_payload = json.loads((tmp_path / "review_report.json").read_text(encoding="utf-8"))
    risk_payload = json.loads((tmp_path / "risk_items.json").read_text(encoding="utf-8"))
    question_payload = json.loads((tmp_path / "open_questions.json").read_text(encoding="utf-8"))
    summary_text = (tmp_path / "review_summary.md").read_text(encoding="utf-8")

    assert report_payload["reviewer_count"] == 2
    assert len(risk_payload["risk_items"]) == 1
    assert len(question_payload["open_questions"]) == 1
    assert "# Review Summary" in summary_text
    assert "Security review gate required" in summary_text
