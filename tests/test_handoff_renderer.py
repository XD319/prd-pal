from requirement_review_v1.handoff import render_claude_code_prompt, render_codex_prompt
from requirement_review_v1.packs import ExecutionPackBuilder


SAMPLE_REQUIREMENTS = [
    {
        "id": "REQ-101",
        "description": "Add recruiter SSO login support",
        "acceptance_criteria": ["SSO callback succeeds", "Existing login remains available"],
    }
]

SAMPLE_TASKS = [
    {
        "id": "TASK-101",
        "title": "Implement recruiter SSO login",
        "owner": "BE",
        "requirement_ids": ["REQ-101"],
    }
]

SAMPLE_RISKS = [
    {
        "id": "RISK-101",
        "description": "Legacy auth session may regress",
        "impact": "high",
        "mitigation": "Run targeted auth regression coverage",
        "owner": "qa",
    }
]

IMPLEMENTATION_PLAN = {
    "implementation_steps": ["Inspect auth flow", "Add SSO callback handler", "Preserve legacy login flow"],
    "target_modules": ["requirement_review_v1/server/app.py", "frontend/src/auth.ts"],
    "constraints": ["Do not break existing password login"],
}

TEST_PLAN = {
    "test_scope": ["SSO callback API", "Recruiter login UI"],
    "edge_cases": ["Expired state token"],
    "regression_focus": ["Password login regression"],
}

CODEX_PROMPT = {
    "agent_prompt": "Implement the smallest safe SSO change set and run focused checks.",
    "recommended_execution_order": ["Review auth modules", "Implement backend changes", "Verify SSO login"],
    "non_goals": ["Do not redesign user profile flows"],
    "validation_checklist": ["SSO flow mapped to tests"],
}

CLAUDE_PROMPT = {
    "agent_prompt": "Validate edge cases and regression coverage before handoff is complete.",
    "recommended_execution_order": ["Inspect changed files", "Add edge-case coverage", "Run auth regression checks"],
    "non_goals": ["Do not expand beyond auth validation"],
    "validation_checklist": ["Regression checks stay green"],
}


def _build_execution_pack():
    return ExecutionPackBuilder().build(
        requirements=SAMPLE_REQUIREMENTS,
        tasks=SAMPLE_TASKS,
        risks=SAMPLE_RISKS,
        implementation_plan_output=IMPLEMENTATION_PLAN,
        test_plan_output=TEST_PLAN,
        codex_prompt_output=CODEX_PROMPT,
        claude_code_prompt_output=CLAUDE_PROMPT,
    )


def test_render_codex_prompt_contains_required_sections() -> None:
    prompt = render_codex_prompt(_build_execution_pack())

    assert prompt.startswith("# Codex Handoff Prompt")
    for section in (
        "## Goal",
        "## Project Context",
        "## Required Changes",
        "## Constraints",
        "## Acceptance Criteria",
        "## Testing Requirements",
        "## Output Expectations",
    ):
        assert section in prompt
    assert "Add SSO callback handler" in prompt
    assert "`requirement_review_v1/server/app.py`" in prompt
    assert "Legacy auth session may regress" in prompt


def test_render_claude_code_prompt_uses_validation_focused_content() -> None:
    prompt = render_claude_code_prompt(_build_execution_pack().model_dump(mode="python"))

    assert prompt.startswith("# Claude Code Handoff Prompt")
    assert "Validate edge cases and regression coverage before handoff is complete." in prompt
    assert "Expired state token" in prompt
    assert "Regression checks stay green" in prompt
    assert "Do not expand scope beyond the execution pack." in prompt
