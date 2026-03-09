# Multi-Agent Requirement Review and Delivery Planning System

A LangGraph-based requirement review engine with an extension layer for delivery packaging, approval, handoff, and execution orchestration.

## System Position

This repository should be understood in two layers:

- Main architecture: a review-result-first engine that turns requirement sources into normalized review artifacts.
- Extension layer: optional packaging and orchestration capabilities that build on top of the review result.

The first-layer definition of the system is:

`source input -> review mode gating -> normalizer -> parallel reviewers -> aggregator -> review artifacts`

This is the primary architecture the repository should be evaluated against.

The repository still keeps additional modules for:

- delivery bundle generation
- approval loop
- coding-agent handoff packs
- execution orchestration
- traceability
- notifications

Those capabilities are retained in code and remain usable, but they are not the first-layer definition of the system.

## Versioning

This project uses three version concepts:

- Plan document version: e.g. `v2.1`
- Capability milestone: e.g. `v4`, `v5`, `v6`
- Package version: e.g. `0.6.0`

`0.6.0` maps to the current milestone baseline without implying a fully stabilized platform release.

## Core Capabilities

The main architecture focuses on review-only capabilities:

- Multi-source requirement intake through `prd_text`, `prd_path`, and connector-backed `source`
- Review mode gating to choose between `single_review` and `parallel_review`
- Requirement normalization into reviewer-specific views
- Multi-role review across product, engineering, QA, and security perspectives
- Aggregation of reviewer findings, risks, open questions, and conflicts
- Review artifact generation for both human-readable and machine-readable outputs
- CLI, FastAPI, and MCP entrypoints centered on producing review results

## Extension Layer

The repository also contains a retained extension layer built on top of review outputs:

- Delivery artifact splitting and `delivery_bundle.json`
- Approval state transitions and persisted review workspace snapshots
- Handoff pack generation:
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
  - `codex_prompt.md`
  - `claude_code_prompt.md`
- Execution routing and task lifecycle management
- Traceability maps across requirements, review items, and execution tasks
- Audit logging, retry metadata, template registry, and notification dispatch

These extension capabilities are not deprecated. They are preserved in the repository, but they should be discussed as second-layer or future-facing platform capabilities rather than the core system definition.

## Repository Layout

- `requirement_review_v1/`: review engine, retained extension modules, services, API, and MCP server
- `review_runtime/`: shared runtime config and model provider utilities
- `docs/`: architecture notes, MCP/API docs, and extension documents
- `eval/`: evaluation scripts
- `tests/`: automated tests
- `data/`: local knowledge and runtime data

## Installation

```bash
pip install -e .
```

## Usage

### CLI

Run one review from a local file:

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
```

The CLI still writes both core review artifacts and retained extension artifacts under `outputs/<run_id>/`.

### FastAPI

Start the API server:

```bash
python main.py
```

Core review endpoints:

- `POST /api/review`
- `GET /api/review/{run_id}`
- `GET /api/report/{run_id}?format=md|json`

Supporting extension or governance endpoints:

- `GET /api/templates`
- `GET /api/templates/{template_type}`
- `GET /api/audit`

### MCP

Run the MCP server in stdio mode:

```bash
python -m requirement_review_v1.mcp_server.server
```

Core review tools:

- `ping`
- `review_prd`
- `get_report`

Retained extension tools:

- `generate_delivery_bundle`
- `approve_handoff`
- `get_review_workspace`
- `handoff_to_executor`
- `update_execution_task`
- `list_execution_tasks`
- `get_execution_status`
- `get_traceability`
- `get_template_registry`
- `get_audit_events`
- `retry_operation`

## Outputs

Each run writes artifacts under `outputs/<run_id>/`.

Core artifacts always written by the review run:

- `report.md`
- `report.json`
- `run_trace.json`

Core review-detail artifacts written when the multi-reviewer path is used:

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

Retained extension artifacts currently preserved in the repository:

- `prd_review_report.md`
- `open_questions.md`
- `scope_boundary.md`
- `tech_design_draft.md`
- `test_checklist.md`
- `delivery_bundle.json`
- `approval_records.json`
- `status_snapshot.json`
- `implementation_pack.json`
- `test_pack.json`
- `execution_pack.json`
- `codex_prompt.md`
- `claude_code_prompt.md`
- `execution_tasks.json`
- `traceability_map.json`
- `audit_log.jsonl`
- `notifications.jsonl`

The current implementation may generate extension artifacts during the same run, but the architectural center of gravity is the review result and its review artifacts.

## Main Flow

The main flow is intentionally defined as:

1. Source input
2. Review mode gating
3. Normalizer
4. Parallel reviewers
5. Aggregator
6. Review artifacts

In current code, surrounding workflow nodes such as parser, planner, risk analysis, delivery planning, and reporting still exist. They support or enrich the review flow, but the top-level system definition should remain anchored on review result production.

## Boundaries

The main architecture does not require:

- approval before a review result exists
- execution orchestration to complete a review run
- traceability or notifications to define review success
- direct control of an external coding agent

The extension layer may add those capabilities, but they are not required to understand or adopt the core review engine.

## Related Docs

- `docs/review-engine-positioning.md`: main-architecture positioning
- `docs/handoff-plan.md`: retained extension-layer handoff and orchestration notes
- `docs/mcp.md`: MCP usage, with core review tools first and extension tools separated
- `docs/v2-api.md`: FastAPI usage, centered on review endpoints

## Validation

```bash
python eval/run_eval.py
pytest -q
```
