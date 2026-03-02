"""Schema for the **parser** agent output.

Field names match the JSON contract defined in ``prompts.PARSER_SYSTEM_PROMPT``
and consumed by ``agents/parser_agent.py``.
"""

from pydantic import BaseModel

from .base import SafeStrList


# ── item-level model ──────────────────────────────────────────────────────


class ParsedItem(BaseModel):
    """A single atomic requirement extracted from the PRD."""

    id: str
    description: str = ""
    acceptance_criteria: SafeStrList = []


# ── top-level output ──────────────────────────────────────────────────────


class ParserOutput(BaseModel):
    """Wrapper returned by the parser LLM call.

    ``{"parsed_items": [...]}``
    """

    parsed_items: list[ParsedItem] = []


def validate_parser_output(data: dict) -> ParserOutput:
    """Validate and coerce a raw dict into a :class:`ParserOutput`."""
    return ParserOutput.model_validate(data)


# ── minimal example ───────────────────────────────────────────────────────
# validate_parser_output({
#     "parsed_items": [
#         {
#             "id": "REQ-001",
#             "description": "User login via OAuth",
#             "acceptance_criteria": ["Redirects to provider", "Returns JWT"]
#         },
#         {
#             "id": "REQ-002",
#             "description": "Dashboard shows KPIs",
#             "acceptance_criteria": None  # safe_list → []
#         }
#     ]
# })
