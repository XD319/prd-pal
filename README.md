# Multi-Agent Requirement Review and Delivery Planning System

A LangGraph-based system for requirement review, delivery planning, standardized delivery artifacts, coding-agent handoff preparation, and lightweight execution orchestration.

## System position

This repository currently implements the milestone-v6 capability baseline for turning a PRD into:

- a structured requirement review report
- standardized delivery artifacts and a canonical `delivery_bundle.json`
- implementation, test, and execution packs for downstream coding agents
- a human approval loop before handoff execution
- persisted execution tasks and traceability for approved bundles

The current scope is orchestration and tracking around execution, not direct external agent control.

## Versioning

This project now uses three separate version concepts:

- Plan document version: e.g. `v2.1`, used for architecture and roadmap documents
- Capability milestone: e.g. `v4`, `v5`, `v6`, used to describe major feature stages
- Package version: `0.6.0`, used for the installable Python package

Why `0.6.0` instead of `6.0.0`:

- the repository is still evolving and several planned platform capabilities are not implemented yet
- current `v6` means "milestone 6 capability baseline", not "sixth major stable release"
- `0.6.0` keeps the milestone mapping while making the package semantics more honest

## Core capabilities

- LangGraph-based requirement review workflow with parser, planner, risk, reviewer, and reporter stages
- Delivery planning outputs embedded in the review flow
- Standardized standalone artifacts:
  - `prd_review_report.md`
  - `open_questions.md`
  - `scope_boundary.md`
  - `tech_design_draft.md`
  - `test_checklist.md`
- Canonical delivery bundle:
  - `delivery_bundle.json`
- Structured handoff packs:
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
- Markdown prompts derived from the execution pack:
  - `codex_prompt.md`
  - `claude_code_prompt.md`
- Approval state machine with `draft`, `need_more_info`, `approved`, and `blocked_by_risk`
- Execution orchestration primitives:
  - `ExecutionTask`
  - `ExecutorRouter`
  - task lifecycle transitions
  - `TraceabilityMap`
- MCP tools for review, bundle approval, execution routing, execution status, and traceability queries
- Trace output for pack building, bundle generation, handoff rendering, and persisted orchestration artifacts

## Explicit boundaries

This system currently does not:

- directly modify the target repository
- directly execute commands inside the target repository
- invoke real external executors through provider-specific adapters
- persist approvals or traceability in a database
- provide notifications, scheduling, or asynchronous callback handling

## Repository layout

- `requirement_review_v1/`: review workflow, delivery planning, orchestration logic, MCP server, schemas, and services
- `review_runtime/`: shared runtime utilities for config loading and model provider access
- `eval/`: regression evaluation cases and runner
- `data/risk_catalog.json`: local risk knowledge base
- `docs/`: project notes, release notes, API docs, and sample PRD
- `tests/`: automated test suite

## Installation

```bash
pip install -e .
```

## Usage

### CLI

Run one review from a local PRD file:

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
```

### FastAPI

Start the API server:

```bash
python main.py
```

Primary endpoints:

- `POST /api/review`
- `GET /api/review/{run_id}`
- `GET /api/report/{run_id}?format=md|json`

### MCP

Run the MCP server in stdio mode:

```bash
python -m requirement_review_v1.mcp_server.server
```

Current MCP tools:

- `ping`
- `review_prd`
- `get_report`
- `generate_delivery_bundle`
- `approve_handoff`
- `handoff_to_executor`
- `get_execution_status`
- `get_traceability`

## Outputs

Each run writes artifacts under `outputs/<run_id>/`:

- `report.md`
- `report.json`
- `run_trace.json`
- `prd_review_report.md`
- `open_questions.md`
- `scope_boundary.md`
- `tech_design_draft.md`
- `test_checklist.md`
- `implementation_pack.json`
- `test_pack.json`
- `execution_pack.json`
- `codex_prompt.md`
- `claude_code_prompt.md`
- `delivery_bundle.json`
- `execution_tasks.json`
- `traceability_map.json`

## Approval and execution flow

`delivery_bundle.json` is the source of truth for approval status.

Approval transitions:

- `draft -> need_more_info`
- `draft -> approved`
- `draft -> blocked_by_risk`
- `need_more_info -> draft`
- `need_more_info -> blocked_by_risk`
- `blocked_by_risk -> draft`

Execution task transitions:

- `pending -> assigned`
- `assigned -> in_progress`
- `in_progress -> waiting_review`
- `in_progress -> completed|failed|cancelled`
- `waiting_review -> in_progress|failed|cancelled`

`approved` is terminal for the bundle itself, but it is now the entry point for execution orchestration.

## Validation

Run evaluation and tests:

```bash
python eval/run_eval.py
pytest -q
```
