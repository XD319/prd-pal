"""Schemas for delivery planning skills."""

from typing import Any

from pydantic import ConfigDict, Field

from .base import AgentSchemaModel


class DeliveryPlanningSkillInput(AgentSchemaModel):
    model_config = ConfigDict(extra="forbid")

    structured_requirements: list[dict[str, Any]] = Field(default_factory=list)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[dict[str, Any]] = Field(default_factory=list)


class ImplementationPlanOutput(AgentSchemaModel):
    implementation_steps: list[str] = Field(default_factory=list)
    target_modules: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class QaPlanningOutput(AgentSchemaModel):
    test_scope: list[str] = Field(default_factory=list)
    edge_cases: list[str] = Field(default_factory=list)
    regression_focus: list[str] = Field(default_factory=list)


def validate_implementation_plan_output(data: dict[str, Any]) -> ImplementationPlanOutput:
    return ImplementationPlanOutput.model_validate(data)


def validate_test_plan_generate_output(data: dict[str, Any]) -> QaPlanningOutput:
    return QaPlanningOutput.model_validate(data)

