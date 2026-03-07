"""Delivery planning node that enriches the base plan with execution skills."""

from __future__ import annotations

import json
from typing import Any

from ..skills import get_skill_executor, get_skill_spec
from ..state import ReviewState, plan_from_state
from ..utils.trace import trace_start

_AGENT = "delivery_planning"
_IMPLEMENTATION_SKILL = "implementation.plan"
_TEST_PLAN_SKILL = "test.plan.generate"


def _empty_implementation_plan() -> dict[str, list[str]]:
    return {
        "implementation_steps": [],
        "target_modules": [],
        "constraints": [],
    }


def _empty_test_plan() -> dict[str, list[str]]:
    return {
        "test_scope": [],
        "edge_cases": [],
        "regression_focus": [],
    }


async def run(state: ReviewState) -> ReviewState:
    parsed_items: list[dict[str, Any]] = list(state.get("parsed_items", []) or [])
    risks: list[dict[str, Any]] = list(state.get("risks", []) or [])
    plan = plan_from_state(state)
    tasks: list[dict[str, Any]] = list(plan.get("tasks", []) or [])
    trace: dict[str, Any] = dict(state.get("trace", {}))

    payload = {
        "structured_requirements": parsed_items,
        "tasks": tasks,
        "risks": risks,
    }
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    span = trace_start(_AGENT, model="none", input_chars=len(payload_json))

    implementation_plan = _empty_implementation_plan()
    test_plan = _empty_test_plan()
    degraded_skills: list[str] = []
    executor = get_skill_executor()

    try:
        implementation_output = await executor.execute(
            get_skill_spec(_IMPLEMENTATION_SKILL),
            payload,
            trace=trace,
        )
        implementation_plan = implementation_output.model_dump(mode="python")
    except Exception:
        degraded_skills.append(_IMPLEMENTATION_SKILL)

    try:
        test_output = await executor.execute(
            get_skill_spec(_TEST_PLAN_SKILL),
            payload,
            trace=trace,
        )
        test_plan = test_output.model_dump(mode="python")
    except Exception:
        degraded_skills.append(_TEST_PLAN_SKILL)

    span.set_attr("implementation_skill", _IMPLEMENTATION_SKILL)
    span.set_attr("test_plan_skill", _TEST_PLAN_SKILL)
    span.set_attr("degraded_skills", degraded_skills)
    trace[_AGENT] = span.end(
        status="ok",
        output_chars=len(json.dumps({"implementation_plan": implementation_plan, "test_plan": test_plan}, ensure_ascii=False)),
    )

    return {
        "implementation_plan": implementation_plan,
        "test_plan": test_plan,
        "trace": trace,
    }
