"""LLM-backed delivery planning skills."""

from __future__ import annotations

import json
from typing import Any

from ..planning_prompts import (
    IMPLEMENTATION_PLAN_SYSTEM_PROMPT,
    IMPLEMENTATION_PLAN_USER_PROMPT,
    TEST_PLAN_SYSTEM_PROMPT,
    TEST_PLAN_USER_PROMPT,
)
from ..schemas.planning_skill_schema import (
    DeliveryPlanningSkillInput,
    ImplementationPlanOutput,
    QaPlanningOutput,
    validate_implementation_plan_output,
    validate_test_plan_generate_output,
)
from ..utils.llm_structured_call import llm_structured_call
from .executor import SkillSpec


def _planning_payload_json(payload: DeliveryPlanningSkillInput) -> tuple[str, str, str]:
    requirements_json = json.dumps(payload.structured_requirements, ensure_ascii=False, indent=2)
    tasks_json = json.dumps(payload.tasks, ensure_ascii=False, indent=2)
    risks_json = json.dumps(payload.risks, ensure_ascii=False, indent=2)
    return requirements_json, tasks_json, risks_json


async def _implementation_plan(payload: DeliveryPlanningSkillInput) -> dict[str, Any]:
    requirements_json, tasks_json, risks_json = _planning_payload_json(payload)
    prompt = (
        f"{IMPLEMENTATION_PLAN_SYSTEM_PROMPT}\n\n"
        f"{IMPLEMENTATION_PLAN_USER_PROMPT.format(requirements_json=requirements_json, tasks_json=tasks_json, risks_json=risks_json)}"
    )
    parsed = await llm_structured_call(
        prompt=prompt,
        schema=ImplementationPlanOutput,
        metadata={"agent_name": "implementation.plan", "run_id": ""},
    )
    return validate_implementation_plan_output(parsed).model_dump(mode="python")


async def _generate_test_plan(payload: DeliveryPlanningSkillInput) -> dict[str, Any]:
    requirements_json, tasks_json, risks_json = _planning_payload_json(payload)
    prompt = (
        f"{TEST_PLAN_SYSTEM_PROMPT}\n\n"
        f"{TEST_PLAN_USER_PROMPT.format(requirements_json=requirements_json, tasks_json=tasks_json, risks_json=risks_json)}"
    )
    parsed = await llm_structured_call(
        prompt=prompt,
        schema=QaPlanningOutput,
        metadata={"agent_name": "test.plan.generate", "run_id": ""},
    )
    return validate_test_plan_generate_output(parsed).model_dump(mode="python")


IMPLEMENTATION_PLAN_SKILL = SkillSpec(
    name="implementation.plan",
    input_model=DeliveryPlanningSkillInput,
    output_model=ImplementationPlanOutput,
    handler=_implementation_plan,
    config_version="implementation.plan@v1",
    cache_ttl_sec=300,
)


TEST_PLAN_GENERATE_SKILL = SkillSpec(
    name="test.plan.generate",
    input_model=DeliveryPlanningSkillInput,
    output_model=QaPlanningOutput,
    handler=_generate_test_plan,
    config_version="test.plan.generate@v1",
    cache_ttl_sec=300,
)


