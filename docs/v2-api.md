# Requirement Review API

This document describes the current FastAPI surface with review-first positioning.

## Positioning

The HTTP API is centered on review result generation.

Core API flow:

1. Submit a review
2. Poll review status
3. Fetch the generated report

The repository also exposes governance-support endpoints, but the main architecture remains review-first.

## Start The Server

```bash
python main.py
```

Or directly:

```bash
uvicorn requirement_review_v1.server.app:app --host 0.0.0.0 --port 8000 --reload
```

## Core Review Endpoints

### `POST /api/review`

Create one review run.

Request body accepts:

- `source`
- `prd_text`
- `prd_path`

`source` is the preferred forward-looking input. `prd_text` and `prd_path` remain supported for compatibility.

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"docs/sample_prd.md\"}"
```

Response:

```json
{
  "run_id": "20260309T000000Z"
}
```

### `GET /api/review/{run_id}`

Fetch job status and node progress.

Example:

```bash
curl "http://127.0.0.1:8000/api/review/20260309T000000Z"
```

Typical response fields:

- `status`
- `progress.percent`
- `progress.current_node`
- `progress.nodes`
- `report_paths`

### `GET /api/report/{run_id}?format=md|json`

Download the main report artifact.

Examples:

```bash
curl "http://127.0.0.1:8000/api/report/20260309T000000Z?format=md"
curl "http://127.0.0.1:8000/api/report/20260309T000000Z?format=json"
```

## Primary Output Interpretation

For API consumers, every review run centers on:

- `report.md`
- `report.json`
- `run_trace.json`

When the multi-reviewer path is selected, the run may also include:

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

The current service implementation may also write retained extension artifacts in the same directory. That does not change the API's review-first positioning.

## Supporting Governance Endpoints

The API also exposes supporting endpoints that belong to the extension or governance layer:

- `GET /api/templates`
- `GET /api/templates/{template_type}`
- `GET /api/audit`

These endpoints help inspect prompt/template metadata and audit events, but they are not required for the main review flow.

## What The HTTP API Does Not Currently Expose

The current FastAPI app does not expose approval or execution-orchestration endpoints directly.

Those retained orchestration capabilities are currently emphasized through the MCP layer rather than the HTTP layer.
