# Deployment Guide

This guide describes the two recommended adoption paths for PRDReview.

## Path 1: Local Skill + Local Repository

Use this when:

- PRD content is sensitive
- a single user or a small team is validating the workflow
- rapid iteration matters more than centralized management

Recommended entrypoints:

- local skill: `skills/prd-review-agent/`
- CLI: `python -m requirement_review_v1.main review --input <file> --json`
- MCP: `python -m requirement_review_v1.mcp_server.server`

## Path 2: Shared Service + Remote Skill

Use this when:

- multiple users need the same review service
- you want one deployed version of the backend
- you need centralized logging, auth, and runtime settings

Recommended entrypoints:

- remote skill: `skills/prd-review-service/`
- HTTP API: FastAPI service on port `8000`

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
- Do not return full report payloads or auth headers to users unless they explicitly ask for them.

## Recommended Rollout

1. Start with the local skill and local CLI.
2. Keep MCP available for agent-native integrations.
3. Deploy the FastAPI service privately.
4. Add auth, TLS, and reverse proxying at the platform layer.
5. Introduce the remote skill for shared service access.
