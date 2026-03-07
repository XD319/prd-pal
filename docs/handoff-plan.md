# Handoff Plan

## v5 handoff model

The v5 handoff flow uses `delivery_bundle.json` as the canonical source of truth for delivery preparation.

Each completed review now produces three layers of output:

- Standardized standalone review artifacts:
  - `prd_review_report.md`
  - `open_questions.md`
  - `scope_boundary.md`
  - `tech_design_draft.md`
  - `test_checklist.md`
- Structured machine-readable packs:
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
- Agent-facing prompt views:
  - `codex_prompt.md`
  - `claude_code_prompt.md`

`delivery_bundle.json` references all of the above and carries approval status plus approval history.

## Why keep both bundle and standalone artifacts

The bundle solves a different problem from the individual files.

- The standalone Markdown artifacts are optimized for human review and handoff reading.
- The JSON packs are optimized for stable downstream programmatic consumption.
- The bundle unifies both into one approval-ready manifest.

This means:

- `delivery_bundle.json` is the source of truth for status and artifact references.
- Individual `.md` and `.json` files remain directly consumable by humans and downstream tools.

## Approval loop

The v5 approval loop is intentionally minimal.

States:

- `draft`: default state after generation
- `need_more_info`: reviewer requests clarification or missing details
- `blocked_by_risk`: reviewer stops handoff because material risk is unresolved
- `approved`: handoff package is ready for downstream execution

Valid transitions:

- `draft -> need_more_info`
- `draft -> approved`
- `draft -> blocked_by_risk`
- `need_more_info -> draft`
- `need_more_info -> blocked_by_risk`
- `blocked_by_risk -> draft`

`approved` is terminal in v5.

## Codex and Claude Code usage

Recommended usage is:

1. Run the requirement review workflow.
2. Review the standalone Markdown artifacts and the delivery bundle.
3. If needed, move the bundle through `need_more_info` or `blocked_by_risk`.
4. Once approved, open `codex_prompt.md` or `claude_code_prompt.md`.
5. Use the prompt in the downstream coding agent workspace.

The prompts still come from `execution_pack.json`, but the handoff decision should now be anchored on `delivery_bundle.json` status instead of only checking whether pack files exist.

## Current boundaries

The current handoff layer still stops at delivery preparation.

It does not yet:

- invoke external coding agents automatically
- create execution tasks or routing decisions
- store approval records in a database
- push notifications to reviewers or executors
- track downstream execution completion

Those are reserved for a later orchestration layer beyond v5.
