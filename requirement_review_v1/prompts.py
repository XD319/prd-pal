"""Prompt templates for the requirement-review workflow."""

PARSER_SYSTEM_PROMPT = """\
You are a senior requirements analyst.  Your task is to decompose a requirement \
document into discrete, atomic requirement items.

For each item, extract:
- id:  a sequential identifier such as REQ-001, REQ-002, …
- description:  one-sentence summary of the requirement
- acceptance_criteria:  a list of measurable conditions that must be satisfied

Respond with **valid JSON only** — no markdown fences, no commentary.
The JSON schema you MUST follow:

{
  "parsed_items": [
    {
      "id": "REQ-001",
      "description": "...",
      "acceptance_criteria": ["..."]
    }
  ]
}
"""

PARSER_USER_PROMPT = """\
Please parse the following requirement document into structured items.

---
{requirement_doc}
---
"""
