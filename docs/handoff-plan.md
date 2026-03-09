# Handoff And Orchestration Extension

## Positioning

This document describes the repository's extension layer.

It is not the definition of the main review architecture.

The primary system flow remains:

`source input -> review mode gating -> normalizer -> parallel reviewers -> aggregator -> review artifacts`

The capabilities below are downstream extensions that build on a completed review result.

## Extension Scope

The repository retains code for:

- `delivery_bundle.json` generation
- approval actions and persisted workspace state
- handoff pack generation for downstream coding agents
- execution task routing and lifecycle tracking
- traceability across requirements, review items, and tasks
- governance support such as notifications and audit data

These modules are still present and usable. They are not removed or deprecated by this document.

## Extension Entry Conditions

The extension layer starts only after a review run has produced its core artifacts.

Recommended extension flow:

1. Run the review engine and inspect the review artifacts.
2. Optionally generate or regenerate `delivery_bundle.json`.
3. Optionally move the bundle through approval actions.
4. Optionally create handoff packs and execution tasks.
5. Optionally query traceability, workspace state, audit events, and execution status.

## Retained Bundle And Approval Model

The current repository keeps `delivery_bundle.json` as the persisted package for downstream extension workflows.

Approval transitions remain:

- `draft -> need_more_info`
- `draft -> approved`
- `draft -> blocked_by_risk`
- `need_more_info -> draft`
- `need_more_info -> blocked_by_risk`
- `blocked_by_risk -> draft`

Related persisted extension files include:

- `delivery_bundle.json`
- `approval_records.json`
- `status_snapshot.json`

## Retained Handoff And Execution Model

The current extension layer also retains:

- `implementation_pack.json`
- `test_pack.json`
- `execution_pack.json`
- `codex_prompt.md`
- `claude_code_prompt.md`
- `execution_tasks.json`
- `traceability_map.json`

Execution task transitions remain:

- `pending -> assigned`
- `assigned -> in_progress`
- `in_progress -> waiting_review`
- `in_progress -> completed|failed|cancelled`
- `waiting_review -> in_progress|failed|cancelled`

Execution modes still available in code:

- `agent_auto`
- `agent_assisted`
- `human_only`

## Extension Boundaries

The retained extension layer still does not:

- invoke real external coding agents through live provider adapters
- provide a full async callback platform or scheduler
- persist workflow state in a database by default
- make notifications mandatory for review completion

## Relationship To The Main Architecture

This document should be read as:

- an extension note for users who want review-plus-orchestration
- not a replacement for the review-engine positioning
- not the first document to use when defining the system at a high level
