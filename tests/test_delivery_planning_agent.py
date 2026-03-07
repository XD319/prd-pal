from __future__ import annotations

from unittest.mock import patch

import pytest

from requirement_review_v1.agents import delivery_planning_agent
from requirement_review_v1.skills.executor import SkillExecutor
from requirement_review_v1.skills.registry import get_skill_spec
from requirement_review_v1.utils.llm_structured_call import StructuredCallError


@pytest.fixture(autouse=True)
def clear_skill_cache():
    SkillExecutor.clear_cache()
    yield
    SkillExecutor.clear_cache()


@pytest.mark.asyncio
async def test_delivery_planning_agent_populates_outputs_and_trace():
    async def fake_llm_structured_call(*, prompt, schema, metadata):
        if metadata["agent_name"] == "implementation.plan":
            return {
                "implementation_steps": ["Implement backend auth endpoint", "Wire login UI to API"],
                "target_modules": ["backend.auth", "frontend.login"],
                "constraints": ["Keep existing session cookie contract stable"],
            }
        if metadata["agent_name"] == "test.plan.generate":
            return {
                "test_scope": ["Auth API", "Login UI"],
                "edge_cases": ["Expired session", "Invalid OAuth callback"],
                "regression_focus": ["Password login", "Session persistence"],
            }
        raise AssertionError(f"unexpected skill: {metadata['agent_name']}")

    state = {
        "parsed_items": [{"id": "REQ-001", "description": "Support login", "acceptance_criteria": ["OAuth works"]}],
        "plan": {
            "tasks": [{"id": "T-1", "title": "Build login", "owner": "BE", "requirement_ids": ["REQ-001"], "depends_on": [], "estimate_days": 2}],
            "milestones": [],
            "dependencies": [],
            "estimation": {"total_days": 2, "buffer_days": 1},
        },
        "risks": [{"id": "R-1", "description": "Auth integration risk", "impact": "medium", "mitigation": "Stage rollout", "buffer_days": 1}],
        "trace": {},
    }

    with patch("requirement_review_v1.skills.delivery_planning.llm_structured_call", side_effect=fake_llm_structured_call):
        result = await delivery_planning_agent.run(state)

    assert result["implementation_plan"]["target_modules"] == ["backend.auth", "frontend.login"]
    assert result["test_plan"]["regression_focus"] == ["Password login", "Session persistence"]
    assert result["trace"]["implementation.plan"]["status"] == "ok"
    assert result["trace"]["test.plan.generate"]["status"] == "ok"
    assert result["trace"]["delivery_planning"]["status"] == "ok"
    assert get_skill_spec("implementation.plan").name == "implementation.plan"
    assert get_skill_spec("test.plan.generate").name == "test.plan.generate"


@pytest.mark.asyncio
async def test_delivery_planning_agent_returns_minimal_fallback_when_skill_fails():
    async def fake_llm_structured_call(*, prompt, schema, metadata):
        if metadata["agent_name"] == "implementation.plan":
            raise StructuredCallError("structured call failed", raw_output="", structured_mode="fallback")
        return {
            "test_scope": ["Auth API"],
            "edge_cases": ["Timeout while exchanging token"],
            "regression_focus": ["Session renewal"],
        }

    state = {
        "parsed_items": [{"id": "REQ-001", "description": "Support login", "acceptance_criteria": ["OAuth works"]}],
        "plan": {
            "tasks": [{"id": "T-1", "title": "Build login", "owner": "BE", "requirement_ids": ["REQ-001"], "depends_on": [], "estimate_days": 2}],
            "milestones": [],
            "dependencies": [],
            "estimation": {"total_days": 2, "buffer_days": 1},
        },
        "risks": [{"id": "R-1", "description": "Auth integration risk", "impact": "medium", "mitigation": "Stage rollout", "buffer_days": 1}],
        "trace": {},
    }

    with patch("requirement_review_v1.skills.delivery_planning.llm_structured_call", side_effect=fake_llm_structured_call):
        result = await delivery_planning_agent.run(state)

    assert result["implementation_plan"] == {
        "implementation_steps": [],
        "target_modules": [],
        "constraints": [],
    }
    assert result["test_plan"]["test_scope"] == ["Auth API"]
    assert result["trace"]["implementation.plan"]["status"] == "error"
    assert result["trace"]["test.plan.generate"]["status"] == "ok"
    assert result["trace"]["delivery_planning"]["status"] == "ok"
