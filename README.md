# Multi-Agent Requirement Review Engine

A LangGraph-based requirement review engine that turns requirement sources into normalized review artifacts.

## System Position

The repository should be evaluated against this review-engine contract:

`source input -> review mode gating -> normalizer -> parallel reviewers -> aggregator -> review artifacts`

That review-result-first flow is the main architecture and the primary adoption path.

## Package Status

Package version `0.6.0` marks the current milestone baseline.

The review flow is usable today, but this package should not yet be treated as a fully stabilized platform release.

## Core Capabilities

- Multi-source requirement intake through `prd_text`, `prd_path`, and connector-backed `source`
- Review mode gating to choose between `single_review` and `parallel_review`
- Requirement normalization into reviewer-specific views
- Multi-role review across product, engineering, QA, and security perspectives
- Aggregation of reviewer findings, risks, open questions, and conflicts
- Review artifact generation for both human-readable and machine-readable outputs
- CLI, FastAPI, and MCP entrypoints centered on producing review results

## Supported Input Boundaries

- `prd_text`, `prd_path`, and local `.md` / `.txt` files remain the primary ingestion path.
- `URLConnector` supports public `http/https` text pages.
- `FeishuConnector` supports authenticated `feishu://...` inputs and recognized Feishu/Lark document URLs for supported `wiki`, `docx`, and legacy `docs` sources.
- `NotionConnector` supports authenticated `notion://page/...` inputs and recognized Notion page URLs, returning normalized Markdown content from the Notion API.
- Configure Feishu access with `MARRDP_FEISHU_APP_ID`, `MARRDP_FEISHU_APP_SECRET`, and optional `MARRDP_FEISHU_OPEN_BASE_URL`.
- Configure Notion access with `MARRDP_NOTION_TOKEN`, and optionally override `MARRDP_NOTION_API_BASE_URL` plus `MARRDP_NOTION_API_VERSION`.
- Controlled Feishu fetch failures are surfaced explicitly as authentication, permission, not-found, or unsupported-document-type errors in the API and MCP layers.
- Controlled Notion fetch failures are surfaced explicitly as authentication, permission, not-found, rate-limit, or network errors in the API and MCP layers.
- Local-file and public-URL ingestion behavior is unchanged.

## Source Support

- Local files: supported
- Public URLs: supported
- Feishu/Lark: supported
- Notion: supported

## Repository Layout

- `requirement_review_v1/`: review engine, service layer, API, MCP server, connectors, and supporting modules
- `review_runtime/`: shared runtime config and model provider utilities
- `docs/`: architecture notes, API docs, MCP docs, and implementation plans
- `eval/`: evaluation scripts
- `tests/`: automated tests
- `data/`: local knowledge and runtime data

## Installation

```bash
pip install -e .
```

## Quick Start

Use Docker to build and start the backend plus the production frontend bundle:

```bash
docker-compose up --build
```

## Usage

### CLI

Run one review from a local file:

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
```

### Review Engine Entry Points

- Use `review_requirement` when the consumer needs structured review output only.
- `review_prd` remains available as a compatibility surface in the current MCP implementation, but the mainline contract is the review result.

### FastAPI

Start the API server:

```bash
python main.py
```

Core review endpoints:

- `POST /api/review`
- `GET /api/review/{run_id}`
- `GET /api/report/{run_id}?format=md|json`

Supporting governance endpoints:

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
- `review_requirement`
- `review_prd`
- `get_report`

Use `review_requirement` when you want the review engine contract: `findings`, `open_questions`, `risk_items`, `conflicts`, `report_path`, and `review_mode`.

The MCP server may also expose compatibility or governance-oriented tools, but the stable review-engine contract is centered on the tools above.

## Outputs

Each run writes artifacts under `outputs/<run_id>/`.

Treat the following files as the stable review-engine outputs:

- `report.md`
- `report.json`
- `run_trace.json`

When the multi-reviewer path is used, the run may also include:

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

The run directory may contain additional compatibility artifacts produced by internal modules. Those files are not part of the main review-engine contract described in this README.

When a run starts from connector-backed `source` input, the normalized `source_metadata` is also persisted where supported, including `report.json`, `run_trace.json`, and `delivery_bundle.json`.

## Main Flow

The main flow is intentionally defined as:

1. Source input
2. Review mode gating
3. Normalizer
4. Parallel reviewers
5. Aggregator
6. Review artifacts

In current code, surrounding workflow nodes such as parser, planner, risk analysis, and reporting still exist. They support or enrich the review flow, but the top-level system definition remains anchored on review result production.

## Review Boundaries

- A successful mainline run means the repository produced review artifacts.
- The review-engine contract does not require approval, downstream orchestration, or external executor control to complete.
- Input handling outside local files, plain text, and public text URLs should be treated as an explicit integration boundary unless documented otherwise.

## Related Docs

- `docs/review-engine-positioning.md`: review-engine positioning and boundaries
- `docs/mcp.md`: MCP usage, with the review tools first
- `docs/v2-api.md`: FastAPI usage centered on review endpoints
- `docs/review-engine-release-prompts.md`: phased implementation prompts for frontend and release-gap work

## Validation

```bash
python eval/run_eval.py
pytest -q
```
