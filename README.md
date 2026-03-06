# Multi-Agent Requirement Review and Delivery Planning System

A LangGraph-based workflow that turns a PRD into a structured requirement review, delivery plan, risk register, and runnable artifacts.

## What remains in this repository

- `requirement_review_v1/`: the review workflow, API, MCP server, schemas, and services
- `review_runtime/`: the minimal shared runtime for config loading and LLM provider access
- `eval/`: regression evaluation cases and runner
- `data/risk_catalog.json`: local risk knowledge base
- `docs/`: project-specific notes, API docs, and sample PRD
- `tests/`: requirement-review focused tests only

## Quickstart

```bash
pip install -e .
python -m requirement_review_v1.main --input docs/sample_prd.md
```

Start the API server:

```bash
python main.py
```

Run evaluation and tests:

```bash
python eval/run_eval.py
pytest -q
```

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

## MCP server

Run the MCP server in stdio mode:

```bash
python -m requirement_review_v1.mcp_server.server
```
