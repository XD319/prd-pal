---
name: prd-review-service
description: Review PRD drafts through a deployed PRDReview HTTP service. Use when the user wants to call a shared private-cloud or internal PRDReview API instead of a local repository checkout. This skill submits PRD content to the review API, polls run status, fetches review results, and summarizes findings without exposing raw secrets.
---

# Prd Review Service

## Overview

Use a deployed PRDReview HTTP API as the source of truth for review results. Prefer sending PRD content as request JSON, poll the run until completion, and summarize the review output instead of echoing raw payloads.

## Workflow

### 1. Resolve the service endpoint and auth

Require a concrete base URL before sending review traffic.

- Use the user-provided PRDReview base URL, or a preconfigured internal URL.
- If the service requires authentication, send the API key in headers only. Never echo it back in chat.
- Before first use, prefer checking `GET <base-url>/health` and `GET <base-url>/ready`.

### 2. Prepare the PRD payload

Prefer request JSON content over server-side file paths.

- If the user gave a local PRD file, read the file and submit its content as `prd_text`.
- If the user pasted the draft directly, submit it as `prd_text`.
- Do not send remote connector `source` values such as URLs, Feishu, or Notion unless the user explicitly asks for them.
- Do not send local machine paths as `prd_path` to a remote service unless the user confirms the server can access the same filesystem.

### 3. Start the review run

Submit:

`POST <base-url>/api/review`

Example body:

```json
{
  "prd_text": "<full prd markdown>"
}
```

Read the returned `run_id`.

### 4. Poll until completion

Poll:

`GET <base-url>/api/review/<run_id>`

Wait until the run is completed or failed.

### 5. Fetch the result

Prefer:

`GET <base-url>/api/review/<run_id>/result`

If needed, fetch:

`GET <base-url>/api/report/<run_id>?format=json`

Extract and summarize:

- `findings`
- `open_questions`
- `risk_items`
- `conflicts`
- review status and readiness signals

### 6. Respond in review-first mode

Provide:

- top ambiguities and missing requirement details
- concrete PRD rewrite suggestions
- a compact readiness judgment

Do not paste full raw reports, full request payloads, or authentication headers back into chat unless the user explicitly asks.

## Operating Rules

- Treat the deployed API as the system of record.
- Prefer `prd_text` for remote submission.
- Avoid connector-backed remote `source` values unless the user explicitly requests them.
- Never reveal API keys, bearer tokens, or auth headers in your response.
- If the user wants downstream coding-agent handoff generation, explain that the current shared HTTP flow is review-first; use local CLI or MCP when handoff prep is required.
