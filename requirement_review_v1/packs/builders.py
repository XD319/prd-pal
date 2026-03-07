"""Helpers for constructing structured task packs."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel

from requirement_review_v1.schemas.planning_skill_schema import (
    CodingAgentPromptOutput,
    ImplementationPlanOutput,
    QaPlanningOutput,
)

from .schemas import (
    AgentHandoff,
    ExecutionPack,
    ImplementationPack,
    RiskSummaryItem,
    TestPack,
)


JsonDict = dict[str, Any]


def _as_dict(data: Any) -> JsonDict:
    if data is None:
        return {}
    if isinstance(data, BaseModel):
        return data.model_dump(mode="python")
    if isinstance(data, dict):
        return dict(data)
    raise TypeError(f"Unsupported input type: {type(data)!r}")


def _as_dict_list(items: Any) -> list[JsonDict]:
    if items is None:
        return []
    if isinstance(items, list):
        return [_as_dict(item) for item in items]
    raise TypeError(f"Expected list input, got: {type(items)!r}")


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value:
            return value
    return ""


def _collect_acceptance_criteria(requirements: list[JsonDict]) -> list[str]:
    criteria: list[str] = []
    for requirement in requirements:
        for item in requirement.get("acceptance_criteria", []) or []:
            text = str(item).strip()
            if text and text not in criteria:
                criteria.append(text)
    return criteria


def _json_block(title: str, payload: Any) -> str:
    return f"{title}:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


class _BasePackBuilder:
    pack_type: str

    def _normalize_inputs(
        self,
        *,
        requirements: list[dict[str, Any]] | list[BaseModel] | None,
        tasks: list[dict[str, Any]] | list[BaseModel] | None,
        risks: list[dict[str, Any]] | list[BaseModel] | None,
        implementation_plan_output: ImplementationPlanOutput | JsonDict | None,
        test_plan_output: QaPlanningOutput | JsonDict | None,
        codex_prompt_output: CodingAgentPromptOutput | JsonDict | None,
        claude_code_prompt_output: CodingAgentPromptOutput | JsonDict | None,
    ) -> JsonDict:
        requirements_list = _as_dict_list(requirements)
        tasks_list = _as_dict_list(tasks)
        risks_list = _as_dict_list(risks)
        implementation_plan = _as_dict(implementation_plan_output)
        test_plan = _as_dict(test_plan_output)
        codex_prompt = _as_dict(codex_prompt_output)
        claude_code_prompt = _as_dict(claude_code_prompt_output)
        primary_task = tasks_list[0] if tasks_list else {}
        primary_requirement = requirements_list[0] if requirements_list else {}

        return {
            "requirements": requirements_list,
            "tasks": tasks_list,
            "risks": risks_list,
            "implementation_plan": implementation_plan,
            "test_plan": test_plan,
            "codex_prompt": codex_prompt,
            "claude_code_prompt": claude_code_prompt,
            "primary_task": primary_task,
            "primary_requirement": primary_requirement,
            "task_id": _first_non_empty(
                str(primary_task.get("id", "")).strip(),
                str(primary_requirement.get("id", "")).strip(),
                "handoff-task",
            ),
            "title": _first_non_empty(
                str(primary_task.get("title", "")).strip(),
                str(primary_requirement.get("description", "")).strip(),
                f"{self.pack_type.replace('_', ' ').title()}",
            ),
            "summary": _first_non_empty(
                str(primary_requirement.get("description", "")).strip(),
                str(primary_task.get("title", "")).strip(),
                "Multi-skill handoff pack",
            ),
            "acceptance_criteria": _collect_acceptance_criteria(requirements_list),
        }


class ImplementationPackBuilder(_BasePackBuilder):
    """Assemble an implementation-focused handoff pack from multiple skill outputs."""

    pack_type = "implementation_pack"

    def build(
        self,
        *,
        requirements: list[dict[str, Any]] | list[BaseModel] | None,
        tasks: list[dict[str, Any]] | list[BaseModel] | None,
        risks: list[dict[str, Any]] | list[BaseModel] | None,
        implementation_plan_output: ImplementationPlanOutput | JsonDict | None,
        test_plan_output: QaPlanningOutput | JsonDict | None,
        codex_prompt_output: CodingAgentPromptOutput | JsonDict | None,
        claude_code_prompt_output: CodingAgentPromptOutput | JsonDict | None,
    ) -> ImplementationPack:
        data = self._normalize_inputs(
            requirements=requirements,
            tasks=tasks,
            risks=risks,
            implementation_plan_output=implementation_plan_output,
            test_plan_output=test_plan_output,
            codex_prompt_output=codex_prompt_output,
            claude_code_prompt_output=claude_code_prompt_output,
        )
        context_sections = [
            _json_block("Requirements", data["requirements"]),
            _json_block("Tasks", data["tasks"]),
            _json_block("Risks", data["risks"]),
        ]
        handoff_notes = [
            data["codex_prompt"].get("agent_prompt", ""),
            data["claude_code_prompt"].get("agent_prompt", ""),
        ]
        handoff_notes.extend(data["codex_prompt"].get("non_goals", []) or [])
        handoff_notes.extend(data["claude_code_prompt"].get("non_goals", []) or [])

        return ImplementationPack.model_validate(
            {
                "pack_type": self.pack_type,
                "task_id": data["task_id"],
                "title": data["title"],
                "summary": data["summary"],
                "context": "\n\n".join(section for section in context_sections if section),
                "target_modules": data["implementation_plan"].get("target_modules", []) or [],
                "implementation_steps": data["implementation_plan"].get("implementation_steps", []) or [],
                "constraints": data["implementation_plan"].get("constraints", []) or [],
                "acceptance_criteria": data["acceptance_criteria"],
                "recommended_skills": ["implementation.plan", "codex.prompt.generate", "claude_code.prompt.generate"],
                "agent_handoff": AgentHandoff.model_validate(
                    {
                        "primary_agent": "codex",
                        "supporting_agents": ["claude_code"],
                        "goals": data["codex_prompt"].get("recommended_execution_order", []) or [],
                        "expected_output": data["codex_prompt"].get("agent_prompt", ""),
                        "notes": [note for note in handoff_notes if note],
                    }
                ),
            }
        )


class TestPackBuilder(_BasePackBuilder):
    """Assemble a test-focused handoff pack from planning and prompt outputs."""

    pack_type = "test_pack"

    def build(
        self,
        *,
        requirements: list[dict[str, Any]] | list[BaseModel] | None,
        tasks: list[dict[str, Any]] | list[BaseModel] | None,
        risks: list[dict[str, Any]] | list[BaseModel] | None,
        implementation_plan_output: ImplementationPlanOutput | JsonDict | None,
        test_plan_output: QaPlanningOutput | JsonDict | None,
        codex_prompt_output: CodingAgentPromptOutput | JsonDict | None,
        claude_code_prompt_output: CodingAgentPromptOutput | JsonDict | None,
    ) -> TestPack:
        data = self._normalize_inputs(
            requirements=requirements,
            tasks=tasks,
            risks=risks,
            implementation_plan_output=implementation_plan_output,
            test_plan_output=test_plan_output,
            codex_prompt_output=codex_prompt_output,
            claude_code_prompt_output=claude_code_prompt_output,
        )
        acceptance_criteria = list(data["acceptance_criteria"])
        for item in data["codex_prompt"].get("validation_checklist", []) or []:
            if item not in acceptance_criteria:
                acceptance_criteria.append(item)
        for item in data["claude_code_prompt"].get("validation_checklist", []) or []:
            if item not in acceptance_criteria:
                acceptance_criteria.append(item)

        return TestPack.model_validate(
            {
                "pack_type": self.pack_type,
                "task_id": data["task_id"],
                "title": data["title"],
                "summary": data["summary"],
                "test_scope": data["test_plan"].get("test_scope", []) or [],
                "edge_cases": (data["test_plan"].get("edge_cases", []) or [])
                + (data["test_plan"].get("regression_focus", []) or []),
                "acceptance_criteria": acceptance_criteria,
                "agent_handoff": AgentHandoff.model_validate(
                    {
                        "primary_agent": "claude_code",
                        "supporting_agents": ["codex"],
                        "goals": data["claude_code_prompt"].get("recommended_execution_order", []) or [],
                        "expected_output": data["claude_code_prompt"].get("agent_prompt", ""),
                        "notes": [
                            note
                            for note in [
                                data["codex_prompt"].get("agent_prompt", ""),
                                data["claude_code_prompt"].get("agent_prompt", ""),
                            ]
                            if note
                        ],
                    }
                ),
            }
        )


class ExecutionPackBuilder(_BasePackBuilder):
    """Combine implementation, test and risk handoff details into one execution pack."""

    pack_type = "execution_pack"

    def __init__(
        self,
        implementation_builder: ImplementationPackBuilder | None = None,
        test_builder: TestPackBuilder | None = None,
    ) -> None:
        self.implementation_builder = implementation_builder or ImplementationPackBuilder()
        self.test_builder = test_builder or TestPackBuilder()

    def build(
        self,
        *,
        requirements: list[dict[str, Any]] | list[BaseModel] | None,
        tasks: list[dict[str, Any]] | list[BaseModel] | None,
        risks: list[dict[str, Any]] | list[BaseModel] | None,
        implementation_plan_output: ImplementationPlanOutput | JsonDict | None,
        test_plan_output: QaPlanningOutput | JsonDict | None,
        codex_prompt_output: CodingAgentPromptOutput | JsonDict | None,
        claude_code_prompt_output: CodingAgentPromptOutput | JsonDict | None,
        handoff_strategy: str = "sequential",
    ) -> ExecutionPack:
        data = self._normalize_inputs(
            requirements=requirements,
            tasks=tasks,
            risks=risks,
            implementation_plan_output=implementation_plan_output,
            test_plan_output=test_plan_output,
            codex_prompt_output=codex_prompt_output,
            claude_code_prompt_output=claude_code_prompt_output,
        )
        implementation_pack = self.implementation_builder.build(
            requirements=data["requirements"],
            tasks=data["tasks"],
            risks=data["risks"],
            implementation_plan_output=data["implementation_plan"],
            test_plan_output=data["test_plan"],
            codex_prompt_output=data["codex_prompt"],
            claude_code_prompt_output=data["claude_code_prompt"],
        )
        test_pack = self.test_builder.build(
            requirements=data["requirements"],
            tasks=data["tasks"],
            risks=data["risks"],
            implementation_plan_output=data["implementation_plan"],
            test_plan_output=data["test_plan"],
            codex_prompt_output=data["codex_prompt"],
            claude_code_prompt_output=data["claude_code_prompt"],
        )
        risk_pack = [
            RiskSummaryItem.model_validate(
                {
                    "id": risk.get("id", f"risk-{index + 1}"),
                    "summary": risk.get("summary", "") or risk.get("description", ""),
                    "level": risk.get("level", "") or risk.get("impact", "medium"),
                    "mitigation": risk.get("mitigation", ""),
                    "owner": risk.get("owner", ""),
                }
            )
            for index, risk in enumerate(data["risks"])
        ]

        return ExecutionPack.model_validate(
            {
                "pack_type": self.pack_type,
                "pack_version": "1.0",
                "implementation_pack": implementation_pack,
                "test_pack": test_pack,
                "risk_pack": risk_pack,
                "handoff_strategy": handoff_strategy,
            }
        )


def build_implementation_pack(**data: object) -> ImplementationPack:
    """Validate and create an implementation pack."""

    return ImplementationPack.model_validate(data)


def build_test_pack(**data: object) -> TestPack:
    """Validate and create a test pack."""

    return TestPack.model_validate(data)


def build_execution_pack(
    implementation_pack: ImplementationPack | dict[str, object],
    test_pack: TestPack | dict[str, object],
    risk_pack: list[RiskSummaryItem | dict[str, object]] | None = None,
    handoff_strategy: str = "sequential",
    pack_type: str = "execution_pack",
    pack_version: str = "1.0",
) -> ExecutionPack:
    """Validate and create a full execution pack."""

    risk_items = risk_pack or []
    return ExecutionPack.model_validate(
        {
            "pack_type": pack_type,
            "pack_version": pack_version,
            "implementation_pack": implementation_pack,
            "test_pack": test_pack,
            "risk_pack": risk_items,
            "handoff_strategy": handoff_strategy,
        }
    )
