# prd-pal

[中文](./README.md) | [English](./README.en.md)

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Node.js](https://img.shields.io/badge/Node.js-22%2B-339933?logo=nodedotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=0A0A0A)
![Docker](https://img.shields.io/badge/Docker-Supported-2496ED?logo=docker&logoColor=white)
![Feishu](https://img.shields.io/badge/Feishu-Integrated-3370FF)
![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)

`prd-pal` 是一个面向 PRD/需求文档的评审服务。它可以把本地文件、纯文本或 Feishu/Notion 文档转成结构化评审结果，包括 findings、risks、open questions 和可下载报告。

正式发布前，推荐把它当作一套“先本地跑通，再接入飞书”的评审服务来使用。

## 你会得到什么

- Web 提审页与结果页
- FastAPI 服务接口
- CLI 与 MCP 入口
- Feishu 提交、澄清回写、H5 结果页接入能力

## 30 秒看懂上手顺序

1. 下载仓库
2. 配置 `.env`
3. 本地启动前后端
4. 用 sample PRD 跑通一次
5. 再配置 Feishu 回调与 H5 打开地址

## 环境要求

- Python `3.11+`
- Node.js `22+`
- 一个可用的模型 API Key
- Windows 本地开发可直接使用仓库内脚本；macOS/Linux 可用 `python` + `npm` 或 Docker

## 一、本地快速跑通

### 1. 下载仓库

```bash
git clone <your-repo-url>
cd prd-pal
```

### 2. 配置环境变量

复制示例文件：

```bash
copy .env.example .env
```

本地最小可用配置只需要：

```dotenv
OPENAI_API_KEY=your-key
SMART_LLM=openai:gpt-5-nano
FAST_LLM=openai:gpt-5-nano
STRATEGIC_LLM=openai:gpt-5-nano
```

第一次跑通时，不需要先填 Feishu、Notion、鉴权和限流相关变量。

### 3. 安装依赖

后端：

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

前端：

```bash
cd frontend
npm install
cd ..
```

### 4. 启动服务

Windows 推荐直接运行：

```bash
start-dev.cmd
```

或 PowerShell：

```powershell
.\start-dev.ps1
```

如果你更习惯手动启动：

```bash
python main.py
cd frontend
npm run dev
```

默认地址：

- 前端: `http://127.0.0.1:5173`
- 后端: `http://127.0.0.1:8000`
- 健康检查: `http://127.0.0.1:8000/health`
- 就绪检查: `http://127.0.0.1:8000/ready`

### 5. 验证本地链路

推荐按这个顺序验证：

1. 打开首页 `http://127.0.0.1:5173`
2. 点击 `Load sample`
3. 提交一次评审
4. 打开结果页确认能看到进度、总结和报告下载

也可以直接走 CLI：

```bash
prd-pal review --input docs/sample_prd.md
```

或：

```bash
python -m prd_pal.main review --input docs/sample_prd.md
```

## 二、Docker 跑通

如果你想先快速启动完整服务，可以直接用 Docker：

```bash
docker-compose up --build
```

这会启动：

- 后端服务
- 生产版前端静态资源

如果你还需要 Vite 开发模式前端：

```bash
docker-compose --profile dev up dev
```

## 三、飞书入口（管理员与用户）

飞书相关文档已按角色拆分，便于直接作为主入口使用：

- 管理员 / 部署者（应用配置、域名与上线检查）：
  - [docs/feishu-setup.md](./docs/feishu-setup.md)
- 普通用户（在飞书里提交、查看结果、回答澄清）：
  - [docs/feishu-user-guide.md](./docs/feishu-user-guide.md)

如果你是首次接入，推荐顺序：

1. 先完成“本地快速跑通”
2. 按 `docs/feishu-setup.md` 完成管理员最小配置清单
3. 按 `docs/feishu-user-guide.md` 验证普通用户流程

## 四、常用入口

### Web

- 首页:
  - `http://127.0.0.1:5173/`
- 飞书提交入口:
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

核心工具：

- `ping`
- `review_requirement`
- `review_prd`
- `get_report`
- `answer_review_clarification`
- `prepare_agent_handoff`

## 五、输出物

每次运行默认写到 `outputs/<run_id>/`。

稳定输出：

- `report.md`
- `report.json`
- `run_trace.json`

并行评审路径下通常还会有：

- `review_report.json`
- `risk_items.json`
- `open_questions.json`
- `review_summary.md`

飞书来源运行还会带上：

- `entry_context.json`
- `audit_log.jsonl`

## 六、推荐阅读顺序

- [docs/quick-start.md](./docs/quick-start.md)
- [docs/feishu-setup.md](./docs/feishu-setup.md)
- [docs/feishu-user-guide.md](./docs/feishu-user-guide.md)
- [docs/v2-api.md](./docs/v2-api.md)
- [docs/mcp.md](./docs/mcp.md)
- [docs/deployment-guide.md](./docs/deployment-guide.md)

## 七、验证

```bash
pytest -q
python eval/run_eval.py
```
