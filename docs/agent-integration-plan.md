# Agent Integration Plan

This document defines the recommended integration contract for coding agents such as Codex, Claude Code, and OpenClaw.

## Recommended Access Model

Use two layers:

- `CLI` as the lowest-friction integration surface for local scripts, CI jobs, and thin wrappers
- `MCP` as the primary native tool interface for agent applications

This keeps the project easy to automate while still feeling native inside agent clients.

## Core Workflows

### 1. Review-Only Workflow

Use this when an agent has just produced a PRD draft and needs review feedback.

Flow:

1. Agent submits `prd_text`, `prd_path`, or `source`
2. Project runs the review engine
3. Project returns structured review outputs:
   - `findings`
   - `open_questions`
   - `risk_items`
   - `conflicts`
   - `review_mode`
   - `report_path`

Recommended entrypoints:

- CLI: `prd-review review --input docs/sample_prd.md --json`
- MCP: `review_requirement`

### 2. Agent Handoff Workflow

Use this when a completed review run should be turned into agent-specific execution requests.

Flow:

1. Agent references an existing `run_id`, or supplies PRD input directly
2. Project ensures review artifacts and delivery bundle exist
3. Project prepares adapter-specific request payloads
4. Agent receives:
   - request file path
   - execution context path
   - request payload
   - prompt path when available

Recommended entrypoints:

- CLI: `prd-review prepare-handoff --run-id <run_id> --agent all --json`
- MCP: `prepare_agent_handoff`

## Agent Mapping

- `codex`
  - default source pack: `implementation_pack`
  - role: implementation-focused code changes
- `claude_code`
  - default source pack: `test_pack`
  - role: validation and regression-oriented work
- `openclaw`
  - default source pack: `implementation_pack`
  - role: implementation with explicit verification scope

## Design Principles

- Review-first remains the main architecture
- Handoff preparation should not require immediate task routing approval
- Request payloads should be stable JSON, not prompt-only text blobs
- Agent-specific prompts should be rendered from the same execution pack
- MCP and CLI should share the same underlying service logic

## Output Contract For Prepared Handoffs

Prepared handoff payloads should include:

- `run_id`
- `bundle_id`
- `status`
- `agent_selection`
- `requests[]`

Each request item should include:

- `agent`
- `task_id`
- `source_pack_type`
- `request_type`
- `request_path`
- `context_path`
- `prompt_path`
- `request`

## Why This Matches Real Workflow

This design matches a practical team workflow:

1. Draft PRD in an agent tool
2. Call the review engine immediately
3. Iterate on findings and missing details
4. When ready, prepare execution requests for downstream coding agents

That keeps the review engine focused on structured validation while making agent handoff a clean follow-on step instead of a separate product.
