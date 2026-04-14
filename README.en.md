# prd-pal

[中文](./README.md) | [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933?logo=nodedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=0A0A0A)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)
![Feishu](https://img.shields.io/badge/Feishu-Integrated-3370FF)
![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)

`prd-pal` is a PRD and requirement review service. It turns local files, raw text, or Feishu/Notion documents into structured review outputs such as findings, risks, open questions, and downloadable reports.

Before the first formal release, the recommended adoption path is:

1. Run it locally
2. Validate one sample review
3. Connect Feishu submission, clarification, and H5 result pages

## What You Get

- Web submission and result pages
- FastAPI backend
- CLI and MCP entry points
- Feishu submission, clarification writeback, and embedded H5 result support

## Quick Start Order

1. Clone the repository
2. Configure `.env`
3. Start backend and frontend locally
4. Run one sample PRD review
5. Configure Feishu callbacks and H5 entry URLs

## Requirements

- Python `3.11+`
- Node.js `22+`
- A valid model API key

## Local Quick Start

### 1. Clone

```bash
git clone <your-repo-url>
cd prd-pal
```

### 2. Configure `.env`

```bash
copy .env.example .env
```

Minimum local setup:

```dotenv
OPENAI_API_KEY=your-key
SMART_LLM=openai:gpt-5-nano
FAST_LLM=openai:gpt-5-nano
STRATEGIC_LLM=openai:gpt-5-nano
```

You do not need Feishu, Notion, auth, or rate-limit settings for the first local run.

### 3. Install dependencies

Backend:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

Frontend:

```bash
cd frontend
npm install
cd ..
```

### 4. Start services

Recommended on Windows:

```bash
start-dev.cmd
```

Or PowerShell:

```powershell
.\start-dev.ps1
```

Manual startup:

```bash
python main.py
cd frontend
npm run dev
```

Default addresses:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8000`
- Health: `http://127.0.0.1:8000/health`
- Ready: `http://127.0.0.1:8000/ready`

### 5. Validate the local flow

1. Open `http://127.0.0.1:5173`
2. Click `Load sample`
3. Submit one review
4. Confirm the result page shows progress, summary, and report downloads

CLI alternative:

```bash
prd-pal review --input docs/sample_prd.md
```

## Docker

To bring up the backend and production frontend bundle quickly:

```bash
docker-compose up --build
```

To run the Vite frontend in dev mode:

```bash
docker-compose --profile dev up dev
```

## Feishu Entry Docs

Feishu docs are split by audience so each reader can find the right actions quickly:

- Admin / deployer setup checklist:
  - [docs/feishu-setup.md](./docs/feishu-setup.md)
- End-user usage flow:
  - [docs/feishu-user-guide.md](./docs/feishu-user-guide.md)

## Common Entry Points

### Web

- Home:
  - `http://127.0.0.1:5173/`
- Feishu entry:
  - `https://<your-domain>/feishu`

### CLI

```bash
prd-pal review --input docs/sample_prd.md
prd-pal prepare-handoff --run-id 20260309T000000Z --agent all --json
prd-pal report --run-id 20260309T000000Z --format md
```

### FastAPI

- `POST /api/review`
- `GET /api/review/{run_id}`
- `GET /api/review/{run_id}/result`
- `GET /api/report/{run_id}?format=md|json|html|csv`
- `POST /api/feishu/events`
- `POST /api/feishu/submit`
- `POST /api/feishu/clarification`

### MCP

```bash
python -m prd_pal.mcp_server.server
```

Core tools:

- `ping`
- `review_requirement`
- `review_prd`
- `get_report`
- `answer_review_clarification`
- `prepare_agent_handoff`

## Outputs

Each run writes artifacts under `outputs/<run_id>/`.

Stable outputs:

- `report.md`
- `report.json`
- `run_trace.json`

Common parallel-review outputs:

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

Feishu-origin runs also persist:

- `entry_context.json`
- `audit_log.jsonl`

## Recommended Reading

- [docs/quick-start.md](./docs/quick-start.md)
- [docs/feishu-setup.md](./docs/feishu-setup.md)
- [docs/feishu-user-guide.md](./docs/feishu-user-guide.md)
- [docs/v2-api.md](./docs/v2-api.md)
- [docs/mcp.md](./docs/mcp.md)
- [docs/deployment-guide.md](./docs/deployment-guide.md)

## Validation

```bash
pytest -q
python eval/run_eval.py
```
