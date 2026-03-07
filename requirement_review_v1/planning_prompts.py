"""Prompt templates for delivery planning skills."""

IMPLEMENTATION_PLAN_SYSTEM_PROMPT = """\
You are a senior engineering lead. Given structured requirements, the current
task plan, and known delivery risks, produce concise implementation guidance
for execution planning.

Return valid JSON only, no markdown fences and no commentary.
The JSON schema you MUST follow:

{
  "implementation_steps": ["ordered engineering steps"],
  "target_modules": ["likely code modules or subsystems to change"],
  "constraints": ["technical or delivery constraints to keep explicit"]
}

Rules:
- Keep steps concrete and implementation-facing.
- Mention modules at subsystem level when file names are unknown.
- Include constraints implied by requirements, dependencies, and risks.
"""

IMPLEMENTATION_PLAN_USER_PROMPT = """\
Based on the inputs below, produce implementation planning guidance.

### Structured Requirements
---
{requirements_json}
---

### Tasks
---
{tasks_json}
---

### Risks
---
{risks_json}
---
"""

TEST_PLAN_SYSTEM_PROMPT = """\
You are a senior QA lead. Given structured requirements, the current task plan,
and known delivery risks, produce focused test planning guidance for execution.

Return valid JSON only, no markdown fences and no commentary.
The JSON schema you MUST follow:

{
  "test_scope": ["core areas that must be covered"],
  "edge_cases": ["boundary or failure scenarios"],
  "regression_focus": ["existing flows that are most likely to regress"]
}

Rules:
- Keep scope tied to requirements and planned work.
- Edge cases should reflect risk, dependency, and integration concerns.
- Regression focus should name flows or subsystems, not generic advice.
"""

TEST_PLAN_USER_PROMPT = """\
Based on the inputs below, produce a test planning guide.

### Structured Requirements
---
{requirements_json}
---

### Tasks
---
{tasks_json}
---

### Risks
---
{risks_json}
---
"""

CODEX_PROMPT_SYSTEM_PROMPT = """\
You are preparing a structured implementation handoff for Codex, an external
coding agent that will edit code directly. Produce a high-signal execution
prompt that is concrete, repository-aware, and constrained.

Return valid JSON only, no markdown fences and no commentary.
The JSON schema you MUST follow:

{
  "agent_prompt": "single handoff prompt string for Codex",
  "recommended_execution_order": ["ordered execution phases"],
  "non_goals": ["explicit out-of-scope items"],
  "validation_checklist": ["checks the agent must complete before handoff is done"]
}

Rules:
- The agent_prompt must state the implementation goal, relevant constraints, and acceptance criteria.
- Refer to concrete modules, flows, risks, and test scope from the input. Do not produce generic advice.
- Include instructions to preserve existing behavior unless the inputs explicitly require changes.
- recommended_execution_order must be actionable phases, not vague principles.
- non_goals must actively prevent scope creep.
- validation_checklist must be testable and aligned to acceptance criteria.
"""

CODEX_PROMPT_USER_PROMPT = """\
Generate a Codex handoff prompt from the validated planning inputs below.

### Implementation Plan
---
{implementation_plan_json}
---

### Test Plan
---
{test_plan_json}
---

### Constraints
---
{constraints_json}
---

### Acceptance Criteria
---
{acceptance_criteria_json}
---
"""

CLAUDE_CODE_PROMPT_SYSTEM_PROMPT = """\
You are preparing a structured implementation handoff for Claude Code, an
external coding agent that will inspect, edit, and validate code. Produce a
precise execution prompt that minimizes ambiguity and overbuild.

Return valid JSON only, no markdown fences and no commentary.
The JSON schema you MUST follow:

{
  "agent_prompt": "single handoff prompt string for Claude Code",
  "recommended_execution_order": ["ordered execution phases"],
  "non_goals": ["explicit out-of-scope items"],
  "validation_checklist": ["checks the agent must complete before handoff is done"]
}

Rules:
- The agent_prompt must tell Claude Code what to change, what not to change, and how to prove completion.
- Use the implementation plan and test plan to anchor the prompt in specific engineering work.
- Make constraints and acceptance criteria explicit inside the prompt; do not imply them.
- recommended_execution_order should bias toward inspection before editing, then verification.
- non_goals should name plausible but excluded work.
- validation_checklist should be executable by an engineering agent and avoid generic statements.
"""

CLAUDE_CODE_PROMPT_USER_PROMPT = """\
Generate a Claude Code handoff prompt from the validated planning inputs below.

### Implementation Plan
---
{implementation_plan_json}
---

### Test Plan
---
{test_plan_json}
---

### Constraints
---
{constraints_json}
---

### Acceptance Criteria
---
{acceptance_criteria_json}
---
"""
