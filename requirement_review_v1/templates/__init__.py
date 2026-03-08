"""Template registry accessors."""

from .models import (
    BASE_SECTION_ORDER,
    AdapterPromptTemplate,
    DeliveryArtifactTemplate,
    ReviewPromptTemplate,
    TemplateDefinition,
)
from .registry import (
    get_adapter_prompt_template,
    get_delivery_artifact_template,
    get_review_prompt_template,
    get_template,
    list_templates,
)

__all__ = [
    "BASE_SECTION_ORDER",
    "AdapterPromptTemplate",
    "DeliveryArtifactTemplate",
    "ReviewPromptTemplate",
    "TemplateDefinition",
    "get_adapter_prompt_template",
    "get_delivery_artifact_template",
    "get_review_prompt_template",
    "get_template",
    "list_templates",
]
