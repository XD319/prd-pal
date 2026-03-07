# Release Notes v4

## Summary

v4 establishes the mainline baseline for requirement review, delivery planning, and coding-agent handoff generation.

The system now goes beyond a review-only workflow and produces structured downstream artifacts that can be handed to implementation and testing agents without directly operating on the target repository.

## New capabilities in v4

- Delivery planning is integrated into the LangGraph review flow.
- The system generates structured planning and handoff outputs from one review run.
- New JSON handoff packs are produced:
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
- New Markdown prompts are rendered from the execution pack:
  - `codex_prompt.md`
  - `claude_code_prompt.md`
- CLI, FastAPI, and MCP entrypoints share the same review service layer.
- Run trace output now records pack-building and handoff-rendering status.

## What changed from v3

Compared with v3, v4 changes the system narrative from "requirement review workflow" to "requirement review plus delivery preparation".

Key differences:

- v3 focused on review outputs and report generation.
- v4 adds delivery planning artifacts for implementation and testing.
- v4 adds coding-agent handoff generation for Codex and Claude Code.
- v4 keeps the review pipeline as the primary source, then derives downstream packs and prompts from that result.

## Known limitations

The following limitations remain in v4:

- No real connector abstraction layer exists yet.
  - Inputs are still centered on local text or file-based PRD ingestion.
- No formal multi-artifact delivery bundle exists yet.
  - The system still centers on a combined report plus three packs, rather than a fully standardized artifact family.
- No approval state machine or human gate exists yet.
  - States such as `approved`, `need_more_info`, and `blocked_by_risk` are not implemented.
- No executor orchestration layer exists yet.
  - The system generates handoff files but does not manage actual executor routing or execution modes.
- No persistent traceability repository exists yet.
  - End-to-end links across requirements, review items, plan tasks, test items, and execution tasks are not maintained.
- No execution task lifecycle exists yet.
  - Existing status tracking is oriented around review runs, not downstream execution work.
- The MCP tool surface is still minimal.
  - Current tools focus on review and report retrieval, not full delivery management.

## Forward look

Planned next steps:

- v5: delivery artifact standardization and minimal approval loop
- v6: execution orchestration, status management, and traceability
