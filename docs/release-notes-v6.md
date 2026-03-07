# Release Notes v6

## Summary

v6 extends the system from delivery preparation into execution orchestration. Approved bundles can now be routed into persisted execution tasks with lifecycle tracking and end-to-end traceability.

## New capabilities

- `ExecutionTask`, `ExecutionEvent`, `ExecutionMode`, and `ExecutionTaskStatus` models
- `ExecutorRouter` for bundle-to-executor assignment
- Execution task lifecycle state machine with explicit transition validation
- `TraceabilityMap` covering `requirement -> review item -> plan task -> test item -> execution task`
- New MCP tools:
  - `handoff_to_executor`
  - `get_execution_status`
  - `get_traceability`
- Persisted execution artifacts:
  - `execution_tasks.json`
  - `traceability_map.json`

## Execution modes

- `agent_auto`: executor can proceed without manual checkpoints
- `agent_assisted`: executor can proceed, but explicit review checkpoints are allowed and expected at key steps
- `human_only`: the task is routed for manual execution only

Recommended usage:

- default to `agent_assisted` for normal engineering work
- use `agent_auto` only when risk is low and execution is well-bounded
- use `human_only` for high-sensitivity work or non-automatable environments

High-risk bundles are automatically downgraded to `agent_assisted` unless the caller explicitly routes to `human_only`.

## Task lifecycle

Valid transitions in v6:

- `pending -> assigned`
- `assigned -> in_progress`
- `in_progress -> waiting_review`
- `in_progress -> completed`
- `in_progress -> failed`
- `waiting_review -> in_progress`
- `waiting_review -> failed`
- `pending|assigned|in_progress|waiting_review -> cancelled`

This state machine makes execution progress queryable and auditable at the file level.

## Traceability model

Each approved bundle can now produce a persisted `traceability_map.json` that links:

- requirement ids from `parsed_items`
- review item ids from `review_results`
- plan task ids from `tasks`
- synthetic test-item ids derived from plan tasks
- execution task ids derived from routed packs

This allows MCP consumers to query traceability by bundle, requirement, or execution task.

## Difference from v5

v5 stopped at delivery preparation plus approval.

v6 adds a lightweight orchestration layer that can:

- take an approved `delivery_bundle.json`
- derive execution tasks for implementation and test work
- persist routing decisions and task state
- expose execution status and traceability via MCP

The system still does not execute external agents directly; it now manages the execution workflow around them.

## Known limitations

- No real executor adapter layer exists for Codex, Claude Code, or human ticketing systems
- No asynchronous callback or event-stream mechanism exists yet
- No notification mechanism exists for reviewers or executors
- Persistence remains file-system based rather than database-backed
