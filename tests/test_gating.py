from requirement_review_v1.review import GatingConfig, decide_review_mode


def test_low_complexity_requirement_uses_single_review():
    prd_text = """
# Candidate portal login

Allow recruiters to sign in with email and password.

## Scenarios
- Recruiter opens the login page and submits valid credentials.

## Acceptance Criteria
- User reaches the dashboard after successful login.
- Invalid credentials show an inline error message.
"""

    decision = decide_review_mode(prd_text)

    assert decision.mode == "single_review"
    assert decision.complexity_score == 0
    assert decision.module_count == 0
    assert decision.cross_system_hits == 0


def test_high_complexity_requirement_uses_parallel_review():
    prd_text = """
# Cross-system billing sync

This feature updates recruiter billing status across several systems and requires coordination across FE, BE, QA, DevOps, and Security.

## Modules
- `billing-api`
- `recruiter-portal`
- `finance-worker`
- `audit-service`

## Scenarios
- Finance updates a subscription and the recruiter portal reflects the new quota.
- The backend retries an external webhook when the downstream finance platform is unavailable.

## Acceptance Criteria
- The recruiter portal shows the latest subscription state.
- The webhook retry flow preserves idempotent writes and audit logs.
- Rollback steps are documented for payment incidents.
"""

    decision = decide_review_mode(prd_text)

    assert decision.mode == "parallel_review"
    assert decision.complexity_score >= 4
    assert decision.module_count >= 4
    assert decision.role_count >= 5
    assert decision.cross_system_hits >= 1


def test_risk_keyword_threshold_switches_to_parallel_review():
    config = GatingConfig(risk_keyword_threshold=3, parallel_score_threshold=5)
    below_threshold_text = """
# Login copy updates

Small wording updates for the login page.

## Notes
- Add a security reminder on the page.
- Capture an audit entry when the copy is published.
"""
    at_threshold_text = """
# Sensitive profile export

Add a CSV export for admin users.

## Notes
- Security review is required before launch.
- An audit trail must record each export action.
- Define a rollback plan if the export format causes issues.
"""

    below_threshold = decide_review_mode(below_threshold_text, config=config)
    at_threshold = decide_review_mode(at_threshold_text, config=config)

    assert below_threshold.mode == "single_review"
    assert below_threshold.risk_keyword_hits == 2
    assert at_threshold.mode == "parallel_review"
    assert at_threshold.risk_keyword_hits == 3
