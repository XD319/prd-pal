# Requirement Review API

This document describes the current FastAPI surface with review-first positioning.

## Positioning

The HTTP API is centered on review result generation.

Core API flow:

1. Submit a review
2. Poll review status
3. Fetch the generated report
4. List recent runs for frontend history views

The repository also exposes governance-support endpoints, but the main architecture remains review-first.

## Start The Server

```bash
python main.py
```

Or directly:

```bash
uvicorn requirement_review_v1.server.app:app --host 0.0.0.0 --port 8000 --reload
```

## Shared-Environment Hardening

The FastAPI surface now supports a simple environment-controlled auth layer and a submission rate limiter.

Environment variables:

- `MARRDP_API_AUTH_DISABLED=true|false`
- `MARRDP_API_KEY=`
- `MARRDP_API_BEARER_TOKEN=`
- `MARRDP_API_RATE_LIMIT_DISABLED=true|false`
- `MARRDP_API_RATE_LIMIT_MAX_REQUESTS=5`
- `MARRDP_API_RATE_LIMIT_WINDOW_SEC=60`

Recommended modes:

- Local development: keep `MARRDP_API_AUTH_DISABLED=true` and `MARRDP_API_RATE_LIMIT_DISABLED=true`.
- Shared environment: set `MARRDP_API_AUTH_DISABLED=false`, configure `MARRDP_API_KEY` and/or `MARRDP_API_BEARER_TOKEN`, then enable rate limiting with `MARRDP_API_RATE_LIMIT_DISABLED=false`.

Auth behavior:

- Send `X-API-Key: <secret>` or `Authorization: Bearer <token>`.
- If auth is enabled but no credentials are configured, the API returns a controlled `503` instead of exposing the surface anonymously.
- Invalid or missing credentials return controlled `401` responses.

Rate-limit behavior:

- The limiter applies to `POST /api/review`.
- When the limit is exceeded, the API returns `429` with `detail.code = rate_limit_exceeded` and a `Retry-After` header.

Controlled errors:

- Request validation failures return `422` with `detail.code = request_validation_error`.
- Unexpected server failures return `500` with `detail.code = internal_server_error`.

## Core Review Endpoints

### `POST /api/review`

Create one review run.

Request body accepts:

- `source`
- `prd_text`
- `prd_path`
- `mode`
- `smart_llm`
- `fast_llm`
- `strategic_llm`
- `temperature`
- `reasoning_effort`
- `llm_kwargs`

`source` is the preferred forward-looking input. It accepts local files, public text URLs, and authenticated Feishu/Lark sources. `prd_text` and `prd_path` remain supported for compatibility.

Model override notes:

- These LLM fields are optional and apply only to the submitted run.
- Use the existing `<provider>:<model>` format, for example `openai:gpt-5-nano` or `deepseek:deepseek-chat`.
- This makes it easy to keep the service default on OpenAI while temporarily testing Chinese output quality with DeepSeek.

Example with API key:

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-secret" \
  -d "{\"source\":\"docs/sample_prd.md\"}"
```

Example with bearer token:

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer shared-env-token" \
  -d "{\"source\":\"docs/sample_prd.md\"}"
```

Example with a temporary DeepSeek override:

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: local-dev-secret" \
  -d "{\"source\":\"docs/sample_prd.md\",\"smart_llm\":\"deepseek:deepseek-chat\"}"
```

Response:

```json
{
  "run_id": "20260309T000000Z"
}
```

Feishu source notes:

- Supported source forms include recognized `https://*.feishu.cn/...`, `https://*.larksuite.com/...`, and `feishu://...` document references.
- Supported Feishu document types are `wiki`, `docx`, and legacy `docs` documents that can be converted to `docx`.
- Set `MARRDP_FEISHU_APP_ID` and `MARRDP_FEISHU_APP_SECRET` before submitting authenticated Feishu sources.
- Override `MARRDP_FEISHU_OPEN_BASE_URL` only when you need a non-default Open API base URL.

### `GET /api/runs`

List recent review runs discovered under `outputs/`.

This endpoint is file-based and lightweight: it scans run directories and reports artifact presence without eagerly parsing large review payloads.

Example:

```bash
curl -H "X-API-Key: local-dev-secret" "http://127.0.0.1:8000/api/runs"
```

Typical response:

```json
{
  "count": 2,
  "runs": [
    {
      "run_id": "20260309T030405Z",
      "status": "completed",
      "created_at": "2026-03-09T03:04:05+00:00",
      "updated_at": "2026-03-09T03:05:12+00:00",
      "artifact_presence": {
        "report_md": true,
        "report_json": true,
        "run_trace": true,
        "review_report_json": true,
        "risk_items_json": true,
        "open_questions_json": true,
        "review_summary_md": true
      }
    }
  ]
}
```

Each run includes:

- `run_id`
- `status`
- `created_at`
- `updated_at`
- `artifact_presence`

### `GET /api/review/{run_id}`

Fetch job status and node progress.

Example:

```bash
curl -H "X-API-Key: local-dev-secret" "http://127.0.0.1:8000/api/review/20260309T000000Z"
```

Typical response fields:

- `status`
- `progress.percent`
- `progress.current_node`
- `progress.nodes`
- `report_paths`
- `error` when the run has failed with a controlled connector or processing error

For failed Feishu connector runs, the response keeps `status: failed` and includes a structured error such as `AUTHENTICATION_FAILED`, `PERMISSION_DENIED`, `DOCUMENT_NOT_FOUND`, or `UNSUPPORTED_DOCUMENT_TYPE`.

### `GET /api/review/{run_id}/result`

Fetch the parsed result payload and stable artifact paths for a completed run.

If the run is still in progress, the endpoint returns `409` with `detail.code = result_not_ready`. If the run failed before writing `report.json`, the endpoint returns `409` with the controlled failure code and message so connector failures remain visible to API clients.

### `GET /api/report/{run_id}?format=md|json`

Download the main report artifact.

Examples:

```bash
curl -H "X-API-Key: local-dev-secret" "http://127.0.0.1:8000/api/report/20260309T000000Z?format=md"
curl -H "X-API-Key: local-dev-secret" "http://127.0.0.1:8000/api/report/20260309T000000Z?format=json"
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

When a review is created from `source`, connector metadata is preserved in run artifacts where supported. In particular, `report.json`, `run_trace.json`, and `delivery_bundle.json` retain `source_metadata` for downstream inspection.

## Supporting Governance Endpoints

The API also exposes supporting endpoints that belong to the extension or governance layer:

- `GET /api/templates`
- `GET /api/templates/{template_type}`
- `GET /api/audit`

These endpoints help inspect prompt/template metadata and audit events, but they are not required for the main review flow.

## What The HTTP API Does Not Currently Expose

The current FastAPI app does not expose approval or execution-orchestration endpoints directly.

Those retained orchestration capabilities are currently emphasized through the MCP layer rather than the HTTP layer.

