import json

from requirement_review_v1.review.aggregator import aggregate_review_results
from requirement_review_v1.review.reviewer_agents.base import ReviewFinding, ReviewerResult, RiskItem


_MANUAL_REVIEW_TEXT = "\u9700\u4eba\u5de5\u8865\u5ba1"
_MANUAL_REVIEW_MESSAGE = (
    "\u9700\u4eba\u5de5\u8865\u5ba1\uff1a\u5b58\u5728\u9ad8\u98ce\u9669\u95ee\u9898\uff0c"
    "\u4e14\u4ee5\u4e0b reviewer \u7f3a\u5931\u6216\u5931\u8d25\uff1aqa (failed: timeout)"
)


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


def _find_conflict(conflicts: tuple[dict[str, object], ...], conflict_type: str) -> dict[str, object]:
    for conflict in conflicts:
        if conflict["type"] == conflict_type:
            return conflict
    raise AssertionError(f"conflict not found: {conflict_type}")


def test_aggregate_review_results_writes_new_schema_and_legacy_aliases(tmp_path):
    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    aggregated = aggregate_review_results(_reviewer_results(), first_output)
    aggregated_again = aggregate_review_results(_reviewer_results(), second_output)

    assert aggregated.reviewer_count == 3
    assert aggregated.partial_review is True
    assert aggregated.reviewers_completed == ("product", "security")
    assert aggregated.reviewers_failed == ({"reviewer": "qa", "status": "failed", "reason": "timeout"},)
    assert aggregated.meta == {
        "review_mode": "parallel_review",
        "partial_review": True,
        "reviewers_completed": ["product", "security"],
        "reviewers_failed": [{"reviewer": "qa", "status": "failed", "reason": "timeout"}],
        "manual_review_required": True,
        "manual_review_message": _MANUAL_REVIEW_MESSAGE,
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
    conflict = aggregated.conflicts[0]
    assert conflict["conflict_id"] == aggregated_again.conflicts[0]["conflict_id"]
    assert conflict["type"] == "severity_mismatch"
    assert conflict["status"] == "severity_mismatch"
    assert conflict["topic"] == "Security review gate required"
    assert conflict["reviewers"] == ["product", "security"]
    assert conflict["requires_manual_resolution"] is True
    assert conflict["description"] == (
        "Severity mismatch on 'Security review gate required': findings use medium, high while risks use high."
    )

    review_result_payload = json.loads((first_output / "review_result.json").read_text(encoding="utf-8"))
    legacy_report_payload = json.loads((first_output / "review_report.json").read_text(encoding="utf-8"))
    risk_payload = json.loads((first_output / "risk_items.json").read_text(encoding="utf-8"))
    question_payload = json.loads((first_output / "open_questions.json").read_text(encoding="utf-8"))
    review_report_text = (first_output / "review_report.md").read_text(encoding="utf-8")
    summary_text = (first_output / "review_summary.md").read_text(encoding="utf-8")

    assert review_result_payload == legacy_report_payload
    assert review_result_payload["partial_review"] is True
    assert review_result_payload["reviewers_completed"] == ["product", "security"]
    assert review_result_payload["reviewers_failed"] == [{"reviewer": "qa", "status": "failed", "reason": "timeout"}]
    assert review_result_payload["manual_review_required"] is True
    assert _MANUAL_REVIEW_TEXT in review_result_payload["manual_review_message"]
    assert review_result_payload["findings"][0]["finding_id"] == finding["finding_id"]
    assert review_result_payload["conflicts"][0]["conflict_id"] == conflict["conflict_id"]
    assert len(risk_payload["risk_items"]) == 1
    assert len(question_payload["open_questions"]) == 1
    assert "# Review Report" in review_report_text
    assert finding["finding_id"] in review_report_text
    assert conflict["description"] in review_report_text
    assert _MANUAL_REVIEW_TEXT in review_report_text
    assert "# Review Summary" in summary_text
    assert "Security review gate required" in summary_text
    assert conflict["description"] in summary_text
    assert _MANUAL_REVIEW_TEXT in summary_text

    artifacts = aggregated.artifacts
    assert artifacts.review_result_json.endswith("review_result.json")
    assert artifacts.review_report_md.endswith("review_report.md")
    assert artifacts.review_report_json.endswith("review_report.json")
    assert artifacts.review_summary_md.endswith("review_summary.md")


def test_detects_scope_inclusion_vs_dependency_blocker_conflict(tmp_path):
    aggregated = aggregate_review_results(
        [
            ReviewerResult(
                reviewer="product",
                summary="The requested scope is included in the current PRD and the scenarios are within scope.",
            ),
            ReviewerResult(
                reviewer="engineering",
                findings=(
                    ReviewFinding(
                        title="Dependency blocker remains",
                        detail="Shared dependencies still block implementation sequencing.",
                        severity="high",
                        category="architecture",
                        reviewer="engineering",
                    ),
                ),
                summary="Engineering found a dependency blocker across shared services.",
            ),
        ],
        tmp_path,
    )

    conflict = _find_conflict(aggregated.conflicts, "scope_inclusion_vs_dependency_blocker")
    assert conflict["reviewers"] == ["product", "engineering"]
    assert conflict["requires_manual_resolution"] is True
    assert conflict["description"] == (
        "Product indicates the requested scope is already covered, but Engineering flags dependency blockers that can stop or delay implementation."
    )


def test_detects_acceptance_complete_vs_testability_gap_conflict(tmp_path):
    aggregated = aggregate_review_results(
        [
            ReviewerResult(
                reviewer="product",
                summary="Acceptance criteria are complete and ready for QA sign off.",
            ),
            ReviewerResult(
                reviewer="qa",
                findings=(
                    ReviewFinding(
                        title="Testability gap remains",
                        detail="QA cannot derive pass/fail expectations for the highest-risk edge cases.",
                        severity="medium",
                        category="testability",
                        reviewer="qa",
                    ),
                ),
                summary="QA still sees a testability gap around rollback coverage.",
            ),
        ],
        tmp_path,
    )

    conflict = _find_conflict(aggregated.conflicts, "acceptance_complete_vs_testability_gap")
    assert conflict["reviewers"] == ["product", "qa"]
    assert conflict["requires_manual_resolution"] is True
    assert conflict["description"] == (
        "Product indicates the acceptance criteria are complete, but QA identifies a testability gap that leaves QA without reliable pass/fail coverage."
    )


def test_detects_release_ok_vs_approval_blocker_conflict(tmp_path):
    aggregated = aggregate_review_results(
        [
            ReviewerResult(
                reviewer="product",
                summary="Release is ok and the feature is ready for release.",
            ),
            ReviewerResult(
                reviewer="security",
                risk_items=(
                    RiskItem(
                        title="Security review gate required",
                        detail="Sensitive data handling cannot release until approval is recorded.",
                        severity="high",
                        category="security",
                        mitigation="Keep the release blocked until the security approval is signed.",
                        reviewer="security",
                    ),
                ),
                summary="Security still treats this as an approval blocker before release.",
            ),
        ],
        tmp_path,
    )

    conflict = _find_conflict(aggregated.conflicts, "release_ok_vs_approval_blocker")
    assert conflict["reviewers"] == ["product", "security"]
    assert conflict["requires_manual_resolution"] is True
    assert conflict["description"] == (
        "Product marks the release as ready to proceed, but Security still requires an approval gate before release."
    )
