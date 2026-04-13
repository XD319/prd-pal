# Deployment Guide

This guide describes the two recommended adoption paths for prd-pal.

## Path 1: Local Skill + Local Repository

Use this when:

- PRD content is sensitive
- a single user or a small team is validating the workflow
- rapid iteration matters more than centralized management

Recommended entrypoints:

- local skill: `skills/prd-review-agent/`
- CLI: `python -m prd_pal.main review --input <file> --json`
- MCP: `python -m prd_pal.mcp_server.server`
- preferred caller contract: `prd_text` / local files first, connector-backed `source` only when explicitly needed

## Path 2: Shared Service + Remote Skill

Use this when:

- multiple users need the same review service
- you want one deployed version of the backend
- you need centralized logging, auth, and runtime settings

Recommended entrypoints:

- remote skill: `skills/prd-review-service/`
- HTTP API: FastAPI service on port `8000`
- preferred caller contract: `prd_text` first, remote connector-backed `source` only for weak callers or centralized-ingestion use cases

## Recommended System Boundary

Treat the deployed review service as the review kernel first and the source-ingestion layer second.

- Strong callers should fetch third-party documents themselves and submit `prd_text`.
- Weak callers may rely on project-side `source` ingestion when they can only provide a document identifier or URL.
- Clarification loops and handoff decisions are usually best orchestrated by the caller's agent, while the project keeps the persisted review state and optional follow-up APIs.

## Container Deployment

Build and run:

```bash
docker-compose up --build
```

The container now exposes:

- `GET /health`
- `GET /ready`
- `POST /api/review`
- `GET /api/review/{run_id}`
- `GET /api/review/{run_id}/result`
- `GET /api/report/{run_id}?format=md|json|html|csv`

## Health Checks

Use these checks for load balancers, orchestrators, and monitoring:

- `GET /health`
  - process-level health
- `GET /ready`
  - startup completion plus output-directory writability

`Dockerfile` and `docker-compose.yml` include health checks using `/health`.

## Security Notes

- Prefer private deployment for internal PRDs.
- Use local-skill mode when PRD text should not leave the developer machine.
- For remote skill mode, prefer submitting `prd_text` directly instead of remote connector sources unless explicitly needed.
- If connector-backed `source` is enabled, treat third-party auth, permissions, and rate limits as integration-layer concerns rather than the core review contract.
- Do not return full report payloads or auth headers to users unless they explicitly ask for them.

## Recommended Rollout

1. Start with the local skill and local CLI.
2. Keep MCP available for agent-native integrations.
3. Normalize around `prd_text` for strong callers before turning on enterprise source connectors.
4. Deploy the FastAPI service privately.
5. Add auth, TLS, and reverse proxying at the platform layer.
6. Introduce the remote skill for shared service access.
7. Turn on Feishu or Notion `source` intake only when weak-caller support or centralized ingestion is required.
