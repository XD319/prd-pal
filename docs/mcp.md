# Requirement Review MCP Guide

This document explains how to run the repository's MCP server with review-first positioning.

## Positioning

The MCP surface should be understood in two layers:

- Core tools: review-only tools used to create and fetch review results
- Extension tools: retained orchestration and governance tools built on top of those review results

If you are integrating this repository for the first time, start with the core tools only.

## Prerequisites

- Python 3.11+
- Required model credentials in the environment
- Repository root as the working directory

## Start The MCP Server

```powershell
python -m requirement_review_v1.mcp_server.server
```

The server uses stdio transport and is normally launched by an MCP client.

## Core Review Tools

These are the primary tools to emphasize:

- `ping`
  - Health check for MCP connectivity
- `review_requirement`
  - Review-only facade for the project's main review-engine positioning
  - Accepts `source`, `prd_text`, `prd_path`, plus `metadata` or `options`
  - Returns `review_id`/`run_id`, `findings`, `open_questions`, `risk_items`, `conflicts`, `report_path`, and `review_mode`
- `review_prd`
  - Retained fuller workflow entrypoint for clients that still want metrics and downstream artifact paths
  - Accepts `prd_text`, `prd_path`, or `source`
  - Returns `run_id`, review metrics, and artifact paths
- `get_report`
  - Fetches `report.md` or `report.json` for a completed run

Recommended first integration flow:

1. Call `ping`
2. Call `review_requirement`
3. Use the returned `review_id` or `run_id`
4. Call `get_report`

## Core Example

Use any MCP client to call:

```json
{
  "tool": "review_requirement",
  "arguments": {
    "source": "docs/sample_prd.md"
  }
}
```

Then fetch the report:

```json
{
  "tool": "get_report",
  "arguments": {
    "run_id": "20260309T000000Z",
    "format": "md"
  }
}
```

## Core Outputs

Every review run centers on:

- `report.md`
- `report.json`
- `run_trace.json`

When the multi-reviewer path is selected, the run may also include:

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

The implementation may also persist additional extension artifacts in the same run directory, but those are not required to understand the core MCP usage.

## Extension Tools

The repository retains additional MCP tools for downstream orchestration and governance:

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

These tools are extension-layer tools. They remain available because the corresponding code is still in the repository.

## Extension Workflow Example

Only after a review result exists, an extension flow can continue with:

1. `generate_delivery_bundle`
2. `approve_handoff`
3. `handoff_to_executor`
4. `get_execution_status`
5. `get_traceability`

This is optional and should not be confused with the main review architecture.

## Notes For Client Authors

- Prefer `source` for new integrations when you want connector-based intake.
- Keep `prd_text` and `prd_path` for backward compatibility.
- Treat `review_requirement` as the review-only facade.
- Treat `review_prd` as the richer compatibility surface when you intentionally need bundle-adjacent artifact paths in the same response.
- Treat review completion as successful even if you do not use any orchestration tool.
- Do not assume extension tools are deprecated; they are retained, just not first-layer.
