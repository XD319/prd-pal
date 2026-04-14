# prd-pal

[中文](./README.md) | [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933?logo=nodedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=0A0A0A)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)
![Feishu](https://img.shields.io/badge/Feishu-Integrated-3370FF)
![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)

`prd-pal` is a PRD and requirement review service with a **Feishu-first** product entry. End users can submit reviews, read H5 results, answer clarifications, and continue follow-up actions directly inside Feishu.

Web and CLI are fully retained as trial and engineering entry points.

## What Feishu Entry Delivers

1. Start PRD review from Feishu
2. Open embedded H5 result pages in Feishu
3. Answer clarification questions in-page
4. Continue next-step delivery actions after updates

## 30-Second Start (Feishu-first)

1. Complete admin setup in [docs/feishu-setup.md](./docs/feishu-setup.md)
2. Open Feishu entry page: `https://<your-domain>/feishu`
3. Submit PRD source/text and get a run
4. Open result page in Feishu: `/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>`
5. Answer clarification prompts and continue to next delivery actions

## Requirements

- Python `3.11+`
- Node.js `22+`
- A valid model API key

## Feishu Docs First

- Admin / deployer setup:
  - [docs/feishu-setup.md](./docs/feishu-setup.md)
- End-user guide:
  - [docs/feishu-user-guide.md](./docs/feishu-user-guide.md)
- Feishu main-entry interaction plan:
  - [docs/feishu-main-entry-mvp.md](./docs/feishu-main-entry-mvp.md)
- Demo material playbook:
  - [docs/feishu-demo-assets.md](./docs/feishu-demo-assets.md)

## Local Quick Start (trial/development)

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

## Common Entry Points

### Feishu (primary entry)

- Feishu work entry:
  - `https://<your-domain>/feishu`
- Feishu H5 result URL template:
  - `https://<your-domain>/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>`

### Web (trial/development)

- Home:
  - `http://127.0.0.1:5173/`
### CLI (trial/development)

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
- [docs/feishu-demo-assets.md](./docs/feishu-demo-assets.md)
- [docs/v2-api.md](./docs/v2-api.md)
- [docs/mcp.md](./docs/mcp.md)
- [docs/deployment-guide.md](./docs/deployment-guide.md)

## Validation

```bash
pytest -q
python eval/run_eval.py
```
