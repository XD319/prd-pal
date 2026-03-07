# Multi-Agent Requirement Review and Delivery Planning System

A LangGraph-based system for requirement review, delivery planning, and coding-agent handoff artifact generation.

## System position

This repository is the v4 mainline baseline for turning a PRD into:

- a structured requirement review report
- delivery planning outputs for implementation and testing
- coding-agent handoff artifacts for Codex and Claude Code

The current scope is delivery preparation, not autonomous execution.

## Core capabilities

- LangGraph-based requirement review workflow with parser, planner, risk, reviewer, and reporter stages
- Delivery planning outputs embedded in the review flow
- Structured handoff artifacts:
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
- Markdown prompts derived from the execution pack:
  - `codex_prompt.md`
  - `claude_code_prompt.md`
- Shared service layer across CLI, FastAPI, and MCP entrypoints
- Trace output for pack building and handoff rendering

## Explicit boundaries

This system currently does not:

- directly modify the target repository
- directly execute commands inside the target repository
- provide a full approval, tracking, or scheduling loop
- route work to external executors automatically
- persist traceability across downstream execution tasks

## Repository layout

- `requirement_review_v1/`: review workflow, delivery planning, handoff rendering, API, MCP server, schemas, and services
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
- `implementation_pack.json`
- `test_pack.json`
- `execution_pack.json`
- `codex_prompt.md`
- `claude_code_prompt.md`

## Validation

Run evaluation and tests:

```bash
python eval/run_eval.py
pytest -q
```
