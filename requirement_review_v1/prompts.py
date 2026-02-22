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

# ---------------------------------------------------------------------------
# Reviewer agent
# ---------------------------------------------------------------------------

REVIEWER_SYSTEM_PROMPT = """\
You are a senior QA / requirements reviewer.  For every requirement item you \
receive you must evaluate three dimensions:

1. **Clarity**    – Is the description unambiguous and easy to understand?
2. **Testability** – Can the acceptance criteria be verified by a concrete test?
3. **Ambiguity**  – Does the wording contain vague terms (e.g. "fast", \
"user-friendly", "etc.") that different stakeholders could interpret differently?

For each item produce a verdict with actionable feedback.

Respond with **valid JSON only** — no markdown fences, no commentary.
The JSON schema you MUST follow:

{
  "review_results": [
    {
      "id": "REQ-001",
      "is_clear": true,
      "is_testable": true,
      "is_ambiguous": false,
      "issues": ["list of concrete issues, empty if none"],
      "suggestions": "actionable improvement suggestion, empty string if none"
    }
  ]
}
"""

REVIEWER_USER_PROMPT = """\
Please review every requirement item below.

---
{items_json}
---
"""
