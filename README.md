# Multi-Agent Requirement Review and Delivery Planning System

A LangGraph-based system for requirement review, delivery planning, standardized delivery artifacts, and coding-agent handoff preparation.

## System position

This repository is the v5 baseline for turning a PRD into:

- a structured requirement review report
- standardized delivery artifacts and a canonical `delivery_bundle.json`
- implementation, test, and execution packs for downstream coding agents
- a minimal human approval loop before handoff execution

The current scope is delivery preparation plus approval readiness, not autonomous execution orchestration.

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
- Minimal approval state machine with `draft`, `need_more_info`, `approved`, and `blocked_by_risk`
- Shared service layer across CLI, FastAPI, and MCP entrypoints
- Trace output for pack building, bundle generation, and handoff rendering

## Explicit boundaries

This system currently does not:

- directly modify the target repository
- directly execute commands inside the target repository
- route work to external executors automatically
- persist approvals or traceability in a database
- provide notifications, scheduling, or execution-task orchestration

## Repository layout

- `requirement_review_v1/`: review workflow, delivery planning, bundle generation, approval logic, API, MCP server, schemas, and services
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

## Runtime configuration

The workflow reads model settings from environment variables through `review_runtime.config.Config`.

Common variables:

```bash
OPENAI_API_KEY=...
SMART_LLM=openai:gpt-4.1
FAST_LLM=openai:gpt-4o-mini
LLM_KWARGS={}
```

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

## Approval flow

`delivery_bundle.json` is the source of truth for approval status.

Valid transitions:

- `draft -> need_more_info`
- `draft -> approved`
- `draft -> blocked_by_risk`
- `need_more_info -> draft`
- `need_more_info -> blocked_by_risk`
- `blocked_by_risk -> draft`

`approved` is terminal in v5.

## Validation

Run evaluation and tests:

```bash
python eval/run_eval.py
pytest -q
```
