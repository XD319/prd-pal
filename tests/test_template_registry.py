from __future__ import annotations

from requirement_review_v1.templates import (
    get_adapter_prompt_template,
    get_delivery_artifact_template,
    get_review_prompt_template,
    list_templates,
)


def test_registry_returns_versioned_review_templates() -> None:
    planner = get_review_prompt_template("review.planner")

    assert planner.template_id == "review.planner"
    assert planner.template_type == "review_prompt"
    assert planner.version == "v1.1"
    assert "delivery plan" in planner.description
    assert "{items_json}" in planner.user_prompt


def test_registry_returns_versioned_adapter_templates() -> None:
    codex = get_adapter_prompt_template("adapter.codex.handoff_markdown")

    assert codex.template_type == "adapter_prompt"
    assert codex.version == "handoff_markdown_v1"
    assert codex.agent_name == "Codex"
    assert codex.section_order


def test_registry_returns_delivery_artifact_templates_with_renderers() -> None:
    template = get_delivery_artifact_template("delivery_artifact.test_checklist")
    rendered = template.renderer(
        {
            "test_plan": {
                "test_scope": ["Login API"],
                "edge_cases": ["Expired token"],
                "regression_focus": ["Password login"],
            },
            "review_results": [{"id": "REQ-001", "issues": ["Clarify provider mapping"]}],
        }
    )

    assert template.template_type == "delivery_artifact_template"
    assert template.version == "v1"
    assert template.file_name == "test_checklist.md"
    assert rendered.startswith("# Test Checklist")
    assert "Clarify provider mapping" in rendered


def test_registry_lists_all_supported_template_types() -> None:
    template_types = {template.template_type for template in list_templates()}

    assert {"review_prompt", "adapter_prompt", "delivery_artifact_template"} <= template_types
