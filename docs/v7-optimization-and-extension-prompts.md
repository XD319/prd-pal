# v7 优化与功能拓展 — 分阶段提示词（含完整 Git 工作流）

基于 v0.6.0 现状分析，本文档将所有可优化项和可拓展功能拆分为 **8 个 Phase**，每个 Phase 包含：

- 目标概述
- 前置条件
- 完整 Git 工作流（新建分支 → 实现 → 测试 → 提交 → 推送 → PR）
- 可直接交给 AI Agent 执行的提示词
- 验收标准

---

## 目录

- [Phase 1: Docker 容器化与部署支持](#phase-1-docker-容器化与部署支持)
- [Phase 2: SSE 实时进度推送](#phase-2-sse-实时进度推送)
- [Phase 3: Notion Connector 实现](#phase-3-notion-connector-实现)
- [Phase 4: 前端测试框架搭建](#phase-4-前端测试框架搭建)
- [Phase 5: 结构化日志与可观测性增强](#phase-5-结构化日志与可观测性增强)
- [Phase 6: Review 结果对比与趋势分析](#phase-6-review-结果对比与趋势分析)
- [Phase 7: 用户认证与权限管理](#phase-7-用户认证与权限管理)
- [Phase 8: 自定义 Reviewer 角色与增量 Review](#phase-8-自定义-reviewer-角色与增量-review)

---

## Phase 1: Docker 容器化与部署支持

### 目标

项目当前没有任何容器化支持。本阶段为后端 + 前端添加 Docker 化部署能力，并通过 docker-compose 实现一键启动。

### 前置条件

- 主分支代码可正常 `pip install -e .` 且 `npm run build` 成功
- 本地 Docker Desktop 已安装

### Git 工作流

```bash
# 1. 从主分支创建新分支
git checkout main
git pull origin main
git checkout -b feature/phase1-docker-containerization

# 2. 实现完成后提交
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker containerization with multi-stage build and docker-compose"

# 3. 如有后续修改，追加提交
git add -A
git commit -m "fix: adjust Docker build context and env handling"

# 4. 推送到远程
git push -u origin feature/phase1-docker-containerization

# 5. 创建 PR
gh pr create --title "feat: Docker containerization support" --body "## Summary
- Add multi-stage Dockerfile for backend + frontend
- Add docker-compose.yml for one-command startup
- Add .dockerignore to optimize build context

## Test plan
- [ ] docker build completes without errors
- [ ] docker-compose up starts both services
- [ ] Frontend accessible at localhost:5173
- [ ] API accessible at localhost:8000/api/runs
"
```

### 提示词

```text
在项目根目录下完成以下 Docker 容器化工作：

1. 创建 `.dockerignore` 文件：
   - 排除 `node_modules/`, `__pycache__/`, `.env`, `outputs/`, `logs/`, `.git/`, `*.pyc`, `eval/`

2. 创建多阶段 `Dockerfile`：
   - 阶段一 (frontend-build)：基于 node:22-alpine，复制 frontend/ 目录，执行 npm ci && npm run build
   - 阶段二 (runtime)：基于 python:3.12-slim
     - 安装系统依赖
     - 复制 requirements.txt 并 pip install
     - 复制 Python 源码（requirement_review_v1/, review_runtime/, main.py, pyproject.toml）
     - 从阶段一复制构建产物到 /app/frontend/dist
     - 设置环境变量 PYTHONUNBUFFERED=1
     - EXPOSE 8000
     - CMD 为 uvicorn 启动命令

3. 修改 `requirement_review_v1/server/app.py`：
   - 添加静态文件挂载：当 `frontend/dist` 目录存在时，使用 FastAPI 的 StaticFiles 挂载到 `/`
   - 保持 API 路由优先级高于静态文件

4. 创建 `docker-compose.yml`：
   - 服务 `app`：构建当前目录，映射 8000 端口，通过 env_file 加载 .env，挂载 outputs/ 为 volume 持久化
   - 可选服务 `dev`：profile 为 dev，同时映射 5173 端口，挂载源码实现热重载

5. 更新 README.md，在 Quick Start 部分添加 Docker 启动方式：
   ```
   docker-compose up --build
   ```

验收标准：
- `docker build -t marrdp .` 成功
- `docker run -p 8000:8000 --env-file .env marrdp` 启动后 curl localhost:8000/api/runs 返回 200
- `docker-compose up` 一键启动成功
- 前端静态文件在生产模式下可通过后端直接访问
```

---

## Phase 2: SSE 实时进度推送

### 目标

将前端的 polling 进度获取替换为 Server-Sent Events (SSE) 推送，减少无效请求，提升 review 过程中的实时体验。

### 前置条件

- Phase 1 完成（非强制，但推荐）
- 了解当前 `RunProgressCard` 和 `useReviewRun` 的 polling 机制

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase2-sse-progress

# 后端 SSE endpoint
git add requirement_review_v1/server/app.py requirement_review_v1/server/sse.py
git commit -m "feat: add SSE endpoint for real-time review progress streaming"

# 前端适配
git add frontend/src/hooks/useReviewRunSSE.js frontend/src/components/RunProgressCard.jsx
git commit -m "feat: replace polling with SSE in RunProgressCard"

# 测试
git add tests/test_server_sse.py
git commit -m "test: add SSE endpoint integration tests"

git push -u origin feature/phase2-sse-progress

gh pr create --title "feat: SSE real-time progress push" --body "## Summary
- Add GET /api/review/{run_id}/progress/stream SSE endpoint
- Replace frontend polling with EventSource
- Graceful fallback to polling when SSE unavailable

## Test plan
- [ ] SSE endpoint streams node-level progress events
- [ ] Frontend receives and renders progress in real-time
- [ ] Connection auto-reconnects on disconnect
- [ ] Polling fallback works when SSE fails
"
```

### 提示词 — Step 1: 后端 SSE endpoint

```text
为 FastAPI 后端添加 SSE（Server-Sent Events）实时进度推送能力：

1. 创建 `requirement_review_v1/server/sse.py` 模块：
   - 实现一个 `ProgressBroadcaster` 单例类：
     - 内部维护 `dict[str, asyncio.Queue]` 按 run_id 管理订阅者队列
     - `subscribe(run_id) -> AsyncGenerator`：注册一个新队列并 yield SSE 格式的事件
     - `publish(run_id, event_type, data)`：向该 run_id 的所有订阅者队列推送事件
     - `unsubscribe(run_id, queue)`：取消订阅时清理队列
   - SSE 事件格式：`data: {"node": "parser", "status": "start", "timestamp": "..."}\n\n`

2. 修改 `requirement_review_v1/server/app.py`：
   - 添加新路由 `GET /api/review/{run_id}/progress/stream`
   - 使用 `StreamingResponse(media_type="text/event-stream")` 返回 SSE 流
   - 设置 headers：`Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`
   - 当 run 已完成时，发送最终状态事件后关闭流

3. 修改 `requirement_review_v1/service/review_service.py`：
   - 在现有的 `progress_hook` 中，除了现有逻辑外，同时调用 `ProgressBroadcaster.publish()`
   - 保证原有 progress 文件持久化逻辑不受影响（SSE 是新增通道，不是替代）

4. 添加测试 `tests/test_server_sse.py`：
   - 测试 SSE endpoint 返回正确的 Content-Type
   - 测试订阅 → 发布 → 接收的流程
   - 测试 run 完成后流自动关闭

验收标准：
- curl -N http://localhost:8000/api/review/{run_id}/progress/stream 能收到持续的事件流
- 多个客户端可以同时订阅同一个 run_id
- 不影响现有的 progress polling endpoint
```

### 提示词 — Step 2: 前端 SSE 适配

```text
修改前端，将 review 进度从 polling 切换为 SSE：

1. 创建 `frontend/src/hooks/useReviewRunSSE.js`：
   - 使用浏览器原生 EventSource API 连接 `/api/review/{runId}/progress/stream`
   - 监听 `message` 事件，解析 JSON data 更新 progress 状态
   - 实现自动重连逻辑：断连后指数退避重连（1s, 2s, 4s, max 30s）
   - 当收到 `event: complete` 时关闭连接
   - 提供 `fallbackToPolling` 选项：如果 SSE 连接失败 3 次，自动降级回 polling
   - 返回值与现有 `useReviewRun` 兼容：`{ run, progress, error, isConnected }`

2. 修改 `frontend/src/components/RunProgressCard.jsx`：
   - 优先使用 `useReviewRunSSE` hook
   - 在 UI 上添加一个小的连接状态指示器（如绿点表示 SSE 连接中，灰点表示 polling 模式）
   - 保持现有 stepper UI 不变，只替换数据源

3. 修改 `frontend/src/pages/RunDetailsPage.jsx`：
   - 将 progress 数据源切换为 SSE hook
   - 确保页面卸载时（useEffect cleanup）正确关闭 SSE 连接

验收标准：
- 启动一次 review 后，RunDetailsPage 上的进度条实时更新，不再有 polling 间隔
- 手动断网再恢复后，SSE 自动重连
- 浏览器 DevTools Network 面板中看到 EventStream 类型的持久连接而非重复 XHR
- 旧浏览器或 SSE 失败时自动回退 polling
```

---

## Phase 3: Notion Connector 实现

### 目标

将现有的 Notion connector stub 升级为可实际获取 Notion 页面内容的完整实现，复用已有的 auth / error / schema 基础设施。

### 前置条件

- 已创建 Notion Integration 并获得 Token
- 目标 Notion 页面已分享给该 Integration

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase3-notion-connector

git add requirement_review_v1/connectors/notion.py
git commit -m "feat: implement live Notion page fetching via Notion API"

git add tests/test_notion_connector.py
git commit -m "test: add integration tests for Notion connector live fetch"

git add .env.example README.md
git commit -m "docs: add Notion connector setup instructions"

git push -u origin feature/phase3-notion-connector

gh pr create --title "feat: implement Notion connector live fetching" --body "## Summary
- Implement get_content() in NotionConnector using Notion API
- Convert Notion blocks to Markdown text
- Add proper error handling for API failures

## Test plan
- [ ] Fetch a public Notion page returns SourceDocument with content
- [ ] Missing token raises NotionAuthenticationError
- [ ] Invalid page ID raises appropriate error
- [ ] Block types (paragraph, heading, list, code, toggle) correctly converted
"
```

### 提示词

```text
将 `requirement_review_v1/connectors/notion.py` 从 stub 升级为完整实现：

1. 添加依赖：在 pyproject.toml 的 dependencies 中添加 `httpx>=0.27.0`（用于异步 HTTP 请求）

2. 在 `NotionConnector` 中实现 `get_content()` 方法：
   - 调用 Notion API `GET /v1/pages/{page_id}` 获取页面元数据（标题、创建时间等）
   - 调用 Notion API `GET /v1/blocks/{page_id}/children?page_size=100` 递归获取所有 blocks
   - 处理分页：如果 `has_more=true`，使用 `start_cursor` 继续获取
   - 使用 httpx 同步客户端（因为 BaseConnector.get_content 是同步接口）
   - 请求头设置：Authorization: Bearer {token}, Notion-Version: {api_version}

3. 实现 `_blocks_to_markdown()` 私有方法，将 Notion block 数组转为 Markdown 文本：
   - `paragraph` → 纯文本 + 换行
   - `heading_1/2/3` → `#/##/###` + 文本
   - `bulleted_list_item` → `- ` + 文本
   - `numbered_list_item` → `1. ` + 文本
   - `code` → 三反引号代码块，带语言标记
   - `toggle` → `<details><summary>` 标记
   - `to_do` → `- [ ]` 或 `- [x]`
   - `quote` → `> ` 引用
   - `divider` → `---`
   - `image` → `![image](url)`
   - `table` → Markdown 表格
   - 递归处理 `has_children=true` 的 blocks（嵌套列表等）
   - 不认识的 block type 跳过并在末尾添加注释

4. 实现 `_extract_rich_text()` 辅助方法：
   - 将 Notion rich_text 数组转为纯文本
   - 处理 bold → `**text**`, italic → `*text*`, code → `\`text\``, link → `[text](url)`

5. 错误处理：
   - HTTP 401 → 抛出 `NotionAuthenticationError`
   - HTTP 403 → 抛出 `NotionPermissionDeniedError`
   - HTTP 404 → 抛出新的 `NotionPageNotFoundError(ConnectorNotFoundError)`
   - HTTP 429 → 抛出 `ConnectorRateLimitError` 并包含 retry-after
   - 网络错误 → 抛出 `ConnectorNetworkError`

6. 返回值：构造 `SourceDocument`，包含：
   - `content`: Markdown 格式的页面内容
   - `source_type`: "notion"
   - `metadata`: 包含 page_id, title, created_time, last_edited_time, url

7. 更新 `.env.example`，添加：
   ```
   MARRDP_NOTION_TOKEN=
   MARRDP_NOTION_API_BASE_URL=https://api.notion.com/v1
   MARRDP_NOTION_API_VERSION=2022-06-28
   ```

8. 更新 `tests/test_notion_connector.py`：
   - 保留现有 stub 测试（改为测试基本解析逻辑）
   - 添加 mock httpx 响应的单元测试：正常获取、401、403、404、429 场景
   - 添加 _blocks_to_markdown 的独立测试：覆盖所有 block 类型

9. 移除 `NotionNotReadyError` 异常类（不再需要 stub 异常）

验收标准：
- 设置 MARRDP_NOTION_TOKEN 后，传入一个 Notion 页面 URL 可以成功获取 Markdown 内容
- 所有新增单元测试通过
- 现有 test_notion_connector.py 中的兼容性测试仍然通过
- README 的 Source Support 部分更新为"Notion 已支持"
```

---

## Phase 4: 前端测试框架搭建

### 目标

当前前端 `package.json` 中没有任何测试脚本或测试框架。本阶段搭建 Vitest + React Testing Library 测试基础设施，并为核心组件编写测试。

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase4-frontend-testing

# 测试基础设施
git add frontend/package.json frontend/vitest.config.js frontend/src/test/setup.js
git commit -m "chore: add Vitest + React Testing Library test infrastructure"

# 核心组件测试
git add frontend/src/components/__tests__/
git commit -m "test: add unit tests for core frontend components"

# Hook 测试
git add frontend/src/hooks/__tests__/
git commit -m "test: add hook tests for useReviewRun and useReviewHistory"

# CI 集成
git add .github/workflows/build.yml
git commit -m "ci: add frontend test step to build workflow"

git push -u origin feature/phase4-frontend-testing

gh pr create --title "feat: frontend testing infrastructure with Vitest" --body "## Summary
- Add Vitest + React Testing Library + jsdom
- Add component tests for core panels
- Add hook tests with mock API
- Integrate into CI pipeline

## Test plan
- [ ] npm test runs all tests
- [ ] All component render tests pass
- [ ] Hook tests cover loading/error/success states
- [ ] CI workflow includes frontend test step
"
```

### 提示词 — Step 1: 测试基础设施

```text
为前端项目搭建 Vitest 测试框架：

1. 在 `frontend/` 目录下安装开发依赖：
   ```bash
   cd frontend
   npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
   ```

2. 创建 `frontend/vitest.config.js`：
   ```js
   import { defineConfig } from 'vitest/config';
   import react from '@vitejs/plugin-react';

   export default defineConfig({
     plugins: [react()],
     test: {
       environment: 'jsdom',
       globals: true,
       setupFiles: './src/test/setup.js',
       css: true,
     },
   });
   ```

3. 创建 `frontend/src/test/setup.js`：
   - 导入 `@testing-library/jest-dom`
   - Mock `window.matchMedia`（用于 useTheme 等）
   - Mock `window.fetch`（默认返回空响应，测试中可覆盖）

4. 修改 `frontend/package.json`，添加 scripts：
   ```json
   "test": "vitest run",
   "test:watch": "vitest",
   "test:coverage": "vitest run --coverage"
   ```

5. 创建 `frontend/src/test/utils.jsx`：
   - 封装 `renderWithProviders(component)` 工具函数
   - 包裹 `BrowserRouter` + `ToastProvider` 等必要的 context providers
   - 导出 `@testing-library/react` 的常用方法（screen, waitFor, fireEvent 等）

验收标准：
- `cd frontend && npm test` 能正常启动 vitest 并以 0 退出（即使还没有测试文件）
- vitest.config.js 与现有 vite.config.js 不冲突
```

### 提示词 — Step 2: 核心组件测试

```text
为前端核心组件编写单元测试：

1. 创建 `frontend/src/components/__tests__/ReviewSubmitPanel.test.jsx`：
   - 测试：渲染三种输入模式（prd_text, prd_path, source）的切换
   - 测试：提交按钮在输入为空时 disabled
   - 测试：填写内容后点击提交，调用 API 并显示 loading 状态
   - 测试：提交成功后重置表单
   - 测试：提交失败时显示错误 toast

2. 创建 `frontend/src/components/__tests__/ReviewHistoryPanel.test.jsx`：
   - 测试：loading 状态显示骨架屏或 spinner
   - 测试：空列表显示"暂无记录"占位符
   - 测试：正常列表渲染 run_id、状态、时间
   - 测试：搜索过滤功能
   - 测试：分页按钮的 disabled 状态

3. 创建 `frontend/src/components/__tests__/FindingsPanel.test.jsx`：
   - 测试：无 findings 时显示空状态
   - 测试：正常渲染 findings 列表
   - 测试：severity 标签的颜色映射

4. 创建 `frontend/src/components/__tests__/RunProgressCard.test.jsx`：
   - 测试：各步骤状态（pending, running, done, error）正确渲染
   - 测试：当前活跃步骤高亮显示
   - 测试：全部完成时显示成功状态

5. 创建 `frontend/src/components/__tests__/ErrorBoundary.test.jsx`：
   - 测试：子组件正常渲染时不显示错误 UI
   - 测试：子组件抛出错误时显示 fallback UI
   - 测试：错误信息正确显示

6. 创建 `frontend/src/hooks/__tests__/useReviewHistory.test.js`：
   - Mock fetch API
   - 测试：初始状态为 loading
   - 测试：成功获取数据后更新 runs 列表
   - 测试：fetch 失败时 error 状态

每个测试文件内使用 describe/it 结构，mock 外部依赖（fetch, router），
确保测试相互独立不依赖执行顺序。

验收标准：
- `npm test` 所有测试通过
- 核心交互路径有覆盖（提交、列表展示、错误处理）
```

---

## Phase 5: 结构化日志与可观测性增强

### 目标

当前日志仅有 `main.py` 中的 `logging.basicConfig`，agent 内部几乎无日志。引入结构化日志，添加 run_id 关联，为生产环境排查问题做准备。

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase5-structured-logging

git add requirement_review_v1/utils/logging.py
git commit -m "feat: add structured logging module with run_id correlation"

git add requirement_review_v1/agents/*.py requirement_review_v1/workflow.py
git commit -m "feat: integrate structured logging into agents and workflow"

git add requirement_review_v1/server/app.py
git commit -m "feat: add request logging middleware with trace ID"

git add tests/test_structured_logging.py
git commit -m "test: add structured logging tests"

git push -u origin feature/phase5-structured-logging

gh pr create --title "feat: structured logging with run_id correlation" --body "## Summary
- Add structured logging utility with JSON formatter
- Add run_id correlation across agents
- Add HTTP request logging middleware
- Configurable log level via environment variable

## Test plan
- [ ] Logs output in JSON format when LOG_FORMAT=json
- [ ] run_id appears in all agent log entries during a review
- [ ] HTTP request/response logged with trace ID
- [ ] Log level configurable via LOG_LEVEL env var
"
```

### 提示词

```text
为项目建立结构化日志体系：

1. 创建 `requirement_review_v1/utils/logging.py`：
   - 实现 `StructuredFormatter(logging.Formatter)` 类：
     - JSON 格式输出，包含字段：timestamp, level, logger, message, run_id, node, duration_ms
     - 支持 extra 字段透传
   - 实现 `HumanReadableFormatter(logging.Formatter)` 类：
     - 格式：`[2026-03-24T10:00:00Z] INFO  [parser] (run_abc123) Parsed 12 requirements in 2.3s`
   - 实现 `setup_logging(log_level, log_format)` 函数：
     - `log_format` 支持 "json" 和 "human"，从环境变量 `LOG_FORMAT` 读取，默认 "human"
     - `log_level` 从环境变量 `LOG_LEVEL` 读取，默认 "INFO"
     - 配置 root logger 和 `requirement_review_v1` logger
     - 抑制第三方库的 verbose 日志（httpx, httpcore, litellm 等设为 WARNING）
   - 实现 `get_logger(name)` 工具函数，返回带命名空间的 logger
   - 实现 `RunLogContext` context manager：
     - 进入时将 run_id 注入到 logging 的 context（使用 contextvars）
     - 自动附加到后续所有日志记录的 extra 中

2. 修改 `main.py`：
   - 将 `logging.basicConfig(...)` 替换为 `setup_logging()`
   - 保留 logs/app.log 文件输出

3. 在各 agent 中添加关键日志点：
   - `parser_agent.py`：日志记录 "开始解析" 和 "解析完成, N 条需求"
   - `planner_agent.py`：日志记录 "开始规划" 和 "规划完成, N 个任务, N 个里程碑"
   - `risk_agent.py`：日志记录 "风险分析开始" 和 "发现 N 个风险项"
   - `reviewer_agent.py`：日志记录 "review 模式: X" 和 "review 完成, N 条 findings"
   - `reporter_agent.py`：日志记录 "报告生成完成"

4. 在 `workflow.py` 的 `_build_async_node` / `_build_sync_node` 中：
   - 节点开始时 log.info("node started", extra={"node": node_name})
   - 节点结束时 log.info("node completed", extra={"node": node_name, "duration_ms": ...})
   - 节点异常时 log.error("node failed", extra={"node": node_name}, exc_info=True)

5. 在 `requirement_review_v1/server/app.py` 添加请求日志中间件：
   - 使用 `@app.middleware("http")` 或 Starlette Middleware
   - 记录：method, path, status_code, duration_ms, client_ip
   - 生成 request trace_id 并通过 response header `X-Trace-ID` 返回
   - 排除 `/health` 和静态文件路径

6. 更新 `.env.example`：
   ```
   LOG_LEVEL=INFO
   LOG_FORMAT=human
   ```

验收标准：
- 启动后端后日志格式清晰可读
- 设置 LOG_FORMAT=json 后输出 JSON 行日志（便于 ELK/Loki 采集）
- 执行一次 review，日志中所有 agent 条目都带有相同的 run_id
- API 请求日志包含 trace_id
```

---

## Phase 6: Review 结果对比与趋势分析

### 目标

支持同一 PRD 的多次 review 结果对比，以及跨 run 的趋势分析仪表盘，让用户看到需求文档质量的演进。

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase6-review-comparison

# 后端对比 API
git add requirement_review_v1/service/comparison_service.py requirement_review_v1/server/app.py
git commit -m "feat: add review comparison and trend analysis API endpoints"

# 前端对比页面
git add frontend/src/pages/ComparisonPage.jsx frontend/src/components/ComparisonPanel.jsx frontend/src/components/TrendChart.jsx
git commit -m "feat: add review comparison UI with diff view and trend charts"

git add tests/test_comparison_service.py
git commit -m "test: add comparison service tests"

git push -u origin feature/phase6-review-comparison

gh pr create --title "feat: review result comparison and trend analysis" --body "## Summary
- Add comparison API for two review runs
- Add trend analysis API across all runs
- Add comparison page with diff view
- Add simple trend chart using inline SVG

## Test plan
- [ ] GET /api/compare?run_a=X&run_b=Y returns structured diff
- [ ] GET /api/trends returns aggregated metrics
- [ ] Comparison page shows added/removed/changed findings
- [ ] Trend chart renders correctly with sample data
"
```

### 提示词 — Step 1: 后端对比服务

```text
实现 review 结果对比和趋势分析后端服务：

1. 创建 `requirement_review_v1/service/comparison_service.py`：

   实现 `compare_runs(run_id_a: str, run_id_b: str, outputs_root: str = "outputs") -> ComparisonResult`：
   - 读取两个 run 的 report.json
   - 对比维度：
     a. findings 对比：按 requirement_id 匹配，标记 added / removed / changed / unchanged
     b. risk 对比：按 risk id 或 description 模糊匹配
     c. metrics 对比：coverage, risk_score, finding_count 的数值变化（+/- delta）
     d. open_questions 对比：新增的问题 / 已解决的问题
   - 返回结构化的 `ComparisonResult` Pydantic model

   实现 `get_trend_data(outputs_root: str = "outputs", limit: int = 20) -> TrendData`：
   - 扫描最近 N 个 run 目录（按时间倒序）
   - 从每个 run 的 report.json 提取：run_id, timestamp, total_findings, high_severity_count, risk_score, coverage_pct
   - 返回时间序列数据

   实现 `get_run_stats_summary(outputs_root: str = "outputs") -> StatsSummary`：
   - 总 run 数、平均 findings 数、最常见问题类型 top-5
   - 平均 review 耗时

2. 修改 `requirement_review_v1/server/app.py`，添加路由：
   - `GET /api/compare?run_a={id}&run_b={id}` → 两次 review 对比
   - `GET /api/trends?limit=20` → 趋势数据
   - `GET /api/stats` → 汇总统计

3. 添加测试 `tests/test_comparison_service.py`：
   - Mock 两个 run 目录和 report.json
   - 测试 findings diff 正确识别 added/removed/changed
   - 测试 trend data 按时间排序
   - 测试空目录、单个 run 的边界情况

验收标准：
- 两个已完成的 run 调用 compare API 返回结构化 diff
- trends API 返回时间序列数组
- 所有测试通过
```

### 提示词 — Step 2: 前端对比页面

```text
实现前端的 review 对比和趋势页面：

1. 修改 `frontend/src/App.jsx`：
   - 添加路由 `/compare` → `ComparisonPage`
   - 添加路由 `/trends` → `TrendsPage`
   - 在 Navbar 中添加"对比"和"趋势"导航链接

2. 创建 `frontend/src/pages/ComparisonPage.jsx`：
   - 顶部：两个 run 选择器（下拉框，数据来自 /api/runs）
   - 选择两个 run 后点击"对比"按钮，请求 /api/compare
   - 结果展示：
     a. 概要卡片：显示两个 run 的核心指标对比（findings 数, risk score, coverage）
        用绿色/红色箭头表示改善/恶化
     b. Findings Diff 表格：
        - 绿色行 = removed（问题已修复）
        - 红色行 = added（新问题）
        - 黄色行 = changed（描述变化）
        - 白色行 = unchanged
     c. Risk 对比列表：左右对照

3. 创建 `frontend/src/pages/TrendsPage.jsx`：
   - 请求 /api/trends 获取数据
   - 使用纯 CSS + inline SVG 实现简单折线图（不引入图表库）：
     a. X 轴：时间（run 日期）
     b. Y 轴左：findings 总数
     c. Y 轴右：coverage 百分比
   - 下方显示统计卡片：总 run 数、平均 findings、最常见问题类型
   - 如果数据不足（< 2 个 run），显示提示信息

4. 创建 `frontend/src/components/MetricDelta.jsx`：
   - 可复用组件：显示一个指标的旧值 → 新值 + 变化百分比
   - 正向变化（如 coverage 增加）绿色，负向变化红色

验收标准：
- 对比页面选择两个 run 后显示完整的 diff 视图
- 趋势页面折线图正确渲染
- 无外部图表库依赖
- 响应式布局在手机宽度下仍可用
```

---

## Phase 7: 用户认证与权限管理

### 目标

从全局 API Key 认证升级为支持用户注册/登录的 JWT 认证体系，Review run 归属到具体用户，前端添加登录页面。

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase7-user-auth

# 用户模型与存储
git add requirement_review_v1/auth/
git commit -m "feat: add user model, JWT auth, and password hashing"

# API 中间件改造
git add requirement_review_v1/server/app.py requirement_review_v1/server/auth_middleware.py
git commit -m "feat: integrate JWT auth middleware with backward compatibility"

# run 归属
git add requirement_review_v1/service/review_service.py
git commit -m "feat: associate review runs with authenticated user"

# 前端登录
git add frontend/src/pages/LoginPage.jsx frontend/src/hooks/useAuth.js frontend/src/api.js
git commit -m "feat: add login page and auth context to frontend"

git add tests/test_auth.py tests/test_server_app_auth.py
git commit -m "test: add auth module and protected route tests"

git push -u origin feature/phase7-user-auth

gh pr create --title "feat: JWT user authentication and authorization" --body "## Summary
- Add user model with SQLite storage
- JWT access/refresh token auth flow
- Role-based access (viewer/reviewer/admin)
- Login/register frontend pages
- Backward compatible: existing API key auth still works

## Test plan
- [ ] Register → login → get token → access protected route
- [ ] Expired token returns 401
- [ ] Admin can see all runs, viewer only sees own
- [ ] API key auth still works when MARRDP_API_AUTH_DISABLED=false
"
```

### 提示词 — Step 1: 后端认证模块

```text
实现基于 JWT 的用户认证系统：

1. 在 pyproject.toml 添加依赖：
   - `pyjwt>=2.8.0`
   - `bcrypt>=4.1.0`
   - `aiosqlite>=0.20.0`（轻量级异步 SQLite）

2. 创建 `requirement_review_v1/auth/` 包：

   `requirement_review_v1/auth/models.py`：
   - `User` Pydantic model：id, username, email, hashed_password, role (viewer|reviewer|admin), created_at, is_active
   - `TokenPair` model：access_token, refresh_token, token_type, expires_in
   - `UserCreate` model：username, email, password（带验证规则）
   - `UserPublic` model：不含 hashed_password 的对外视图

   `requirement_review_v1/auth/store.py`：
   - `UserStore` 类，使用 SQLite 文件存储（默认路径 `data/users.db`）
   - 方法：create_user, get_user_by_username, get_user_by_id, list_users, update_user
   - 建表 SQL 在首次访问时自动执行
   - 密码使用 bcrypt 哈希存储

   `requirement_review_v1/auth/jwt_utils.py`：
   - `create_access_token(user_id, role, expires_minutes=30) -> str`
   - `create_refresh_token(user_id, expires_days=7) -> str`
   - `decode_token(token) -> dict` 解码并验证 token
   - Secret key 从环境变量 `MARRDP_JWT_SECRET` 读取
   - 如果未设置，启动时自动生成随机 secret 并警告

   `requirement_review_v1/auth/service.py`：
   - `register(user_create) -> UserPublic`：检查重名，创建用户
   - `login(username, password) -> TokenPair`：验证密码，签发 token
   - `refresh(refresh_token) -> TokenPair`：刷新 access token
   - `get_current_user(token) -> User`：从 token 解析用户

3. 创建 `requirement_review_v1/server/auth_middleware.py`：
   - 实现 `get_current_user_optional` 依赖：
     - 从 `Authorization: Bearer xxx` header 解析 JWT
     - 也兼容现有的 `X-API-Key` 方式（返回一个虚拟 admin 用户）
     - 如果 `MARRDP_API_AUTH_DISABLED=true`，返回匿名用户
   - 实现 `require_role(role)` 依赖工厂：
     - 返回一个依赖函数，校验当前用户角色是否满足要求

4. 修改 `requirement_review_v1/server/app.py`：
   - 添加路由：
     - `POST /api/auth/register`
     - `POST /api/auth/login`
     - `POST /api/auth/refresh`
     - `GET /api/auth/me`
   - `POST /api/review` 注入当前用户信息，将 user_id 存入 run 元数据
   - `GET /api/runs` 非 admin 用户只能看到自己的 run
   - 保持向后兼容：`MARRDP_API_AUTH_DISABLED=true` 时行为与之前完全一致

5. 更新 `.env.example`：
   ```
   MARRDP_JWT_SECRET=
   MARRDP_JWT_ACCESS_EXPIRES_MINUTES=30
   MARRDP_JWT_REFRESH_EXPIRES_DAYS=7
   ```

验收标准：
- POST /api/auth/register 创建用户并返回用户信息（不含密码）
- POST /api/auth/login 返回 JWT token pair
- 带 token 访问 /api/review 成功，不带 token 返回 401
- MARRDP_API_AUTH_DISABLED=true 时所有旧行为不变
```

### 提示词 — Step 2: 前端登录

```text
为前端添加用户认证 UI：

1. 创建 `frontend/src/hooks/useAuth.js`：
   - 使用 React Context 管理认证状态
   - 存储到 localStorage：access_token, refresh_token, user 信息
   - 提供方法：login, register, logout, refreshToken
   - 在 App 初始化时检查 localStorage 中的 token，如有效则恢复登录状态
   - access_token 过期前 5 分钟自动 refresh

2. 修改 `frontend/src/api.js`：
   - `requestJson` 自动附加 `Authorization: Bearer {token}` header
   - 收到 401 响应时自动尝试 refresh token
   - Refresh 也失败时跳转到登录页

3. 创建 `frontend/src/pages/LoginPage.jsx`：
   - 表单包含：用户名、密码输入框、登录按钮
   - 下方有"没有账号？注册"链接
   - 登录成功后跳转到首页
   - 错误信息显示在表单下方

4. 创建 `frontend/src/pages/RegisterPage.jsx`：
   - 表单：用户名、邮箱、密码、确认密码
   - 前端校验：密码长度 >= 8，两次密码一致
   - 注册成功后自动登录并跳转首页

5. 修改 `frontend/src/App.jsx`：
   - 用 `AuthProvider` 包裹整个应用
   - 添加路由 `/login` 和 `/register`
   - 实现路由守卫：未登录时重定向到 `/login`（除 login/register 外）
   - 如果后端 MARRDP_API_AUTH_DISABLED=true（首次请求不需要 auth），
     则跳过登录守卫（通过尝试一次无 token 请求判断）

6. 修改 `frontend/src/components/Navbar.jsx`：
   - 已登录：显示用户名 + 下拉菜单（包含"退出登录"）
   - 未登录：显示"登录"链接

验收标准：
- 注册 → 登录 → 看到首页 → 提交 review → 查看结果 全流程正常
- 退出登录后访问首页被重定向到登录页
- Token 过期后自动刷新不中断用户操作
- 关闭浏览器重新打开仍保持登录状态
```

---

## Phase 8: 自定义 Reviewer 角色与增量 Review

### 目标

允许用户定义自定义 reviewer 角色（超出默认的 product/engineering/QA/security），并支持增量 review（仅评审变更部分）。

### Git 工作流

```bash
git checkout main
git pull origin main
git checkout -b feature/phase8-custom-reviewers-incremental

# 自定义 reviewer
git add requirement_review_v1/review/custom_reviewer.py requirement_review_v1/review/reviewer_registry.py
git commit -m "feat: add custom reviewer role support with configurable checklist"

# 增量 review
git add requirement_review_v1/service/incremental_review.py
git commit -m "feat: add incremental review support for PRD changes"

# API 适配
git add requirement_review_v1/server/app.py
git commit -m "feat: add custom reviewer and incremental review API endpoints"

# 前端适配
git add frontend/src/components/CustomReviewerConfig.jsx frontend/src/components/ReviewSubmitPanel.jsx
git commit -m "feat: add custom reviewer configuration UI"

git add tests/test_custom_reviewer.py tests/test_incremental_review.py
git commit -m "test: add custom reviewer and incremental review tests"

git push -u origin feature/phase8-custom-reviewers-incremental

gh pr create --title "feat: custom reviewer roles and incremental review" --body "## Summary
- Pluggable reviewer system with custom roles and checklists
- Incremental review for changed sections only
- Reviewer configuration UI in submit panel

## Test plan
- [ ] Custom reviewer registered and invoked during review
- [ ] Incremental review correctly identifies changed sections
- [ ] Unchanged findings carried over from previous run
- [ ] Frontend reviewer config saved and applied
"
```

### 提示词 — Step 1: 自定义 Reviewer 角色

```text
实现可插拔的自定义 reviewer 角色系统：

1. 创建 `requirement_review_v1/review/reviewer_registry.py`：
   - 实现 `ReviewerRegistry` 单例类：
     - `_builtin_reviewers`: 注册默认的 product, engineering, qa, security reviewer
     - `_custom_reviewers`: dict[str, ReviewerConfig] 存储自定义 reviewer
     - `register(name, config: ReviewerConfig)`: 注册自定义 reviewer
     - `unregister(name)`: 移除自定义 reviewer（不允许移除 builtin）
     - `get_active_reviewers(requested: list[str] | None) -> list[ReviewerConfig]`: 返回要使用的 reviewer 列表
     - `list_all() -> list[dict]`: 列出所有可用 reviewer（含 builtin 和 custom）
   - `ReviewerConfig` dataclass：
     - name: str
     - display_name: str
     - description: str
     - system_prompt: str（reviewer 的系统提示词）
     - checklist: list[str]（该角色关注的检查项）
     - severity_weight: float（该 reviewer findings 的权重，0.0-1.0）
     - is_builtin: bool

2. 创建 `requirement_review_v1/review/custom_reviewer.py`：
   - 实现 `run_custom_review(config: ReviewerConfig, parsed_items, plan, requirement_doc) -> ReviewerResult`：
     - 构建 prompt：将 config.system_prompt + config.checklist 组合成完整提示
     - 调用 LLM structured output（复用 SMART_LLM 配置）
     - 返回格式与 product_reviewer 等一致的 ReviewerResult

3. 修改 `requirement_review_v1/review/parallel_review_manager.py`：
   - `select_reviewers()` 现在从 `ReviewerRegistry.get_active_reviewers()` 获取 reviewer 列表
   - 自定义 reviewer 通过 `run_custom_review` 执行
   - 内置 reviewer 仍用原有的 `review_product` 等函数

4. 修改 `requirement_review_v1/server/app.py`：
   - `POST /api/reviewers` → 注册自定义 reviewer
     body: { name, display_name, description, system_prompt, checklist, severity_weight }
   - `GET /api/reviewers` → 列出所有 reviewer
   - `DELETE /api/reviewers/{name}` → 移除自定义 reviewer
   - `POST /api/review` 新增可选字段 `reviewers: list[str]` 指定本次 review 使用哪些 reviewer

5. 自定义 reviewer 配置持久化：
   - 存储为 `data/custom_reviewers.json`
   - 启动时自动加载

6. 提供几个预置的自定义 reviewer 模板（不自动启用，仅供参考）：
   - `performance_reviewer`：关注性能相关需求（响应时间、并发、资源消耗）
   - `accessibility_reviewer`：关注无障碍访问（WCAG 标准）
   - `ux_reviewer`：关注用户体验一致性

验收标准：
- 注册一个 "performance_reviewer" 后，review 结果中出现该 reviewer 的 findings
- 不指定 reviewer 时使用默认的 4 个内置 reviewer
- 指定 reviewers=["product", "performance_reviewer"] 时只运行这两个
- GET /api/reviewers 返回内置 + 自定义 reviewer 列表
```

### 提示词 — Step 2: 增量 Review

```text
实现增量 review 功能，当 PRD 小幅修改时只 review 变更部分：

1. 创建 `requirement_review_v1/service/incremental_review.py`：

   实现 `compute_prd_diff(old_doc: str, new_doc: str) -> PRDDiff`：
   - 使用 Python 标准库 `difflib.SequenceMatcher` 比较两个文档
   - 将文档按段落（双换行分割）切分，计算段落级别的 diff
   - 返回 `PRDDiff`：
     - added_sections: list[str]（新增的段落）
     - removed_sections: list[str]（删除的段落）
     - changed_sections: list[tuple[str, str]]（修改的段落，(旧, 新)）
     - unchanged_sections: list[str]（未改动的段落）
     - change_ratio: float（变更比例 0.0-1.0）

   实现 `run_incremental_review(new_doc, previous_run_id, outputs_root) -> ReviewState`：
   - 读取 previous_run_id 的 report.json 获取上次 review 结果
   - 计算 PRD diff
   - 如果 change_ratio < 0.1（变更 < 10%），进入增量模式：
     a. 只将 added_sections + changed_sections 发送给 reviewer
     b. 上次 unchanged_sections 对应的 findings 直接沿用
     c. removed_sections 对应的 findings 标记为 resolved
     d. 合并新 findings 和沿用的 findings
   - 如果 change_ratio >= 0.1，走完整 review 流程（避免增量偏差累积）
   - 在 trace 中记录 incremental_review 元数据：change_ratio, reused_findings_count, new_findings_count

2. 修改 `requirement_review_v1/server/app.py`：
   - `POST /api/review` 新增可选字段 `previous_run_id: str`
   - 当提供 previous_run_id 时，调用 incremental review 逻辑
   - response 中添加字段 `incremental: bool` 和 `change_ratio: float`

3. 修改 `requirement_review_v1/service/review_service.py`：
   - 在 `review_prd_text_async` 中检查 previous_run_id 参数
   - 有 previous_run_id 且找到历史 run 时走增量路径
   - 增量 review 仍然生成完整的 report（包含沿用的 + 新的 findings）
   - report.json 中额外写入 `incremental_metadata` 字段

4. 前端适配：
   - 修改 `ReviewSubmitPanel.jsx`：
     - 新增"基于上次 review"下拉框，可选择一个已完成的 run 作为基准
     - 选择后自动填入 previous_run_id
   - 修改 `RunDetailsPage.jsx`：
     - 增量 review 的 findings 旁添加标记：[沿用] / [新发现] / [已解决]

5. 添加测试：
   - 测试 compute_prd_diff 的各种场景（纯新增、纯删除、混合变更）
   - 测试增量 review 正确沿用未变更 findings
   - 测试 change_ratio 超过阈值时回退全量 review

验收标准：
- 修改 PRD 一小段后提交增量 review，耗时明显低于全量 review
- 增量 review 报告中沿用的 findings 正确标记来源
- 变更超过 10% 自动切换全量 review 并在 trace 中说明原因
```

---

## 附录 A: 补充优化项（可穿插在任何 Phase 后执行）

### A1. pytest conftest 共享 fixtures

```text
Git 分支: chore/shared-test-fixtures

在 tests/ 目录下创建 conftest.py，提取公共测试 fixtures：

1. 创建 `tests/conftest.py`：
   - `sample_prd_text` fixture：返回一段标准的测试用 PRD 文本（约 200 字）
   - `sample_parsed_items` fixture：返回 3 个 ParsedItemState
   - `temp_run_dir` fixture：创建临时目录并在测试结束后清理（使用 tmp_path）
   - `mock_llm_response` fixture：返回一个可配置的 LLM mock 函数
   - `sample_review_state` fixture：返回包含基本数据的 ReviewState
   - `sample_report_json` fixture：返回标准 report.json 内容

2. 扫描现有 57 个测试文件，找出重复定义的 mock 数据和 setup 逻辑，
   将高频重复（出现 >= 3 次）的部分迁移到 conftest.py。

3. 确保所有现有测试仍然通过（`pytest -q`）。

验收标准：
- conftest.py 包含至少 5 个共享 fixture
- 至少 10 个测试文件引用了共享 fixture（减少重复代码）
- 所有 57 个测试文件通过
```

### A2. CI 流水线完善

```text
Git 分支: chore/ci-enhancement

完善 .github/workflows/build.yml CI 配置：

1. 添加前端构建和测试 job（在 Phase 4 完成后）：
   ```yaml
   frontend:
     runs-on: ubuntu-latest
     defaults:
       run:
         working-directory: frontend
     steps:
       - uses: actions/checkout@v4
       - uses: actions/setup-node@v4
         with:
           node-version: '22'
           cache: 'npm'
           cache-dependency-path: frontend/package-lock.json
       - run: npm ci
       - run: npm test
       - run: npm run build
   ```

2. 添加后端 pytest + coverage：
   - 安装 pytest-cov
   - 运行 `pytest --cov=requirement_review_v1 --cov-report=xml`
   - 上传 coverage 到 Codecov 或作为 artifact

3. 添加代码质量检查：
   - ruff check（linting）
   - ruff format --check（formatting）

4. 添加 Docker 构建验证（不 push，只验证 build 成功）

验收标准：
- PR 触发 CI 包含：后端测试、前端测试、lint、Docker build
- 任一步骤失败则 PR 标记为红色
```

### A3. 报告导出格式增强

```text
Git 分支: feature/report-export-formats

增加 review 报告的导出格式：

1. 修改 `requirement_review_v1/server/app.py` 的 `GET /api/report/{run_id}`：
   - 现有支持：`format=md` 和 `format=json`
   - 新增 `format=html`：将 Markdown 报告转为带样式的 HTML
     - 使用 Python 标准库或 markdown 库转换
     - 嵌入一套简洁的 CSS 样式（适合打印）
     - 包含封面页（PRD 标题、review 时间、模式、reviewer 列表）
   - 新增 `format=csv`：将 findings 导出为 CSV 表格
     - 列：id, requirement, severity, category, description, suggestion, reviewer

2. 前端 ArtifactDownloadPanel 中添加格式选择下拉框

验收标准：
- /api/report/{run_id}?format=html 返回可在浏览器中直接打开的 HTML
- /api/report/{run_id}?format=csv 返回可在 Excel 中打开的 CSV
```

---

## 附录 B: 各 Phase 之间的依赖关系

```text
Phase 1 (Docker)          ← 独立，可随时开始
Phase 2 (SSE)             ← 独立，可随时开始
Phase 3 (Notion)          ← 独立，可随时开始
Phase 4 (前端测试)        ← 独立，可随时开始
Phase 5 (结构化日志)      ← 独立，推荐在 Phase 2 前完成
Phase 6 (对比与趋势)      ← 独立，可随时开始
Phase 7 (用户认证)        ← 推荐在 Phase 6 后，因为对比/趋势页面也需要权限控制
Phase 8 (自定义 Reviewer) ← 推荐在 Phase 6 后，与增量 review 需要对比服务的部分逻辑

推荐执行顺序: 1 → 5 → 2 → 3 → 4 → 6 → 7 → 8
可并行的组合: (1, 3, 4) 可以同时进行
```

---

## 附录 C: 版本演进建议

完成以上所有 Phase 后，建议版本号更新为 `0.7.0`（或 `1.0.0` 如果认为功能已达到首个稳定版标准）。

每个 Phase merge 后建议打 tag：

```text
v0.6.1 — Phase 1 (Docker)
v0.6.2 — Phase 2 (SSE)
v0.6.3 — Phase 3 (Notion)
v0.6.4 — Phase 4 (Frontend Tests)
v0.6.5 — Phase 5 (Logging)
v0.6.6 — Phase 6 (Comparison)
v0.6.7 — Phase 7 (Auth)
v0.7.0 — Phase 8 (Custom Reviewers + Incremental Review)
```
