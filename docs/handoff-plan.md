# Handoff Plan

## v6 orchestration model

The v6 handoff flow keeps `delivery_bundle.json` as the approval source of truth, then adds an execution orchestration layer on top of approved bundles.

Each completed and approved review can now produce five layers of output:

- Standardized standalone review artifacts
- Structured machine-readable packs
- Agent-facing prompt views
- Persisted execution tasks in `execution_tasks.json`
- End-to-end traceability in `traceability_map.json`

## Bundle to execution flow

Recommended flow:

1. Run the requirement review workflow.
2. Review the standalone Markdown artifacts and `delivery_bundle.json`.
3. Move the bundle through approval until it reaches `approved`.
4. Call `handoff_to_executor` to route implementation and test work.
5. Track the routed work with `get_execution_status`.
6. Inspect upstream/downstream relationships with `get_traceability`.

`delivery_bundle.json` remains the decision gate. Execution only starts from an approved bundle.

## Execution modes

v6 supports three execution modes:

- `agent_auto`: lowest-friction execution, best for low-risk bounded work
- `agent_assisted`: default mode, allows manual checkpoints during execution
- `human_only`: no autonomous execution is assumed

When the execution pack contains high-risk items, routing automatically downgrades to `agent_assisted` unless the mode is already `human_only`.

## Execution task lifecycle

Execution tasks move through these states:

- `pending`
- `assigned`
- `in_progress`
- `waiting_review`
- `completed`
- `failed`
- `cancelled`

This gives the system a minimal but explicit orchestration model for downstream work without requiring a database or external scheduler.

## Traceability

The traceability layer links:

- requirement ids
- review item ids
- planned implementation tasks
- derived test items
- routed execution tasks

This makes it possible to answer both of these questions programmatically:

- which execution tasks implement one requirement?
- what upstream requirement and review context produced one execution task?

## Current boundaries

The v6 orchestration layer still does not:

- invoke real external coding agents through a live adapter
- stream asynchronous execution callbacks
- send notifications or reminders
- persist orchestration state in a database

Those remain future extensions beyond the current file-based orchestration model.
