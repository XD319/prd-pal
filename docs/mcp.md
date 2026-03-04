# MCP Server 集成方案（只读调研结论）

## 1. 当前仓库现状

### 1.1 是否已有 MCP 相关依赖/代码
- 已有 MCP 依赖声明：
  - `pyproject.toml` 中存在 `mcp` 与 `langchain-mcp-adapters`
  - `requirements.txt` 中存在 `mcp>=1.9.1` 与 `langchain-mcp-adapters>=0.1.0`
- 已有 MCP 相关代码（主要在 GPT Researcher 子模块），例如：
  - `gpt_researcher/mcp/*`
  - `tests/test_mcp.py`
  - `mcp-server/README.md`（仅文档，当前仓库内未落地本项目的 requirement review MCP 服务端实现）

结论：仓库总体已具备 MCP 基础依赖与经验，但 `requirement_review_v1` 尚未有专用 MCP Server 对外暴露 `review_prd`。

### 1.2 Python 版本与依赖管理方式
- Python 版本：`.python-version` 为 `3.11`
- 依赖管理：同时存在
  - `pyproject.toml`（Poetry/PEP 621）
  - `requirements.txt`

## 2. MCP Server 目标

MCP Server 的目标是向外部 Agent/客户端稳定暴露 `review_prd` 能力：
- 输入 PRD 文本或 PRD 文件路径
- 复用现有 `requirement_review_v1.run_review` 工作流执行
- 输出与当前系统一致的产物路径与结构（`outputs/<run_id>/report.md|report.json|run_trace.json`）

## 3. 计划工具列表与 Schema

优先保证最小可用：先实现 `review_prd`；再补充查询类工具，便于异步/长任务场景。

### 3.1 `review_prd`（核心）
用途：发起一次 PRD 审查并返回结果（同步版可直接等待完成；后续可扩展异步模式）。

输入 schema（JSON Schema 草案）：
```json
{
  "type": "object",
  "properties": {
    "prd_text": { "type": "string", "minLength": 1 },
    "prd_path": { "type": "string", "minLength": 1 },
    "run_id": { "type": "string" },
    "outputs_root": { "type": "string", "default": "outputs" }
  },
  "oneOf": [
    { "required": ["prd_text"] },
    { "required": ["prd_path"] }
  ],
  "additionalProperties": false
}
```

输出 schema（JSON Schema 草案）：
```json
{
  "type": "object",
  "required": ["run_id", "run_dir", "report_paths"],
  "properties": {
    "run_id": { "type": "string" },
    "run_dir": { "type": "string" },
    "report_paths": {
      "type": "object",
      "required": ["report_md", "report_json", "run_trace"],
      "properties": {
        "report_md": { "type": "string" },
        "report_json": { "type": "string" },
        "run_trace": { "type": "string" }
      },
      "additionalProperties": false
    },
    "result": {
      "type": "object",
      "description": "与 run_review 返回一致的原始结果对象（可选透出）"
    }
  },
  "additionalProperties": false
}
```

### 3.2 `get_review_status`（建议）
用途：查询 `run_id` 对应任务状态（对齐现有 FastAPI `GET /api/review/{run_id}` 语义）。

输入 schema：
```json
{
  "type": "object",
  "required": ["run_id"],
  "properties": {
    "run_id": { "type": "string" }
  },
  "additionalProperties": false
}
```

输出 schema：
```json
{
  "type": "object",
  "required": ["run_id", "status", "progress", "report_paths"],
  "properties": {
    "run_id": { "type": "string" },
    "status": { "type": "string", "enum": ["queued", "running", "completed", "failed"] },
    "progress": { "type": "object" },
    "report_paths": { "type": "object" }
  },
  "additionalProperties": true
}
```

### 3.3 `get_review_report`（建议）
用途：按格式读取产物内容（对齐现有 FastAPI `GET /api/report/{run_id}?format=md|json`）。

输入 schema：
```json
{
  "type": "object",
  "required": ["run_id"],
  "properties": {
    "run_id": { "type": "string" },
    "format": { "type": "string", "enum": ["md", "json"], "default": "md" }
  },
  "additionalProperties": false
}
```

输出 schema：
```json
{
  "type": "object",
  "required": ["run_id", "format", "content"],
  "properties": {
    "run_id": { "type": "string" },
    "format": { "type": "string", "enum": ["md", "json"] },
    "content": {},
    "path": { "type": "string" }
  },
  "additionalProperties": false
}
```

## 4. 与现有 CLI / FastAPI 的关系（复用策略）

- CLI 现状：`requirement_review_v1/main.py` 通过 `run_review(...)` 执行并打印产物路径。
- FastAPI 现状：`requirement_review_v1/server/app.py` 已封装创建任务、查询状态、下载报告。

MCP 集成建议：
- 业务核心统一复用 `requirement_review_v1/run_review.py`，避免复制逻辑。
- `review_prd` 工具直接调用 `run_review(...)`，确保 `outputs` 目录结构与 `report.json` schema 保持一致。
- 查询类工具可复用 FastAPI 同等语义（不一定要 HTTP 调自己，优先直接复用同源函数/文件约定）。

## 5. MCP Python SDK 选型与接入方式建议

### 5.1 首选：stdio 模式
原因：
- 与本地 Agent/IDE 集成最直接，部署成本最低。
- 无需额外开放端口，适合先落地内部能力。
- 与 `review_prd` 这种工具调用型场景匹配度高。

建议实现：
- 使用官方 `mcp` Python SDK 创建 server。
- 先暴露 `review_prd` 单工具，确认端到端稳定后再补充 `get_review_status`/`get_review_report`。

### 5.2 次选：SSE/HTTP（按需）
适用场景：
- 需要远程多客户端共享同一 MCP 服务。
- 需要与现有 Web 平台做统一鉴权和网关治理。

建议：
- 第二阶段再引入，保持工具 schema 不变，仅替换 transport。
- 对长任务优先返回 `run_id`，由 `get_review_status` 轮询。

## 6. 最小依赖声明建议（本次不改代码）

仓库已具备基础 MCP 依赖，但建议后续整理为“服务端专用最小集”并统一到单一入口：
- 必需：`mcp>=1.9.1`
- 可选（仅当需要把外部 MCP 当数据源接入工作流时）：`langchain-mcp-adapters>=0.1.0`

额外注意：当前 `pyproject.toml` 中 `mcp` 带有 `platform_system != 'Windows'` marker；若目标运行环境包含 Windows，需要评估并调整该 marker 策略。
