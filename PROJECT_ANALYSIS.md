# GPT-Researcher 项目系统性分析

> 分析日期：2026-02-17

---

## 目录

- [1. 项目整体架构（模块划分）](#1-项目整体架构模块划分)
- [2. 核心运行流程（从入口到最终输出）](#2-核心运行流程从入口到最终输出)
- [3. 多 Agent 协作深度分析](#3-多-agent-协作深度分析)
- [4. 状态管理](#4-状态管理)
- [5. LLM 调用位置](#5-llm-调用位置)
- [6. 数据流流转](#6-数据流流转)
- [7. 项目可扩展点](#7-项目可扩展点)
- [8. 改造为"需求评审与交付计划系统"—— 完整方案](#8-改造为需求评审与交付计划系统-完整方案)
- [9. 模块风险等级分类（复杂度 / 耦合度 / 可重构性）](#9-模块风险等级分类复杂度--耦合度--可重构性)

---

## 1. 项目整体架构（模块划分）

### 1.1 顶层目录结构

```
gpt-researcher-main/
├── gpt_researcher/          # 核心研究引擎（Python 库）
│   ├── agent.py             # 主入口类 GPTResearcher
│   ├── skills/              # 技能模块（Researcher, Writer, Curator...）
│   ├── actions/             # 动作层（查询处理、报告生成、网页抓取...）
│   ├── config/              # 配置管理
│   ├── llm_provider/        # LLM 提供商抽象层（20+ 提供商）
│   ├── retrievers/          # 搜索引擎检索器（14 种）
│   ├── scraper/             # 网页抓取器（8 种）
│   ├── context/             # 上下文压缩与检索
│   ├── memory/              # Embedding 管理
│   ├── document/            # 文档加载与处理
│   ├── vector_store/        # 向量存储
│   ├── prompts.py           # 提示词模板体系
│   └── mcp/                 # Model Context Protocol 支持
│
├── multi_agents/            # 多 Agent 协作系统（LangGraph）
│   ├── agents/              # 8 个 Agent 实现
│   │   ├── orchestrator.py  # 总编辑（调度器）
│   │   ├── researcher.py    # 研究员
│   │   ├── editor.py        # 编辑（规划者）
│   │   ├── writer.py        # 写作者
│   │   ├── reviewer.py      # 审稿人
│   │   ├── reviser.py       # 修改者
│   │   ├── publisher.py     # 发布者
│   │   └── human.py         # 人工反馈节点
│   └── memory/              # 状态定义（ResearchState, DraftState）
│
├── backend/                 # 后端服务层
│   ├── server/              # FastAPI 服务（REST + WebSocket）
│   ├── report_type/         # 报告类型处理（Basic / Detailed / Deep）
│   ├── chat/                # 对话系统（带记忆）
│   └── utils.py             # 输出格式转换（PDF/DOCX/MD）
│
├── frontend/                # 前端（Static HTML + Next.js）
├── main.py                  # 服务启动入口
└── cli.py                   # CLI 命令行入口
```

### 1.2 gpt_researcher 核心模块详细结构

```
gpt_researcher/
├── __init__.py                 # 导出 GPTResearcher 类
├── agent.py                    # 主 GPTResearcher 类
├── prompts.py                  # 提示词模板体系
│
├── actions/                    # 核心动作模块
│   ├── agent_creator.py        # Agent 类型选择
│   ├── markdown_processing.py  # Markdown 处理
│   ├── query_processing.py     # 子查询生成、研究大纲规划
│   ├── report_generation.py    # 报告生成（引言、结论、正文）
│   ├── retriever.py            # 检索器工厂
│   ├── utils.py                # 流式输出、日志
│   └── web_scraping.py         # 网页抓取编排
│
├── config/                     # 配置管理
│   ├── config.py               # Config 类（加载配置文件、环境变量、默认值）
│   └── variables/
│       ├── base.py             # 基础变量定义
│       └── default.py          # 默认配置值
│
├── context/                    # 上下文管理
│   ├── compression.py          # 上下文压缩（Embedding 相似度过滤）
│   └── retriever.py            # 上下文检索
│
├── document/                   # 文档处理
│   ├── document.py             # 文档加载器
│   ├── azure_document_loader.py
│   ├── langchain_document.py
│   └── online_document.py
│
├── llm_provider/               # LLM 提供商抽象
│   ├── generic/
│   │   └── base.py             # GenericLLMProvider（统一接口）
│   └── image/
│       └── image_generator.py  # 图片生成
│
├── memory/                     # Embedding 管理
│   └── embeddings.py           # Memory 类（多 Embedding 提供商）
│
├── mcp/                        # Model Context Protocol
│   ├── client.py               # MCP 客户端
│   ├── research.py             # MCP 研究执行
│   ├── streaming.py            # MCP 流式处理
│   └── tool_selector.py        # MCP 工具选择
│
├── retrievers/                 # 搜索引擎检索器
│   ├── tavily/                 # Tavily（默认）
│   ├── google/                 # Google Custom Search
│   ├── bing/                   # Bing Search
│   ├── duckduckgo/             # DuckDuckGo
│   ├── serpapi/                # SerpAPI
│   ├── serper/                 # Serper
│   ├── searchapi/              # SearchAPI
│   ├── searx/                  # SearX（自托管）
│   ├── arxiv/                  # ArXiv（学术）
│   ├── semantic_scholar/       # Semantic Scholar（学术）
│   ├── pubmed_central/         # PubMed（医学）
│   ├── custom/                 # 自定义检索器
│   ├── mcp/                    # MCP 检索器
│   └── utils.py
│
├── scraper/                    # 网页抓取器
│   ├── scraper.py              # 主抓取器（路由分发）
│   ├── beautiful_soup/         # BeautifulSoup（HTML 解析）
│   ├── browser/                # 浏览器抓取（Headless）
│   ├── pymupdf/                # PyMuPDF（PDF 解析）
│   ├── arxiv/                  # ArXiv 专用
│   ├── firecrawl/              # FireCrawl API
│   ├── tavily_extract/         # Tavily Extract
│   └── web_base_loader/        # LangChain WebBaseLoader
│
├── skills/                     # 技能模块
│   ├── researcher.py           # ResearchConductor（研究执行）
│   ├── writer.py               # ReportGenerator（报告生成）
│   ├── context_manager.py      # ContextManager（上下文管理）
│   ├── curator.py              # SourceCurator（源排序）
│   ├── browser.py              # BrowserManager（浏览器管理）
│   ├── deep_research.py        # DeepResearchSkill（深度研究）
│   └── image_generator.py      # ImageGenerator（图片生成）
│
├── utils/                      # 工具模块
│   ├── costs.py                # 费用跟踪
│   ├── enum.py                 # 枚举定义
│   ├── llm.py                  # LLM 工具函数
│   ├── logger.py               # 日志
│   ├── logging_config.py       # 日志配置
│   ├── rate_limiter.py         # 速率限制
│   ├── tools.py                # 通用工具
│   ├── validators.py           # 校验器
│   └── workers.py              # 工作池
│
└── vector_store/               # 向量存储
    └── vector_store.py         # VectorStoreWrapper
```

### 1.3 后端服务结构

```
backend/
├── server/
│   ├── app.py                  # FastAPI 应用（REST + WebSocket 路由）
│   ├── websocket_manager.py    # WebSocket 管理和研究任务编排
│   ├── server_utils.py         # 服务工具函数
│   ├── report_store.py         # 报告持久化（JSON 文件）
│   └── logging_config.py       # 日志配置
│
├── report_type/
│   ├── basic_report/
│   │   └── basic_report.py     # 基础报告
│   ├── detailed_report/
│   │   └── detailed_report.py  # 详细报告（子主题并行）
│   └── deep_research/
│       └── main.py             # 深度研究
│
├── chat/
│   └── chat.py                 # ChatAgentWithMemory（带记忆对话）
│
├── memory/
│   ├── draft.py                # 草稿状态
│   └── research.py             # 研究状态
│
├── utils.py                    # 输出格式转换（PDF/DOCX/MD）
└── styles/
    └── pdf_styles.css          # PDF 样式
```

### 1.4 核心分层架构

| 层次 | 职责 | 关键技术 |
|------|------|---------|
| **表示层** | 前端 UI + API 接口 | Next.js / FastAPI / WebSocket |
| **调度层** | 单 Agent 或多 Agent 编排 | LangGraph StateGraph |
| **能力层** | 研究、写作、审稿、发布等技能 | GPTResearcher Skills |
| **基础设施层** | LLM、搜索、抓取、Embedding | LangChain / 各 Provider SDK |

---

## 2. 核心运行流程（从入口到最终输出）

### 2.1 入口方式

项目支持三种启动入口：

| 入口 | 文件 | 说明 |
|------|------|------|
| **Web 服务** | `main.py` | FastAPI 服务，端口 8000，支持 REST + WebSocket |
| **CLI** | `cli.py` | 命令行界面，直接执行研究任务 |
| **多 Agent** | `multi_agents/main.py` | LangGraph 多 Agent 入口 |

### 2.2 单 Agent 模式流程

```
用户请求（REST / WebSocket / CLI）
    │
    ▼
┌──────────────────────────────────────┐
│  GPTResearcher.__init__()            │
│  初始化组件：                          │
│  ├── ResearchConductor               │
│  ├── ReportGenerator                 │
│  ├── ContextManager                  │
│  ├── BrowserManager                  │
│  ├── SourceCurator                   │
│  ├── DeepResearchSkill               │
│  └── ImageGenerator                  │
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  GPTResearcher.conduct_research()    │
│                                      │
│  1. choose_agent()                   │ ← Smart LLM 选择 Agent 类型和角色
│  2. plan_research()                  │ ← Strategic LLM 生成子查询列表
│  3. 对每个子查询循环:                   │
│     ├─ get_retrievers() → 搜索       │ ← Tavily/Google/Bing...
│     ├─ scrape_urls() → 抓取内容       │ ← BS4/Browser/PyMuPDF...
│     ├─ compress_context()            │ ← Embedding 相似度过滤
│     └─ 累积到 self.context           │
│  4. curate_sources()（可选）           │ ← Smart LLM 排序源可信度
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  GPTResearcher.write_report()        │
│                                      │
│  1. generate_report()                │ ← Smart LLM 生成报告正文
│  2. add_references()                 │ ← 添加引用列表
│  3. table_of_contents()              │ ← 生成目录
│  4. 图片生成（可选）                    │ ← Gemini 生成配图
└──────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────┐
│  输出格式转换                          │
│  ├── write_md_to_pdf()   → PDF       │
│  ├── write_md_to_word()  → DOCX      │
│  └── write_text_to_md()  → Markdown  │
└──────────────────────────────────────┘
```

### 2.3 详细报告模式 (DetailedReport)

```
1. 初步研究 → 获取初始上下文
2. generate_subtopics() → LLM 生成子主题列表（Pydantic 结构化输出）
3. 对每个子主题 → 创建独立 GPTResearcher 实例并行研究
4. 汇总所有子主题报告 → 合成完整报告
```

### 2.4 深度研究模式 (DeepResearch)

```
1. generate_research_plan() → LLM 生成研究计划
2. 递归研究（可配置 breadth/depth）:
   ├── generate_search_queries() → 生成搜索查询
   ├── 并发执行搜索和抓取
   ├── process_research_results() → 提取发现和后续问题
   └── 递归进入下一层深度
3. 汇总所有层级发现 → 生成最终报告
```

### 2.5 API 端点列表

| 方法 | 路径 | 用途 |
|------|------|------|
| `GET` | `/` | 前端页面 |
| `GET` | `/api/reports` | 获取报告列表 |
| `GET` | `/api/reports/{id}` | 获取单个报告 |
| `POST` | `/api/reports` | 创建/更新报告 |
| `PUT` | `/api/reports/{id}` | 更新报告 |
| `DELETE` | `/api/reports/{id}` | 删除报告 |
| `GET` | `/api/reports/{id}/chat` | 获取报告聊天记录 |
| `POST` | `/api/reports/{id}/chat` | 添加聊天消息 |
| `POST` | `/api/chat` | 通用聊天（带报告上下文） |
| `POST` | `/report/` | 生成研究报告 |
| `POST` | `/api/multi_agents` | 执行多 Agent 研究 |
| `GET` | `/files/` | 列出上传文件 |
| `POST` | `/upload/` | 上传文档 |
| `DELETE` | `/files/{filename}` | 删除文件 |
| `WS` | `/ws` | WebSocket 实时推送 |

### 2.6 完整执行流程逐步追踪（以 WebSocket 触发 BasicReport 为例）

以下以最典型的路径 —— 用户通过前端 WebSocket 发起一次 `research_report` 类型的研究 —— 为例，逐步追踪从输入到输出的完整调用链。

#### Step 0：服务启动

```
main.py
  │  load_dotenv()                          ← 加载 .env 环境变量
  │  from backend.server.app import app     ← 导入 FastAPI 应用
  │  uvicorn.run(app, host="0.0.0.0", port=8000)
  │
  ▼
app.py
  │  app = FastAPI(lifespan=lifespan)
  │  manager = WebSocketManager()           ← 创建 WebSocket 管理器
  │  注册路由: /, /ws, /report/, /api/...
```

此时服务已就绪，等待客户端连接。

#### Step 1：用户输入（WebSocket 消息解析）

前端通过 WebSocket 发送消息，格式为：

```json
"start {\"task\":\"AI对教育的影响\",\"report_type\":\"research_report\",\"report_source\":\"web\",\"tone\":\"Objective\"}"
```

**调用链**（`app.py:348` → `server_utils.py:323`）：

```
websocket_endpoint()
  │  await manager.connect(websocket)       ← 建立连接
  │  await handle_websocket_communication(websocket, manager)
  │     │  data = await websocket.receive_text()   ← 接收 "start {...}"
  │     │  data.startswith("start") → True
  │     ▼
  │  handle_start_command(websocket, data, manager)
```

**`handle_start_command` 解析输入**（`server_utils.py:124-174`）：

```python
json_data = json.loads(data[6:])   # 去掉 "start " 前缀
task, report_type, source_urls, document_urls, tone, headers,
report_source, query_domains, mcp_enabled, mcp_strategy, mcp_configs = extract_command_data(json_data)

logs_handler = CustomLogsHandler(websocket, task)   # 创建日志处理器（写文件 + 推 WebSocket）

report = await manager.start_streaming(task, report_type, report_source, ...)
```

#### Step 2：路由到 `run_agent()`

**`start_streaming` → `run_agent`**（`websocket_manager.py:98-183`）：

```python
async def run_agent(task, report_type, report_source, ...):
    logs_handler = CustomLogsHandler(websocket, task)

    # 根据 report_type 分流
    if report_type == "multi_agents":
        report = await run_research_task(...)       # 多 Agent 路径
    elif report_type == "detailed_report":
        researcher = DetailedReport(...)             # 详细报告路径
        report = await researcher.run()
    else:
        researcher = BasicReport(...)                # ← 我们追踪这条路径
        report = await researcher.run()
```

三条路径对应三种报告类型：

| report_type | 处理类 | 说明 |
|-------------|--------|------|
| `"multi_agents"` | `ChiefEditorAgent` | LangGraph 多 Agent 协作 |
| `"detailed_report"` | `DetailedReport` | 子主题并行研究 |
| 其他（默认） | `BasicReport` | 单 Agent 研究 ← 本次追踪 |

#### Step 3：BasicReport 初始化

**`BasicReport.__init__`**（`basic_report.py:9-59`）：

```python
class BasicReport:
    def __init__(self, query, report_type, report_source, tone, websocket, ...):
        self.gpt_researcher = GPTResearcher(
            query=self.query,              # "AI对教育的影响"
            report_type=self.report_type,  # "research_report"
            report_source=self.report_source, # "web"
            tone=self.tone,                # Tone.Objective
            websocket=self.websocket,      # CustomLogsHandler 实例
            headers=self.headers,
        )
```

`BasicReport` 是一个轻量包装器，核心逻辑全部委托给 `GPTResearcher`。

#### Step 4：GPTResearcher 初始化（状态诞生）

**`GPTResearcher.__init__`**（`agent.py:51-197`）—— 这里是**状态初始化**的核心：

```python
class GPTResearcher:
    def __init__(self, query, ...):
        # ========= 状态初始化 =========
        self.query = "AI对教育的影响"
        self.cfg = Config(config_path)         # 加载配置（.env + 默认值）
        self.context = []                       # 空列表 ← 后续累积研究上下文
        self.visited_urls = set()               # 空集合 ← 后续累积已访问 URL
        self.research_sources = []              # 空列表 ← 后续累积抓取的源
        self.research_images = []               # 空列表 ← 后续累积图片
        self.research_costs = 0.0               # 零费用 ← 后续累加
        self.agent = None                       # 未选择 ← Step 6 赋值
        self.role = None                        # 未选择 ← Step 6 赋值

        # ========= 组件初始化 =========
        self.retrievers = get_retrievers(self.headers, self.cfg)  # [TavilySearch]
        self.memory = Memory(embedding_provider, embedding_model)  # Embedding 管理器

        self.research_conductor = ResearchConductor(self)   # 研究执行器
        self.report_generator = ReportGenerator(self)       # 报告生成器
        self.context_manager = ContextManager(self)         # 上下文管理器
        self.scraper_manager = BrowserManager(self)         # 浏览器/抓取管理器
        self.source_curator = SourceCurator(self)           # 源排序器
```

**此刻状态快照**：

| 字段 | 值 |
|------|---|
| `query` | `"AI对教育的影响"` |
| `context` | `[]` |
| `visited_urls` | `set()` |
| `research_sources` | `[]` |
| `research_costs` | `0.0` |
| `agent` | `None` |
| `role` | `None` |

#### Step 5：`BasicReport.run()` 触发两阶段执行

```python
# basic_report.py:67-70
async def run(self):
    await self.gpt_researcher.conduct_research()   # ← 阶段一：研究
    report = await self.gpt_researcher.write_report()  # ← 阶段二：写报告
    return report
```

#### Step 6：LLM 选择 Agent 类型

**`conduct_research()`** → **`choose_agent()`**（`agent.py:328-364`）：

```python
async def conduct_research(self):
    if not (self.agent and self.role):
        self.agent, self.role = await choose_agent(
            query=self.query, cfg=self.cfg, parent_query=self.parent_query, ...)
```

调用 **Smart LLM**，输入查询，让 LLM 返回最合适的 Agent 类型和角色描述。

**状态变化**：

| 字段 | 之前 | 之后 |
|------|------|------|
| `agent` | `None` | `"Research Agent"` |
| `role` | `None` | `"You are an AI research assistant specialized in..."` |
| `research_costs` | `0.0` | `≈0.003` |

#### Step 7：规划子查询

**`research_conductor.conduct_research()`** → **`_get_context_by_web_search()`** → **`plan_research()`**（`skills/researcher.py:48-87`）：

```python
async def plan_research(self, query, query_domains=None):
    # 7a: 先做一次初步搜索获取背景信息
    search_results = await get_search_results(query, self.researcher.retrievers[0], ...)

    # 7b: 调用 Strategic LLM，基于搜索结果生成子查询列表
    outline = await plan_research_outline(
        query=query, search_results=search_results,
        agent_role_prompt=self.researcher.role, cfg=self.researcher.cfg, ...)
    return outline   # → ["AI课堂应用", "个性化学习", "教师角色变化", "AI工具优缺点"]
```

**状态变化**：

| 字段 | 之前 | 之后 |
|------|------|------|
| `research_costs` | `≈0.003` | `≈0.008`（Tavily 搜索 + Strategic LLM） |

#### Step 8：对每个子查询并行「搜索→抓取→压缩」

**`_get_context_by_web_search()`**（`skills/researcher.py:266-365`）：

```python
sub_queries = await self.plan_research(query, query_domains)
sub_queries.append(query)   # 追加原始查询 → ["AI课堂应用", "个性化学习", ..., "AI对教育的影响"]

# 对所有子查询并行处理
context = await asyncio.gather(*[
    self._process_sub_query(sub_query, scraped_data, query_domains)
    for sub_query in sub_queries
])
```

**每个 `_process_sub_query` 内部**（`skills/researcher.py:449-578`）：

```
_process_sub_query("AI课堂应用")
  │
  ├─ _scrape_data_by_urls("AI课堂应用")
  │    ├─ _search_relevant_source_urls()
  │    │    └─ TavilySearch("AI课堂应用").search(max_results=5)
  │    │       → [{url, title, snippet}, ...]              ← 搜索引擎返回结果
  │    │
  │    ├─ _get_new_urls()                                   ← URL 去重
  │    │    → visited_urls += {url1, url2, url3...}
  │    │
  │    └─ scraper_manager.browse_urls([url1, url2, ...])
  │         → [{url, raw_content, image_urls, title}, ...]  ← 抓取完整网页内容
  │
  └─ context_manager.get_similar_content_by_query("AI课堂应用", scraped_data)
       │  RecursiveCharacterTextSplitter → 将文档切分为小块
       │  EmbeddingsFilter(similarity_threshold) → 用 Embedding 相似度过滤
       └─ → "与查询最相关的文本片段..."                       ← 压缩后的上下文
```

**状态变化**（所有子查询完成后）：

| 字段 | 之前 | 之后 |
|------|------|------|
| `visited_urls` | `set()` | `{url1, url2, ..., url20}`（约 20 个 URL） |
| `research_sources` | `[]` | `[{url, raw_content, images, title}, ...]` |
| `research_costs` | `≈0.008` | `≈0.025`（多次搜索 + Embedding 调用） |

#### Step 9：汇总上下文 + 可选源排序

```python
# skills/researcher.py:194-211
self.researcher.context = research_data   # 合并所有子查询的压缩上下文

# 可选：用 Smart LLM 对源进行可信度排序
if self.researcher.cfg.curate_sources:
    self.researcher.context = await self.researcher.source_curator.curate_sources(research_data)
```

**状态变化**：

| 字段 | 之前 | 之后 |
|------|------|------|
| `context` | `[]` | `["相关片段1...", "相关片段2...", ...]`（精炼后上下文） |
| `research_costs` | `≈0.025` | `≈0.030`（如果启用了源排序） |

**至此，`conduct_research()` 完成，进入报告生成阶段。**

#### Step 10：`write_report()` — LLM 生成最终报告

**`GPTResearcher.write_report()`** → **`report_generator.write_report()`**（`agent.py:445-485`）：

```python
async def write_report(self, ...):
    report = await self.report_generator.write_report(
        ext_context=self.context,              # 传入精炼后的上下文
        available_images=self.available_images, # 传入预生成的图片（如有）
    )
    return report
```

**内部调用链**（`skills/writer.py` → `actions/report_generation.py`）：

```
report_generator.write_report()
  │
  ├─ generate_report()                      ← Smart LLM 生成报告正文
  │    prompt = generate_report_prompt(
  │      query, context, agent_role, report_format, total_words, ...)
  │    report = await create_chat_completion(model=smart_llm, messages=[prompt], ...)
  │    → "# AI对教育的影响\n\n## 引言\n..."   ← Markdown 报告
  │
  ├─ add_references(report, visited_urls)    ← 在末尾添加引用列表
  │    → report += "\n## References\n1. [来源标题](url)\n..."
  │
  └─ table_of_contents(report)               ← 提取 headers 生成目录
       → 插入目录到报告中
```

**状态变化**：

| 字段 | 之前 | 之后 |
|------|------|------|
| `research_costs` | `≈0.030` | `≈0.065`（Smart LLM 生成长报告） |

**`write_report()` 返回值**：一个完整的 Markdown 字符串（包含标题、目录、正文、结论、引用）。

#### Step 11：格式转换 + 文件写入

回到 `handle_start_command()`（`server_utils.py:170-174`）：

```python
report = str(report)
file_paths = await generate_report_files(report, sanitized_filename)
# 内部:
#   pdf_path  = await write_md_to_pdf(report, filename)   → outputs/task_xxx.pdf
#   docx_path = await write_md_to_word(report, filename)  → outputs/task_xxx.docx
#   md_path   = await write_text_to_md(report, filename)  → outputs/task_xxx.md
```

#### Step 12：WebSocket 推送文件路径给前端

```python
file_paths["json"] = os.path.relpath(logs_handler.log_file)
await send_file_paths(websocket, file_paths)
# → websocket.send_json({"type": "path", "output": {"pdf": "...", "docx": "...", "md": "...", "json": "..."}})
```

前端收到最终消息：

```json
{
  "type": "path",
  "output": {
    "pdf": "outputs/task_1739836800_a1b2c3d4e5.pdf",
    "docx": "outputs/task_1739836800_a1b2c3d4e5.docx",
    "md": "outputs/task_1739836800_a1b2c3d4e5.md",
    "json": "outputs/task_1739836800_a1b2c3d4e5.json"
  }
}
```

#### 全链路调用栈总览

```
main.py
 └─ uvicorn.run(app)
     └─ app.py: websocket_endpoint()
         └─ handle_websocket_communication()
             └─ handle_start_command()
                 ├─ extract_command_data()           ← 解析输入
                 ├─ CustomLogsHandler()              ← 创建日志流
                 └─ manager.start_streaming()
                     └─ run_agent()                  ← 路由分发
                         └─ BasicReport()
                             └─ GPTResearcher()      ← 状态初始化
                                 │
                                 ├─ .conduct_research()
                                 │   ├─ choose_agent()           [Smart LLM]     → agent/role 赋值
                                 │   └─ research_conductor.conduct_research()
                                 │       └─ _get_context_by_web_search()
                                 │           ├─ plan_research()
                                 │           │   ├─ get_search_results()      [Tavily]        初步搜索
                                 │           │   └─ plan_research_outline()   [Strategic LLM]  子查询
                                 │           │
                                 │           └─ asyncio.gather(*sub_queries)  ← 并行
                                 │               └─ _process_sub_query()      × N
                                 │                   ├─ _scrape_data_by_urls()
                                 │                   │   ├─ retriever.search()           [Tavily]
                                 │                   │   └─ scraper_manager.browse_urls() [BS4]
                                 │                   └─ context_manager.get_similar_content_by_query()
                                 │                       └─ EmbeddingsFilter()           [Embedding]
                                 │
                                 └─ .write_report()
                                     └─ report_generator.write_report()
                                         ├─ generate_report()       [Smart LLM]   生成正文
                                         ├─ add_references()                       添加引用
                                         └─ table_of_contents()                    生成目录
                                             │
                                             ▼
                         generate_report_files(report)
                             ├─ write_md_to_pdf()   → outputs/xxx.pdf
                             ├─ write_md_to_word()  → outputs/xxx.docx
                             └─ write_text_to_md()  → outputs/xxx.md
                                 │
                                 ▼
                         send_file_paths(websocket)  → {"type":"path","output":{...}}
```

#### 状态变化时间线

```
时刻0  GPTResearcher.__init__()
       ┌─────────────────────────────────────────────────────┐
       │ context=[], visited_urls={}, costs=0.0              │
       │ agent=None, role=None, research_sources=[]          │
       └─────────────────────────────────────────────────────┘

时刻1  choose_agent()                     [Smart LLM 调用]
       ┌─────────────────────────────────────────────────────┐
       │ agent="Research Agent"                              │
       │ role="You are an AI research assistant..."          │
       │ costs ≈ 0.003                                       │
       └─────────────────────────────────────────────────────┘

时刻2  get_search_results()               [Tavily API 调用]
       ┌─────────────────────────────────────────────────────┐
       │ (初步搜索，获取背景信息，不改变主状态)                    │
       └─────────────────────────────────────────────────────┘

时刻3  plan_research_outline()            [Strategic LLM 调用]
       ┌─────────────────────────────────────────────────────┐
       │ sub_queries=["AI课堂应用", "个性化学习", ...]          │
       │ costs ≈ 0.008                                       │
       └─────────────────────────────────────────────────────┘

时刻4  _process_sub_query() × N 并行      [N × Tavily + N × BS4 + N × Embedding]
       ┌─────────────────────────────────────────────────────┐
       │ visited_urls = {url1, url2, ..., url20}             │
       │ research_sources = [{url, content, images}, ...]    │
       │ costs ≈ 0.025                                       │
       └─────────────────────────────────────────────────────┘

时刻5  curate_sources()（可选）             [Smart LLM 调用]
       ┌─────────────────────────────────────────────────────┐
       │ context = ["精炼片段1", "精炼片段2", ...]              │
       │ costs ≈ 0.030                                       │
       └─────────────────────────────────────────────────────┘

时刻6  generate_report()                   [Smart LLM 调用]
       ┌─────────────────────────────────────────────────────┐
       │ → 返回 Markdown 报告字符串                             │
       │ costs ≈ 0.065                                       │
       └─────────────────────────────────────────────────────┘

时刻7  add_references() + table_of_contents()
       ┌─────────────────────────────────────────────────────┐
       │ → 完整报告（含引用和目录）                               │
       └─────────────────────────────────────────────────────┘

时刻8  generate_report_files()
       ┌─────────────────────────────────────────────────────┐
       │ → PDF + DOCX + MD 文件写入 outputs/ 目录              │
       └─────────────────────────────────────────────────────┘

时刻9  send_file_paths()
       ┌─────────────────────────────────────────────────────┐
       │ → WebSocket 推送文件路径给前端                          │
       └─────────────────────────────────────────────────────┘
```

#### 过程中的 WebSocket 推送时序

在整个执行过程中，前端会依次收到以下 WebSocket 消息：

```
时刻1  {"type":"logs", "content":"starting_research",  "output":"🔍 Starting the research task..."}
时刻1  {"type":"logs", "content":"agent_generated",    "output":"Research Agent"}
时刻2  {"type":"logs", "content":"planning_research",  "output":"🌐 Browsing the web..."}
时刻3  {"type":"logs", "content":"planning_research",  "output":"🤔 Planning the research strategy..."}
时刻3  {"type":"logs", "content":"subqueries",         "output":"🗂️ I will conduct my research based on..."}
时刻4  {"type":"logs", "content":"running_subquery_research", "output":"🔍 Running research for 'AI课堂应用'..."}
  ...（每个子查询一条）
时刻4  {"type":"logs", "content":"researching",        "output":"🤔 Researching for relevant information..."}
  ...（每个子查询一条）
时刻5  {"type":"logs", "content":"research_step_finalized", "output":"Finalized research step.\n💸 Total: $0.030"}
时刻6  {"type":"report","output":"# AI对教育的影响\n\n## 引言\n..."}  ← 报告内容逐段推送
时刻8  {"type":"path",  "output":{"pdf":"outputs/xxx.pdf","docx":"outputs/xxx.docx","md":"outputs/xxx.md"}}
```

---

## 3. 多 Agent 协作深度分析

### 3.1 Agent 角色一览

系统共有 **7 个 Agent 类** + **1 个调度器类**，分布在两层工作流中：

| Agent | 类名 | 源文件 | 所属工作流 | 是否调用 LLM |
|-------|------|--------|-----------|-------------|
| **Chief Editor** | `ChiefEditorAgent` | `orchestrator.py` | 顶层调度器（不参与图节点） | 否 |
| **Researcher** | `ResearchAgent` | `researcher.py` | 主图 + 子图 | 是（内部封装 GPTResearcher） |
| **Editor** | `EditorAgent` | `editor.py` | 主图（承担 2 个节点） | 是（规划大纲） |
| **Human** | `HumanAgent` | `human.py` | 主图 | 否 |
| **Reviewer** | `ReviewerAgent` | `reviewer.py` | 子图 | 是（审查稿件） |
| **Reviser** | `ReviserAgent` | `reviser.py` | 子图 | 是（修改稿件） |
| **Writer** | `WriterAgent` | `writer.py` | 主图 | 是（写引言结论） |
| **Publisher** | `PublisherAgent` | `publisher.py` | 主图 | 否 |

### 3.2 每个 Agent 的详细职责（源码级）

#### Chief Editor — 总编辑（调度器本体）

**职责**：初始化所有 Agent，构建 LangGraph `StateGraph`，编排节点和边，触发整个流程执行。它**不作为图中的节点**，而是图的创建者和执行者。

**核心代码**（`orchestrator.py:52-66`）：
```python
def _create_workflow(self, agents):
    workflow = StateGraph(ResearchState)
    workflow.add_node("browser", agents["research"].run_initial_research)
    workflow.add_node("planner", agents["editor"].plan_research)
    workflow.add_node("researcher", agents["editor"].run_parallel_research)
    workflow.add_node("writer", agents["writer"].run)
    workflow.add_node("publisher", agents["publisher"].run)
    workflow.add_node("human", agents["human"].review_plan)
    self._add_workflow_edges(workflow)
    return workflow
```

**初始化的 Agent 实例**（`orchestrator.py:43-50`）：
```python
def _initialize_agents(self):
    return {
        "writer": WriterAgent(self.websocket, self.stream_output, self.headers),
        "editor": EditorAgent(self.websocket, self.stream_output, self.tone, self.headers),
        "research": ResearchAgent(self.websocket, self.stream_output, self.tone, self.headers),
        "publisher": PublisherAgent(self.output_dir, self.websocket, self.stream_output, self.headers),
        "human": HumanAgent(self.websocket, self.stream_output, self.headers)
    }
```

#### Researcher — 研究员

**职责**：承担两种研究任务。`run_initial_research` 做初步广度研究，为 Editor 提供规划素材；`run_depth_research` 对单个子主题做深度研究，生成该章节的草稿。内部封装了完整的 `GPTResearcher`（搜索→抓取→压缩→生成报告）。

**初步研究**（`researcher.py:34-44`）：
```python
async def run_initial_research(self, research_state: dict):
    task = research_state.get("task")
    query = task.get("query")
    source = task.get("source", "web")
    return {"task": task, "initial_research": await self.research(
        query=query, verbose=task.get("verbose"), source=source, tone=self.tone, headers=self.headers)}
```

**深度研究**（`researcher.py:46-58`）：
```python
async def run_depth_research(self, draft_state: dict):
    task = draft_state.get("task")
    topic = draft_state.get("topic")
    parent_query = task.get("query")
    research_draft = await self.run_subtopic_research(
        parent_query=parent_query, subtopic=topic, verbose=verbose, source=source, headers=self.headers)
    return {"draft": research_draft}
```

**内部调用链**（`researcher.py:13-23`）：
```python
async def research(self, query, ...):
    researcher = GPTResearcher(query=query, report_type=research_report, ...)
    await researcher.conduct_research()   # 搜索 + 抓取 + 压缩
    report = await researcher.write_report()  # LLM 生成报告
    return report
```

#### Editor — 编辑

**职责**：承担**两个图节点**。作为 `planner` 时，调用 LLM 将初步研究拆分为章节大纲（JSON 输出）；作为 `researcher` 时，**创建子工作流（Researcher→Reviewer→Reviser 循环）并用 `asyncio.gather` 并行执行所有章节**。

**规划大纲**（`editor.py:22-50`）：
```python
async def plan_research(self, research_state):
    initial_research = research_state.get("initial_research")
    human_feedback = research_state.get("human_feedback")  # 若有人工反馈则纳入
    prompt = self._create_planning_prompt(initial_research, ...)
    plan = await call_model(prompt=prompt, model=task.get("model"), response_format="json")
    return {"title": plan.get("title"), "date": plan.get("date"), "sections": plan.get("sections")}
```

**并行调度**（`editor.py:52-77`）：
```python
async def run_parallel_research(self, research_state):
    workflow = self._create_workflow()   # 创建 Researcher→Reviewer→Reviser 子图
    chain = workflow.compile()
    queries = research_state.get("sections")  # 所有章节标题
    final_drafts = [
        chain.ainvoke(self._create_task_input(research_state, query, title), ...)
        for query in queries
    ]
    research_results = [result["draft"] for result in await asyncio.gather(*final_drafts)]
    return {"research_data": research_results}
```

#### Human — 人工审核

**职责**：可选的人工反馈节点。通过 WebSocket（Web 端）或 `input()`（控制台）接收用户对研究大纲的审核意见。返回 `None` 表示通过，否则携带反馈内容。

**核心逻辑**（`human.py:10-52`）：
```python
async def review_plan(self, research_state: dict):
    if task.get("include_human_feedback"):
        if self.websocket and self.stream_output:
            await self.stream_output("human_feedback", "request",
                f"Any feedback on this plan of topics to research? {layout}?", self.websocket)
            response = await self.websocket.websocket.receive_text()  # 阻塞等待
        else:
            user_feedback = input(f"Any feedback on this plan? ...")   # 控制台阻塞
    if user_feedback and "no" in user_feedback.strip().lower():
        user_feedback = None  # "no" 视为无反馈 → 通过
    return {"human_feedback": user_feedback}
```

#### Reviewer — 审稿人

**职责**：对标 `task.guidelines` 审查草稿质量。如果 `follow_guidelines=False`，直接跳过返回 `None`（通过）。如果审查后草稿满足要求，返回 `None`；否则返回具体的修改意见字符串。

**核心逻辑**（`reviewer.py:63-79`）：
```python
async def run(self, draft_state: dict):
    to_follow_guidelines = task.get("follow_guidelines")
    review = None
    if to_follow_guidelines:
        review = await self.review_draft(draft_state)
    else:
        print_agent_output(f"Ignoring guidelines...", agent="REVIEWER")
    return {"review": review}
```

**关键收敛机制**（`reviewer.py:25-29`）—— 当存在 `revision_notes`（即已经修改过一轮）时，提示词会告知：
```
The reviser has already revised the draft based on your previous review notes...
Please provide additional feedback ONLY if critical since the reviser has already
made changes based on your previous feedback.
If you think the article is sufficient, please aim to return None.
```
这是**通过提示词实现的软收敛机制**，引导 Reviewer 在后续轮次中倾向于接受，避免无限循环。

#### Reviser — 修改者

**职责**：接收 Reviewer 的反馈，调用 LLM 修改草稿，返回修改后的 `draft` 和 `revision_notes`。

**核心逻辑**（`reviser.py:54-74`）：
```python
async def run(self, draft_state: dict):
    revision = await self.revise_draft(draft_state)
    return {
        "draft": revision.get("draft"),           # 修改后的草稿
        "revision_notes": revision.get("revision_notes"),  # 修改说明
    }
```

**LLM 提示词要求返回 JSON**（`reviser.py:30-45`）：
```
Draft: {draft_report}
Reviewer's notes: {review}
You MUST return nothing but a JSON:
{ "draft": {revised draft}, "revision_notes": {message about changes made} }
```

#### Writer — 写作者

**职责**：接收所有章节的研究数据，调用 LLM 撰写引言、结论、目录，汇编源列表。如果启用了 guidelines，还会对报告 headers 做二次 LLM 修订。

**核心逻辑**（`writer.py:94-142`）：
```python
async def run(self, research_state: dict):
    research_layout_content = await self.write_sections(research_state)  # LLM 调用
    headers = self.get_headers(research_state)
    if research_state.get("task").get("follow_guidelines"):
        headers = await self.revise_headers(task=..., headers=headers)   # 再次 LLM 调用
    return {**research_layout_content, "headers": headers}
```

**LLM 要求返回结构化 JSON**：
```python
# 返回格式
{
    "table_of_contents": "...",  # Markdown 目录
    "introduction": "...",       # 引言
    "conclusion": "...",         # 结论
    "sources": ["- Title, Author [url](url)", ...]  # APA 格式引用
}
```

#### Publisher — 发布者

**职责**：纯粹的格式化输出节点。将 `ResearchState` 中的全部内容拼装为完整的 Markdown 布局，然后按 `publish_formats` 配置导出为 PDF / DOCX / Markdown 文件。**不调用 LLM**。

**布局拼装**（`publisher.py:22-53`）：
```python
def generate_layout(self, research_state: dict):
    layout = f"""# {headers.get('title')}
#### {headers.get("date")}: {research_state.get('date')}
## {headers.get("introduction")}
{research_state.get('introduction')}
## {headers.get("table_of_contents")}
{research_state.get('table_of_contents')}
{sections_text}
## {headers.get("conclusion")}
{research_state.get('conclusion')}
## {headers.get("references")}
{references}"""
    return layout
```

**格式导出**（`publisher.py:55-61`）：
```python
async def write_report_by_formats(self, layout, publish_formats):
    if publish_formats.get("pdf"):   await write_md_to_pdf(layout, self.output_dir)
    if publish_formats.get("docx"):  await write_md_to_word(layout, self.output_dir)
    if publish_formats.get("markdown"): await write_text_to_md(layout, self.output_dir)
```

### 3.3 调度方式：串行 + 条件分支 + 并行

系统**三种调度方式都有**，各出现在不同位置。

#### 3.3.1 主工作流边定义（`orchestrator.py:68-81`）

```python
def _add_workflow_edges(self, workflow):
    workflow.add_edge('browser', 'planner')          # ① 串行
    workflow.add_edge('planner', 'human')             # ② 串行
    workflow.add_edge('researcher', 'writer')         # ③ 串行
    workflow.add_edge('writer', 'publisher')          # ④ 串行
    workflow.set_entry_point("browser")
    workflow.add_edge('publisher', END)               # ⑤ 串行 → 结束

    # 条件分支：人工审核
    workflow.add_conditional_edges(                   # ⑥ 条件分支
        'human',
        lambda review: "accept" if review['human_feedback'] is None else "revise",
        {"accept": "researcher", "revise": "planner"}
    )
```

#### 3.3.2 子工作流边定义（`editor.py:126-144`）

```python
def _create_workflow(self):
    workflow = StateGraph(DraftState)
    workflow.add_node("researcher", agents["research"].run_depth_research)
    workflow.add_node("reviewer", agents["reviewer"].run)
    workflow.add_node("reviser", agents["reviser"].run)

    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "reviewer")       # 串行
    workflow.add_edge("reviser", "reviewer")           # reviser → reviewer（循环边）
    workflow.add_conditional_edges(                     # 条件分支
        "reviewer",
        lambda draft: "accept" if draft["review"] is None else "revise",
        {"accept": END, "revise": "reviser"},
    )
```

#### 3.3.3 并行执行（`editor.py:68-76`）

```python
final_drafts = [
    chain.ainvoke(self._create_task_input(research_state, query, title), ...)
    for query in queries        # N 个章节
]
research_results = [
    result["draft"] for result in await asyncio.gather(*final_drafts)  # 并行等待
]
```

#### 3.3.4 调度模式总结

| 模式 | 出现位置 | 代码机制 |
|------|---------|---------|
| **串行** | 主图的 browser→planner→human、researcher→writer→publisher | `add_edge()` 固定顺序 |
| **条件分支** | human 节点之后、reviewer 节点之后 | `add_conditional_edges()` + lambda 判断 |
| **并行** | researcher 节点内部，多个章节同时研究 | `asyncio.gather()` 并发执行 N 个子图 |

### 3.4 循环执行：有，存在两处

#### 循环 1：Human → Planner 循环（主图）

```
Planner ──► Human ──[feedback != None]──► Planner   （循环直到人工说"接受"）
                   └─[feedback == None]──► Researcher （通过，继续后续流程）
```

- **触发条件**：`review['human_feedback'] is not None`，即人工给出了修改意见
- **终止条件**：`human_feedback is None`（用户回复 "no" 或不提供反馈）
- **收敛保障**：人工控制，由用户决定何时结束

#### 循环 2：Reviewer → Reviser → Reviewer 循环（子图）

```
Researcher ──► Reviewer ──[review != None]──► Reviser ──► Reviewer   （循环）
                         └─[review == None]──► END                    （通过）
```

- **触发条件**：`draft["review"] is not None`，即 Reviewer 给出了修改意见
- **终止条件**：`draft["review"] is None`，即 Reviewer 认为草稿合格
- **收敛保障**：通过提示词实现**软收敛** —— 当存在 `revision_notes` 时，提示词明确要求"只有在严重问题时才继续要求修改，否则返回 None"（见 `reviewer.py:25-29`）
- **注意**：没有硬性的最大迭代次数限制，理论上可能出现无限循环（但提示词收敛策略在实践中有效）

### 3.5 冲突仲裁：无显式机制

系统**没有显式的冲突仲裁机制**，原因如下：

| 场景 | 为什么不需要仲裁 |
|------|----------------|
| 主图串行执行 | 每个节点只有一个前驱，不存在多个 Agent 同时写入同一字段 |
| 并行子图互相独立 | 每个章节有自己独立的 `DraftState` 实例，互不干涉 |
| 审查-修改是一对一 | Reviewer 给 Reviser 提意见，不存在多个 Reviewer 意见冲突 |
| 并行结果收集 | `asyncio.gather` 的结果是一个列表，直接拼接到 `research_data`，不需要合并冲突 |
| Human 节点阻塞 | 等待人工回复后才继续，不存在并发写入 |

### 3.6 Agent 之间的数据共享

数据共享**完全通过 LangGraph 状态对象传递**，没有任何全局变量、消息队列或直接通信。每个节点从状态中读取所需字段，处理后返回需要更新的字段。

#### 主图数据共享矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│                    ResearchState（主图共享）                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [browser] (ResearchAgent)                                      │
│    读取: task                                                    │
│    写入: task, initial_research                                  │
│                     ↓                                           │
│  [planner] (EditorAgent)                                        │
│    读取: task, initial_research, human_feedback                  │
│    写入: title, date, sections                                   │
│                     ↓                                           │
│  [human] (HumanAgent)                                           │
│    读取: task, sections                                          │
│    写入: human_feedback                                          │
│                     ↓                                           │
│  [researcher] (EditorAgent)                                     │
│    读取: task, sections, title                                   │
│    写入: research_data        ← 并行子图结果汇总                    │
│                     ↓                                           │
│  [writer] (WriterAgent)                                         │
│    读取: task, title, research_data                               │
│    写入: table_of_contents, introduction, conclusion,            │
│          sources, headers                                       │
│                     ↓                                           │
│  [publisher] (PublisherAgent)                                   │
│    读取: task, research_data, sources, headers, date,            │
│          introduction, table_of_contents, conclusion             │
│    写入: report                                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 子图数据共享矩阵

```
┌─────────────────────────────────────────────────────────────────┐
│                DraftState（每个章节子图独立一份）                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [researcher] (ResearchAgent)                                   │
│    读取: task, topic                                             │
│    写入: draft                                                   │
│                     ↓                                           │
│  [reviewer] (ReviewerAgent)                                     │
│    读取: task, draft, revision_notes                             │
│    写入: review                                                  │
│              ↓ (review != None)                                  │
│  [reviser] (ReviserAgent)                                       │
│    读取: task, draft, review                                     │
│    写入: draft, revision_notes                                   │
│              ↓                                                  │
│  [reviewer] ← 循环                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 数据共享设计原则

- **无共享内存** —— Agent 之间不直接通信，全靠 LangGraph 状态传递
- **无消息队列** —— 不是 pub/sub 模式，是函数调用链
- **写入隔离** —— 每个节点只写入自己负责的字段，不覆盖他人字段
- **子图隔离** —— 并行的 N 个子图各有独立的 `DraftState` 实例，互不干涉

### 3.7 简化版全景流程图

```
╔══════════════════════════════════════════════════════════════════════╗
║                          主工作流 (Main Graph)                       ║
║                     状态对象: ResearchState                          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  ┌──────────┐    ┌──────────┐    ┌──────────┐                       ║
║  │ Browser  │───▶│ Planner  │───▶│  Human   │                       ║
║  │(Research │    │(Editor   │    │(Human    │                       ║
║  │ Agent)   │    │ Agent)   │    │ Agent)   │                       ║
║  │          │    │          │◀───│          │                       ║
║  │ 初步研究  │    │ 规划章节  │ 驳回│ 人工审核  │                       ║
║  └──────────┘    └──────────┘    └────┬─────┘                       ║
║                                    通过│                              ║
║                                       ▼                              ║
║  ┌────────────────────────────────────────────────────────────┐     ║
║  │              Researcher (Editor Agent)                      │     ║
║  │              并行调度 N 个子工作流                              │     ║
║  │                                                            │     ║
║  │  ┌─────────────┐ ┌─────────────┐     ┌─────────────┐      │     ║
║  │  │  子图: 章节1  │ │  子图: 章节2  │ ... │  子图: 章节N  │      │     ║
║  │  │             │ │             │     │             │      │     ║
║  │  │ ┌─────────┐ │ │ ┌─────────┐ │     │ ┌─────────┐ │      │     ║
║  │  │ │Research │ │ │ │Research │ │     │ │Research │ │      │     ║
║  │  │ │ Agent   │ │ │ │ Agent   │ │     │ │ Agent   │ │      │     ║
║  │  │ │ 深度研究 │ │ │ │ 深度研究 │ │     │ │ 深度研究 │ │      │     ║
║  │  │ └────┬────┘ │ │ └────┬────┘ │     │ └────┬────┘ │      │     ║
║  │  │      ▼      │ │      ▼      │     │      ▼      │      │     ║
║  │  │ ┌─────────┐ │ │ ┌─────────┐ │     │ ┌─────────┐ │      │     ║
║  │  │ │Reviewer │ │ │ │Reviewer │ │     │ │Reviewer │ │      │     ║
║  │  │ │ 审稿    │ │ │ │ 审稿    │ │     │ │ 审稿    │ │      │     ║
║  │  │ └──┬───┬──┘ │ │ └──┬───┬──┘ │     │ └──┬───┬──┘ │      │     ║
║  │  │  通过  驳回  │ │  通过  驳回  │     │  通过  驳回  │      │     ║
║  │  │   │    ▼    │ │   │    ▼    │     │   │    ▼    │      │     ║
║  │  │   │ ┌─────┐ │ │   │ ┌─────┐ │     │   │ ┌─────┐ │      │     ║
║  │  │   │ │Revis│ │ │   │ │Revis│ │     │   │ │Revis│ │      │     ║
║  │  │   │ │er   │ │ │   │ │er   │ │     │   │ │er   │ │      │     ║
║  │  │   │ │修改  │ │ │   │ │修改  │ │     │   │ │修改  │ │      │     ║
║  │  │   │ └──┬──┘ │ │   │ └──┬──┘ │     │   │ └──┬──┘ │      │     ║
║  │  │   │    │循环 │ │   │    │循环 │     │   │    │循环 │      │     ║
║  │  │   ▼    ▲    │ │   ▼    ▲    │     │   ▼    ▲    │      │     ║
║  │  │  END ──┘    │ │  END ──┘    │     │  END ──┘    │      │     ║
║  │  └─────────────┘ └─────────────┘     └─────────────┘      │     ║
║  │                                                            │     ║
║  │  asyncio.gather() 等待全部完成 → research_data              │     ║
║  └────────────────────────────────────────────────────────────┘     ║
║                                       │                              ║
║                                       ▼                              ║
║                              ┌──────────┐    ┌──────────┐           ║
║                              │  Writer  │───▶│Publisher │───▶ END   ║
║                              │          │    │          │           ║
║                              │ 写引言结论 │    │ 导出文件  │           ║
║                              │ 汇编目录  │    │ PDF/DOCX │           ║
║                              └──────────┘    └──────────┘           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

**精简文字版**：

```
Browser ──串行──▶ Planner ──串行──▶ Human ──条件──┬──▶ Researcher ──串行──▶ Writer ──串行──▶ Publisher ──▶ END
                    ▲                            │     (并行N个子图)
                    └────────────驳回─────────────┘
                                                       每个子图内部:
                                                       Researcher ──▶ Reviewer ──条件──┬──▶ END
                                                                        ▲              │
                                                                        └── Reviser ◀──┘(驳回循环)
```

**调度模式总结**：

```
主图:  串行 + 1处条件分支(Human→Planner循环)
子图:  串行 + 1处条件分支(Reviewer→Reviser循环)
跨图:  N个子图通过 asyncio.gather 并行执行
仲裁:  无（写入字段不冲突，子图实例独立）
收敛:  提示词软收敛（"仅在严重问题时继续修改"）
```

### 3.8 LLM 调用工具函数

所有多 Agent 中的 LLM 调用都通过统一的 `call_model()` 函数（`multi_agents/agents/utils/llms.py`）：

```python
async def call_model(prompt: list, model: str, response_format: str | None = None):
    cfg = Config()
    lc_messages = convert_openai_messages(prompt)
    response = await create_chat_completion(
        model=model,
        messages=lc_messages,
        temperature=0,
        llm_provider=cfg.smart_llm_provider,
        llm_kwargs=cfg.llm_kwargs,
    )
    if response_format == "json":
        return parse_json_markdown(response, parser=json_repair.loads)
    return response
```

**设计要点**：
- 使用 `temperature=0` 确保输出稳定性
- JSON 格式返回时自动解析并带有容错修复（`json_repair.loads`）
- 模型由 `task.json` 中的 `model` 字段指定，而非使用全局 LLM 分级策略

### 3.9 Agent 提示词模板

#### Editor 规划提示词

```
System: "You are a research editor. Your goal is to oversee the research project
from inception to completion. Your main task is to plan the article section
layout based on an initial research summary."

User: "Today's date is {date}
Research summary report: '{initial_research}'
{Human feedback instruction if applicable}

Your task is to generate an outline of sections headers for the research project
based on the research summary report above.
You must generate a maximum of {max_sections} section headers.
You must focus ONLY on related research topics for subheaders and do NOT include
introduction, conclusion and references.
You must return nothing but a JSON with the fields 'title' (str) and
'sections' (maximum {max_sections} section headers)..."
```

#### Reviewer 审查提示词

```
System: "You are an expert research article reviewer. Your goal is to review
research drafts and provide feedback to the reviser only based on specific guidelines."

User: "Please accept the draft if it is good enough to publish, or send it
for revision, along with your notes to guide the revision.
If not all of the guideline criteria are met, you should send appropriate revision notes.
If the draft meets all the guidelines, please return None.

[若已有修改记录，追加:]
The reviser has already revised the draft based on your previous review notes...
Please provide additional feedback ONLY if critical.
If you think the article is sufficient, please aim to return None.

Guidelines: {guidelines}
Draft: {draft}"
```

#### Reviser 修改提示词

```
System: "You are an expert writer. Your goal is to revise drafts based on
reviewer notes."

User: "Draft: {draft_report}
Reviewer's notes: {review}

You have been tasked by your reviewer with revising the following draft.
If you decide to follow the reviewer's notes, please write a new draft and
make sure to address all of the points they raised.
Please keep all other aspects of the draft the same.
You MUST return nothing but a JSON in the following format:
{
  'draft': {revised draft},
  'revision_notes': {message about changes made}
}"
```

#### Writer 写作提示词

```
System: "You are a research writer. Your sole purpose is to write a well-written
research reports about a topic based on research findings and information."

User: "Today's date is {date}
Query or Topic: {query}
Research data: {research_data}

Your task is to write an in depth, well written and detailed introduction and
conclusion to the research report based on the provided research data.
Do not include headers in the results.
You MUST include any relevant sources as markdown hyperlinks.

{Guidelines instruction if follow_guidelines is True}

You MUST return nothing but a JSON in the following format:
{
  'table_of_contents': ...,
  'introduction': ...,
  'conclusion': ...,
  'sources': [list of APA formatted source links]
}"
```

---

## 4. 状态管理

### 4.1 单 Agent 状态（GPTResearcher 实例属性）

```python
class GPTResearcher:
    # 核心状态
    self.query: str                     # 用户查询
    self.context: List[str]             # 累积的研究上下文
    self.visited_urls: Set[str]         # 已访问 URL（去重）
    self.research_sources: List[dict]   # 抓取的源 {title, content, images, url}
    self.research_images: List[dict]    # 筛选的图片
    self.research_costs: float          # 累积 API 费用

    # 运行时状态
    self.subtopics: List[str]           # 生成的子主题
    self.agent: str                     # 选定的 Agent 类型
    self.role: str                      # Agent 角色描述

    # 配置
    self.cfg: Config                    # 配置对象
    self.report_type: str               # 报告类型
    self.report_source: str             # 数据来源（web/local/hybrid）

    # 组件引用
    self.researcher: ResearchConductor  # 研究执行器
    self.writer: ReportGenerator        # 报告生成器
    self.context_manager: ContextManager # 上下文管理器
    self.browser_manager: BrowserManager # 浏览器管理器
    self.source_curator: SourceCurator  # 源排序器
```

### 4.2 多 Agent 状态 —— 主工作流

```python
class ResearchState(TypedDict):
    task: dict                    # 任务配置（query, model, max_sections...）
    initial_research: str         # 初步研究摘要
    sections: List[str]           # 章节标题列表
    research_data: List[dict]     # 各章节研究结果（并行汇聚）
    human_feedback: str           # 人工反馈意见
    title: str                    # 报告标题
    headers: dict                 # 报告结构
    date: str                     # 报告日期
    table_of_contents: str        # 目录
    introduction: str             # 引言
    conclusion: str               # 结论
    sources: List[str]            # 引用源列表
    report: str                   # 最终报告全文
```

### 4.3 多 Agent 状态 —— 子工作流

```python
class DraftState(TypedDict):
    task: dict            # 任务配置
    topic: str            # 当前子主题
    draft: dict           # 草稿内容 {title, body, sources...}
    review: str           # 审稿人反馈（None 表示通过）
    revision_notes: str   # 修改说明
```

### 4.4 状态流转路径

```
┌─────────┐   +initial_research   ┌─────────┐   +sections, +title   ┌─────────┐
│  task    │ ──────────────────► │ Browser │ ──────────────────► │ Planner │
└─────────┘                      └─────────┘                     └─────────┘
                                                                      │
                                                              +human_feedback
                                                                      │
                                                                      ▼
┌─────────┐   +report            ┌─────────┐   +intro, +conclusion  ┌─────────┐
│Publisher │ ◄────────────────── │ Writer  │ ◄──────────────────── │Research │
└─────────┘                      └─────────┘   +toc, +sources       └─────────┘
     │                                                              +research_data
     ▼
   END（输出文件）
```

### 4.5 配置状态管理

```python
class Config:
    # LLM 配置
    FAST_LLM: str          = "openai:gpt-4o-mini"
    SMART_LLM: str         = "openai:gpt-4.1"
    STRATEGIC_LLM: str     = "openai:o4-mini"
    TEMPERATURE: float     = 0.4

    # 搜索配置
    RETRIEVER: str         = "tavily"
    MAX_SEARCH_RESULTS_PER_QUERY: int = 5
    MAX_ITERATIONS: int    = 4

    # 抓取配置
    SCRAPER: str           = "bs"
    MAX_SCRAPER_WORKERS: int = 4

    # 报告配置
    REPORT_FORMAT: str     = "APA"
    TOTAL_WORDS: int       = 1000
    LANGUAGE: str          = "english"

    # 深度研究配置
    DEEP_RESEARCH_BREADTH: int     = 4
    DEEP_RESEARCH_DEPTH: int       = 2
    DEEP_RESEARCH_CONCURRENCY: int = 4
```

配置加载优先级：**函数参数 > 环境变量 > 配置文件 > 默认值**

---

## 5. LLM 调用位置

### 5.1 三级 LLM 策略

| LLM 层级 | 默认模型 | 用途 | Token 限制 |
|----------|---------|------|-----------|
| `FAST_LLM` | gpt-4o-mini | 快速任务、轻量处理 | 2,000 |
| `SMART_LLM` | gpt-4.1 | 报告生成、源排序 | 4,000 |
| `STRATEGIC_LLM` | o4-mini | 规划、推理、复杂决策 | 4,000 |

### 5.2 所有 LLM 调用点详表

| 文件 | 函数 | LLM 层级 | 用途 |
|------|------|---------|------|
| `actions/agent_creator.py` | `choose_agent()` | Smart | 选择研究 Agent 类型和角色 |
| `actions/query_processing.py` | `generate_sub_queries()` | Strategic | 将主查询拆分为子查询列表 |
| `actions/query_processing.py` | `plan_research_outline()` | Strategic | 规划研究大纲和结构 |
| `actions/report_generation.py` | `generate_report()` | Smart | 生成报告正文 |
| `actions/report_generation.py` | `write_conclusion()` | Smart | 撰写报告结论 |
| `actions/report_generation.py` | `write_report_introduction()` | Smart | 撰写报告引言 |
| `actions/report_generation.py` | `generate_draft_section_titles()` | Smart | 生成章节标题 |
| `skills/curator.py` | `curate_sources()` | Smart | 评估和排序源的可信度 |
| `skills/deep_research.py` | `generate_research_plan()` | Strategic | 生成深度研究计划 |
| `skills/deep_research.py` | `generate_search_queries()` | Strategic | 生成搜索查询 |
| `skills/deep_research.py` | `process_research_results()` | Strategic | 提取研究发现和后续问题 |
| `utils/llm.py` | `construct_subtopics()` | Smart | 子主题结构化输出（Pydantic） |
| `mcp/tool_selector.py` | MCP 工具选择 | Smart | 选择合适的 MCP 工具 |
| `multi_agents/agents/editor.py` | `plan_research()` | 任务配置 | 规划章节大纲 |
| `multi_agents/agents/reviewer.py` | `run()` | 任务配置 | 审查稿件质量 |
| `multi_agents/agents/reviser.py` | `run()` | 任务配置 | 修改稿件 |
| `multi_agents/agents/writer.py` | `run()` | 任务配置 | 撰写引言和结论 |

### 5.3 LLM 提供商支持（20+）

| 提供商 | LangChain 集成 |
|--------|---------------|
| OpenAI | `langchain_openai.ChatOpenAI` |
| Anthropic | `langchain_anthropic.ChatAnthropic` |
| Azure OpenAI | `langchain_openai.AzureChatOpenAI` |
| Google Vertex AI | `langchain_google_vertexai.ChatVertexAI` |
| Google GenAI | `langchain_google_genai.ChatGoogleGenerativeAI` |
| Cohere | `langchain_cohere.ChatCohere` |
| Ollama | `langchain_ollama.ChatOllama` |
| Together | `langchain_together.ChatTogether` |
| Mistral AI | `langchain_mistralai.ChatMistralAI` |
| HuggingFace | `langchain_huggingface.ChatHuggingFace` |
| Groq | `langchain_groq.ChatGroq` |
| AWS Bedrock | `langchain_aws.ChatBedrock` |
| Fireworks | `langchain_fireworks.ChatFireworks` |
| DashScope (阿里) | OpenAI 兼容接口 |
| xAI | `langchain_xai.ChatXAI` |
| DeepSeek | OpenAI 兼容接口 |
| LiteLLM | `langchain_community.chat_models.litellm.ChatLiteLLM` |
| GigaChat | `langchain_gigachat.GigaChat` |
| OpenRouter | OpenAI 兼容接口 + 速率限制 |
| vLLM | 自托管 vLLM 服务 |
| AIMLAPI | OpenAI 兼容接口 |
| Netmind | `langchain_netmind.ChatNetmind` |

### 5.4 提示词模板体系

```python
class PromptFamily:
    """基础提示词族，可被继承覆盖"""

    def generate_search_queries_prompt()    # 生成搜索查询
    def generate_report_prompt()            # 生成报告正文
    def generate_subtopics_prompt()         # 生成子主题
    def generate_subtopic_report_prompt()   # 生成子主题报告
    def curate_sources()                    # 源排序评估
    def generate_image_analysis_prompt()    # 图片分析
    def generate_mcp_tool_selection_prompt() # MCP 工具选择

# 已有的提示词族变体
class GranitePromptFamily(PromptFamily): ...     # IBM Granite
class Granite3PromptFamily(PromptFamily): ...    # Granite 3.X
class Granite33PromptFamily(PromptFamily): ...   # Granite 3.3
```

---

## 6. 数据流流转

### 6.1 整体数据流

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  用户查询     │────▶│ 子查询生成     │────▶│ 搜索引擎检索   │
│  (query)     │     │ (Strategic   │     │ (Retriever)  │
│              │     │   LLM)       │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
                                               │
                                    [{url, title, snippet}]
                                               │
                                               ▼
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  最终报告     │◀────│ 上下文压缩     │◀────│ 网页抓取      │
│  (Markdown)  │     │ (Embedding   │     │ (Scraper)    │
│              │     │   Filter)    │     │              │
└─────────────┘     └──────────────┘     └──────────────┘
      │                                  [{url, raw_content,
      │                                   image_urls, title}]
      ▼
┌─────────────┐
│ PDF/DOCX/MD │
└─────────────┘
```

### 6.2 各阶段数据格式

#### 阶段 1：查询输入

```python
{
    "query": "人工智能对教育的影响",
    "report_type": "research_report",
    "report_source": "web",
    "tone": "Objective",
    "language": "chinese"
}
```

#### 阶段 2：子查询生成

```python
[
    "AI在课堂教学中的应用",
    "AI辅助个性化学习",
    "AI对教师角色的影响",
    "AI教育工具的优缺点"
]
```

#### 阶段 3：检索结果

```python
[
    {"url": "https://...", "title": "...", "snippet": "..."},
    {"url": "https://...", "title": "...", "snippet": "..."},
    ...
]
```

#### 阶段 4：抓取结果

```python
[
    {
        "url": "https://...",
        "raw_content": "完整网页文本内容...",
        "image_urls": ["https://..."],
        "title": "页面标题"
    },
    ...
]
```

#### 阶段 5：压缩后上下文

```python
[
    "与查询最相关的文本片段1...",
    "与查询最相关的文本片段2...",
    ...
]
```

#### 阶段 6：最终报告

```markdown
# 报告标题

## 目录
- 章节1
- 章节2
...

## 引言
...

## 正文
...

## 结论
...

## 参考文献
1. [来源标题](URL)
...
```

### 6.3 WebSocket 实时流式数据

```python
# 进度日志
{"type": "logs", "content": "正在搜索...", "output": "..."}

# 报告内容（逐段）
{"type": "report", "output": "## 章节标题\n内容..."}

# 文件路径（完成时）
{"type": "path", "output": {"pdf": "outputs/xxx.pdf", "docx": "outputs/xxx.docx"}}

# 费用统计
{"type": "cost", "data": {"total_cost": 0.15, "model": "gpt-4.1"}}
```

---

## 7. 项目可扩展点

### 7.1 扩展点一览

| 扩展点 | 位置 | 扩展方式 | 难度 |
|--------|------|---------|------|
| **新增 LLM 提供商** | `gpt_researcher/llm_provider/generic/base.py` | 在 `_get_provider()` 中添加新 provider 映射 | 低 |
| **新增搜索检索器** | `gpt_researcher/retrievers/` | 创建新目录，实现 `search(query, max_results)` 方法，注册到 `__init__.py` | 低 |
| **新增网页抓取器** | `gpt_researcher/scraper/` | 创建新目录，实现 `scrape(url)` 方法，注册到 `__init__.py` | 低 |
| **新增报告类型** | `backend/report_type/` | 创建新目录，实现报告生成逻辑 | 中 |
| **自定义提示词族** | `gpt_researcher/prompts.py` | 继承 `PromptFamily` 类，覆盖目标方法 | 中 |
| **新增 Agent 角色** | `multi_agents/agents/` | 创建新 Agent 文件，注册到 LangGraph 工作流 | 中 |
| **修改工作流拓扑** | `multi_agents/agents/orchestrator.py` | 修改 `_create_workflow()` 中的节点和边 | 中 |
| **新增输出格式** | `backend/utils.py` | 添加新的格式转换函数（如 HTML, PPT） | 低 |
| **新增 Embedding 提供商** | `gpt_researcher/memory/embeddings.py` | 在 `Memory` 类中添加新 provider 分支 | 低 |
| **MCP 工具集成** | `gpt_researcher/mcp/` | 通过 MCP 协议接入外部工具和数据源 | 中 |
| **新增 Skill** | `gpt_researcher/skills/` | 创建新 Skill 类，在 `agent.py` 中注册 | 中 |
| **自定义向量存储** | `gpt_researcher/vector_store/` | 替换或扩展向量存储后端 | 低 |

### 7.2 扩展示例：添加新检索器

```python
# 1. 创建文件: gpt_researcher/retrievers/my_engine/my_engine.py
class MyEngineSearch:
    def __init__(self, query: str):
        self.query = query

    async def search(self, max_results: int = 5) -> list:
        # 返回 [{"url": ..., "title": ..., "snippet": ...}]
        ...

# 2. 注册到: gpt_researcher/retrievers/__init__.py
retriever_mapping = {
    ...
    "my_engine": MyEngineSearch,
}

# 3. 配置使用: .env
RETRIEVER=my_engine
```

### 7.3 扩展示例：添加新 Agent

```python
# 1. 创建文件: multi_agents/agents/my_agent.py
class MyAgent:
    def __init__(self, ...):
        ...

    async def run(self, state: ResearchState) -> dict:
        # 处理状态，返回状态更新
        return {"my_field": result}

# 2. 在 orchestrator.py 中注册:
workflow.add_node("my_agent", my_agent.run)
workflow.add_edge("writer", "my_agent")
workflow.add_edge("my_agent", "publisher")
```

---

## 8. 改造为"需求评审与交付计划系统"—— 完整方案

### 8.1 哪些 Agent 可以复用？

逐个对照原系统 Agent，分析其在新系统中的可复用性：

| 原 Agent | 原职责 | 新系统中的角色 | 复用方式 | 改动量 |
|----------|--------|--------------|---------|-------|
| **ChiefEditorAgent** | 构建 StateGraph、初始化 Agent、触发执行 | **项目调度器** | **直接复用框架**，替换节点和边定义 | 改 `_create_workflow()` 和 `_initialize_agents()` |
| **ReviewerAgent** | 对标 guidelines 审查草稿 | **评审委员会** | **高度复用**，改提示词即可：将"文章审查标准"换为"需求评审标准" | 仅改提示词 |
| **ReviserAgent** | 根据审查意见修改草稿 | **需求修改者** | **高度复用**，改提示词：将"修改文章"换为"修改需求拆解" | 仅改提示词 |
| **HumanAgent** | WebSocket/控制台人工反馈 | **人工审批节点** | **原样复用**，零改动 | 无 |
| **PublisherAgent** | Markdown 拼装 + PDF/DOCX 导出 | **交付计划导出器** | **高度复用**，改 `generate_layout()` 的模板结构 | 改模板 |
| **WriterAgent** | 写引言、结论、汇编目录 | **报告汇编器** | **部分复用**，改提示词：将"研究报告"换为"交付计划总结" | 改提示词 + 输出结构 |
| **EditorAgent** | 规划大纲 + 并行调度子图 | 不直接对应 | **复用并行调度机制**（`asyncio.gather` + 子图模式），但规划逻辑需重写 | 大改 |
| **ResearchAgent** | 调用 GPTResearcher 搜索+抓取 | 不复用 | **删除**，新系统不需要网络搜索 | — |

**复用总结**：

```
可原样复用:    HumanAgent（零改动）
改提示词复用:  ReviewerAgent, ReviserAgent, WriterAgent, PublisherAgent
复用框架:      ChiefEditorAgent（改工作流定义）, EditorAgent（复用并行调度机制）
不复用:        ResearchAgent（删除）
```

### 8.2 哪些 Agent 需要新增？

| 新 Agent | 对应图节点 | 职责 | 类比原系统 |
|----------|-----------|------|-----------|
| **RequirementAnalyst** | `analyst` | 将原始 PRD/用户故事拆解为结构化子需求，标注优先级和验收标准 | 替代原 `browser` 节点（初步研究 → 初步分析） |
| **ArchitectAgent** | `architect` | 技术可行性评估、架构方案建议、依赖关系分析 | 全新，无对应 |
| **TestExpertAgent** | `test_expert` | 制定测试策略、规划测试用例、自动化建议 | 全新，无对应 |
| **ProjectManagerAgent** | `pm` | 排期估算、资源分配、里程碑规划 | 替代原 `writer` 节点（汇编 → 规划） |
| **RiskAssessorAgent** | `risk` | 风险识别、影响分析、应对措施 | 全新，无对应 |
| **ConflictArbitrator** | `arbitrator` | 仲裁 Agent 间的冲突意见 | 全新，原系统缺失此机制 |

### 8.3 哪些逻辑可以删除？

#### 8.3.1 可完全移除的模块

| 模块 | 文件/目录 | 删除原因 |
|------|----------|---------|
| **搜索引擎检索器** | `gpt_researcher/retrievers/` (14 个子目录) | 新系统输入是 PRD 文档，不做网络搜索 |
| **网页抓取器** | `gpt_researcher/scraper/` (8 个子目录) | 不需要抓取网页内容 |
| **上下文压缩** | `gpt_researcher/context/compression.py` | 不需要 Embedding 相似度过滤 |
| **向量存储** | `gpt_researcher/vector_store/` | 不需要向量检索（除非做需求知识库） |
| **MCP 协议** | `gpt_researcher/mcp/` | 不需要外部工具协议 |
| **深度研究技能** | `gpt_researcher/skills/deep_research.py` | 不需要递归研究 |
| **图片生成** | `gpt_researcher/skills/image_generator.py` | 交付计划不需要配图 |
| **ResearchAgent** | `multi_agents/agents/researcher.py` | 不需要网络研究 |
| **GPTResearcher 核心** | `gpt_researcher/agent.py` 的 `conduct_research()` | 整个搜索-抓取-压缩管线不需要 |

#### 8.3.2 可移除的逻辑流程

| 逻辑 | 位置 | 原因 |
|------|------|------|
| `choose_agent()` | `actions/agent_creator.py` | 新系统 Agent 角色固定，不需要 LLM 动态选择 |
| `_get_context_by_web_search()` | `skills/researcher.py` | 整个搜索→抓取→压缩管线 |
| `_scrape_data_by_urls()` | `skills/researcher.py` | 网页抓取 |
| `plan_research_outline()` | `actions/query_processing.py` | 研究大纲规划 → 替换为需求拆解 |
| `curate_sources()` | `skills/curator.py` | 源可信度排序 |
| 所有 `BasicReport` / `DetailedReport` | `backend/report_type/` | 替换为新的报告类型 |

#### 8.3.3 保留但不引用（安全策略）

建议不物理删除以上模块，而是**创建新的入口文件，不 import 这些模块**。这样：
- 保持原项目完整性，方便对照学习
- 避免误删导致的依赖断裂
- 可随时切换回原系统做对比测试

### 8.4 哪些 Prompt 需要重写？

#### 8.4.1 需要重写的 Prompt 完整清单

| # | 原 Prompt | 原用途 | 新 Prompt | 新用途 |
|---|----------|--------|----------|--------|
| 1 | Editor 规划提示词 | 将初步研究拆分为章节大纲 | **需求拆解提示词** | 将 PRD 拆分为结构化子需求 |
| 2 | Reviewer 审查提示词 | 对标 guidelines 审查文章 | **需求评审提示词** | 对标评审标准审查需求质量 |
| 3 | Reviser 修改提示词 | 根据审查意见修改文章 | **需求修改提示词** | 根据评审意见修改需求拆解 |
| 4 | Writer 写作提示词 | 写引言、结论、汇编目录 | **计划汇编提示词** | 汇编交付计划总结 |
| 5 | — | — | **架构评估提示词（新增）** | 技术可行性评估 |
| 6 | — | — | **测试规划提示词（新增）** | 制定测试策略 |
| 7 | — | — | **排期估算提示词（新增）** | 排期和资源规划 |
| 8 | — | — | **风险评估提示词（新增）** | 风险识别与应对 |
| 9 | — | — | **冲突仲裁提示词（新增）** | 仲裁 Agent 间的分歧 |

#### 8.4.2 核心 Prompt 设计

**Prompt 1：需求拆解（RequirementAnalyst）**

```python
REQUIREMENT_ANALYST_SYSTEM = """You are a senior requirement analyst.
Your goal is to decompose a raw PRD or user story into structured, actionable sub-requirements.
You must identify ambiguities, missing acceptance criteria, and implicit dependencies."""

REQUIREMENT_ANALYST_USER = """Today's date is {date}.
Team info: {team_info}
Constraints: {constraints}

Raw requirement document:
{raw_requirement}

{human_feedback_instruction}

Your task:
1. Decompose into sub-requirements (max {max_requirements})
2. For each sub-requirement, provide: id, title, description, priority (P0/P1/P2), acceptance_criteria, dependencies
3. Flag any ambiguities or missing information

You MUST return a JSON:
{{
  "parsed_requirements": [
    {{
      "id": "REQ-001",
      "title": "string",
      "description": "string",
      "priority": "P0|P1|P2",
      "acceptance_criteria": ["criterion1", "criterion2"],
      "dependencies": ["REQ-002"],
      "ambiguities": ["unclear point 1"]
    }}
  ],
  "overall_notes": "string"
}}"""
```

**Prompt 2：需求评审（ReviewBoard，改造自 ReviewerAgent）**

```python
REVIEW_BOARD_SYSTEM = """You are an expert requirement review board consisting of a product manager,
a tech lead, and a QA lead. Your goal is to evaluate requirement quality from three dimensions:
completeness, feasibility, and testability."""

REVIEW_BOARD_USER = """Review the following requirement analysis against these criteria:

Evaluation criteria:
- Completeness: Are all acceptance criteria clearly defined? Are edge cases covered?
- Feasibility: Is the technical assessment realistic? Are effort estimates reasonable?
- Testability: Can each requirement be verified? Are test strategies adequate?
- Consistency: Do any requirements contradict each other?
- Risk: Are high-risk items identified and mitigated?

{revision_prompt_if_applicable}

Requirements: {parsed_requirements}
Technical Assessment: {technical_assessment}
Test Strategy: {test_strategy}

If ALL criteria are met, return None.
If issues exist, return structured feedback:
{{
  "verdict": "revise",
  "issues": [
    {{"requirement_id": "REQ-001", "dimension": "completeness", "severity": "critical|major|minor", "description": "..."}},
  ],
  "summary": "Overall review summary"
}}"""
```

**Prompt 3：架构评估（ArchitectAgent，全新）**

```python
ARCHITECT_SYSTEM = """You are a senior software architect.
Your goal is to evaluate technical feasibility, propose architecture decisions,
and identify technical risks and dependencies."""

ARCHITECT_USER = """Based on the following parsed requirements, provide a technical assessment:

Requirements: {parsed_requirements}
Team capabilities: {team_info}
Technical constraints: {constraints}

You MUST return a JSON:
{{
  "feasibility": "feasible|partially_feasible|infeasible",
  "architecture_notes": "High-level architecture approach",
  "tech_stack": ["technology1", "technology2"],
  "effort_estimates": [
    {{"requirement_id": "REQ-001", "estimated_days": 5, "complexity": "high|medium|low", "rationale": "..."}}
  ],
  "dependencies": [
    {{"from": "REQ-001", "to": "REQ-003", "type": "blocks|relates_to", "description": "..."}}
  ],
  "technical_risks": [
    {{"risk": "description", "impact": "high|medium|low", "mitigation": "..."}}
  ]
}}"""
```

**Prompt 4：风险评估（RiskAssessorAgent，全新）**

```python
RISK_ASSESSOR_SYSTEM = """You are a project risk management expert.
Your goal is to identify, assess, and propose mitigations for all project risks
including technical, schedule, resource, and external risks."""

RISK_ASSESSOR_USER = """Based on all available project data, conduct a comprehensive risk assessment:

Requirements: {parsed_requirements}
Technical Assessment: {technical_assessment}
Delivery Plan: {delivery_plan}
Team: {team_info}
Constraints: {constraints}

You MUST return a JSON:
{{
  "risks": [
    {{
      "id": "RISK-001",
      "category": "technical|schedule|resource|external|requirement",
      "description": "Risk description",
      "probability": "high|medium|low",
      "impact": "high|medium|low",
      "risk_score": 9,
      "affected_requirements": ["REQ-001"],
      "mitigation": "Mitigation strategy",
      "contingency": "Contingency plan if risk materializes",
      "owner": "Role responsible"
    }}
  ],
  "overall_risk_level": "high|medium|low",
  "risk_summary": "Executive summary of risk posture"
}}"""
```

**Prompt 5：冲突仲裁（ConflictArbitrator，全新）**

```python
ARBITRATOR_SYSTEM = """You are a senior project arbitrator.
When different agents produce conflicting assessments, you must analyze both positions,
weigh the evidence, and produce a final binding decision with clear rationale."""

ARBITRATOR_USER = """The following conflicts were detected between agent outputs:

Conflicts:
{conflicts}

Context:
- Requirements: {parsed_requirements}
- Team: {team_info}
- Constraints: {constraints}

For each conflict, you MUST:
1. Summarize both positions
2. Analyze the trade-offs
3. Make a final decision
4. Provide rationale

Return a JSON:
{{
  "resolutions": [
    {{
      "conflict_id": "CONFLICT-001",
      "description": "What the conflict is about",
      "position_a": "Agent A's position",
      "position_b": "Agent B's position",
      "decision": "The final decision",
      "rationale": "Why this decision was made",
      "affected_fields": ["field_to_update"]
    }}
  ]
}}"""
```

### 8.5 哪些地方需要加入结构化 JSON 输出？

原系统中，只有部分 Agent 使用 JSON 输出（Editor、Reviser、Writer），其余返回自由文本。新系统**所有 Agent 都必须返回结构化 JSON**，原因：

1. 下游 Agent 需要精确解析上游输出的特定字段
2. 冲突检测需要对比结构化数据
3. 最终文档拼装需要可靠的数据结构

#### 所有 Agent 的输出格式规范

| Agent | 输出字段 | JSON Schema 关键字段 |
|-------|---------|---------------------|
| **RequirementAnalyst** | `parsed_requirements` | `[{id, title, description, priority, acceptance_criteria, dependencies, ambiguities}]` |
| **ArchitectAgent** | `technical_assessment` | `{feasibility, architecture_notes, tech_stack, effort_estimates[], dependencies[], technical_risks[]}` |
| **TestExpertAgent** | `test_strategy` | `{approach, test_cases[{req_id, cases[], automation_feasibility}], coverage_targets}` |
| **ReviewBoard** | `review_feedback` | `{verdict, issues[{req_id, dimension, severity, description}], summary}` 或 `None` |
| **ReviserAgent** | `parsed_requirements`（修改版） | 与 RequirementAnalyst 相同格式 + `revision_notes` |
| **ProjectManagerAgent** | `delivery_plan`, `milestones` | `{sprints[], resource_allocation, timeline}`, `[{name, date, deliverables}]` |
| **RiskAssessorAgent** | `risk_assessment` | `[{id, category, description, probability, impact, risk_score, mitigation, contingency}]` |
| **ConflictArbitrator** | 修改冲突字段 | `{resolutions[{conflict_id, decision, rationale, affected_fields}]}` |
| **PublisherAgent** | `final_document` | Markdown 字符串（非 JSON，但由结构化数据拼装） |

#### 实现方式：复用现有 `call_model` 的 `response_format="json"` 机制

```python
# multi_agents/agents/utils/llms.py 已有的 JSON 解析逻辑，直接复用
async def call_model(prompt, model, response_format=None):
    response = await create_chat_completion(model=model, messages=lc_messages, temperature=0, ...)
    if response_format == "json":
        return parse_json_markdown(response, parser=json_repair.loads)  # 自动容错修复
    return response
```

所有新 Agent 调用时统一使用 `response_format="json"`：

```python
result = await call_model(prompt=prompt, model=task.get("model"), response_format="json")
```

### 8.6 如何加入风险评审 Agent？

#### 8.6.1 Agent 实现

```python
# multi_agents/agents/risk_assessor.py

from .utils.views import print_agent_output
from .utils.llms import call_model

RISK_SYSTEM_PROMPT = """You are a project risk management expert.
Your goal is to identify, assess, and propose mitigations for all project risks
including technical, schedule, resource, and external risks."""


class RiskAssessorAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def assess_risks(self, state: dict) -> dict:
        task = state.get("task")
        prompt = [
            {"role": "system", "content": RISK_SYSTEM_PROMPT},
            {"role": "user", "content": f"""Based on all available project data, conduct a comprehensive risk assessment:

Requirements: {state.get("parsed_requirements")}
Technical Assessment: {state.get("technical_assessment")}
Delivery Plan: {state.get("delivery_plan")}
Team: {task.get("team_info")}
Constraints: {task.get("constraints")}

Return a JSON with fields: risks (array), overall_risk_level, risk_summary."""},
        ]

        print_agent_output("Assessing project risks...", agent="RISK_ASSESSOR")
        result = await call_model(prompt, model=task.get("model"), response_format="json")

        return {
            "risk_assessment": result.get("risks", []),
            "overall_risk_level": result.get("overall_risk_level", "unknown"),
        }

    async def run(self, state: dict) -> dict:
        if self.websocket and self.stream_output:
            await self.stream_output("logs", "risk_assessment",
                "Conducting comprehensive risk assessment...", self.websocket)
        return await self.assess_risks(state)
```

#### 8.6.2 注册到工作流

```python
# orchestrator.py 中注册
workflow.add_node("risk", agents["risk"].run)
workflow.add_edge("pm", "risk")        # 项目经理之后执行
workflow.add_edge("risk", "publisher")  # 风险评估之后发布
```

#### 8.6.3 风险评估的输入来源

```
RequirementAnalyst → parsed_requirements ──┐
ArchitectAgent     → technical_assessment ──┼──► RiskAssessorAgent
ProjectManager     → delivery_plan ─────────┤
task.json          → team_info, constraints ┘
```

风险评估是**汇聚节点**，读取前面所有 Agent 的输出，因此必须放在工作流后段。

### 8.7 如何加入冲突仲裁机制？

原系统**没有冲突仲裁**（因为 Agent 写入字段互不重叠）。新系统中，多个 Agent 可能对同一需求产生矛盾判断，因此需要仲裁。

#### 8.7.1 可能的冲突场景

| 冲突类型 | Agent A 判断 | Agent B 判断 | 示例 |
|---------|-------------|-------------|------|
| **工期冲突** | 架构师估算 REQ-001 需 10 天 | 项目经理安排 3 天完成 | 技术复杂度 vs 交付压力 |
| **优先级冲突** | 需求分析师标记 P2 | 风险评估标记为高风险（应提升优先级） | 业务优先级 vs 技术风险 |
| **可行性冲突** | 架构师标记"可行" | 测试专家标记"无法自动化测试" | 开发可行性 vs 测试可行性 |
| **资源冲突** | 项目经理分配了 A 做 REQ-001 | 项目经理也分配 A 做 REQ-003（时间重叠） | 资源分配冲突 |

#### 8.7.2 冲突检测机制

在工作流中加入**冲突检测函数**（非 LLM 调用，纯逻辑判断）：

```python
def detect_conflicts(state: dict) -> list:
    """检测 Agent 输出之间的冲突，返回冲突列表"""
    conflicts = []

    parsed_reqs = state.get("parsed_requirements", [])
    tech_assessment = state.get("technical_assessment", {})
    delivery_plan = state.get("delivery_plan", {})
    risk_assessment = state.get("risk_assessment", [])

    # 冲突1：工期估算 vs 排期安排
    effort_estimates = {e["requirement_id"]: e["estimated_days"]
                        for e in tech_assessment.get("effort_estimates", [])}
    for sprint in delivery_plan.get("sprints", []):
        for req_id in sprint.get("requirement_ids", []):
            estimated = effort_estimates.get(req_id)
            allocated = sprint.get("duration_days")
            if estimated and allocated and estimated > allocated * 1.5:
                conflicts.append({
                    "id": f"CONFLICT-{len(conflicts)+1}",
                    "type": "effort_vs_schedule",
                    "requirement_id": req_id,
                    "position_a": f"Architect estimates {estimated} days",
                    "position_b": f"PM allocated {allocated} days in sprint",
                })

    # 冲突2：高风险需求优先级过低
    high_risk_reqs = {r["affected_requirements"][0]
                      for r in risk_assessment if r.get("impact") == "high"}
    for req in parsed_reqs:
        if req["id"] in high_risk_reqs and req.get("priority") == "P2":
            conflicts.append({
                "id": f"CONFLICT-{len(conflicts)+1}",
                "type": "priority_vs_risk",
                "requirement_id": req["id"],
                "position_a": f"Analyst marked as P2 (low priority)",
                "position_b": f"Risk assessor flagged as high impact",
            })

    # 冲突3：可行性不一致
    feasibility = tech_assessment.get("feasibility")
    test_blockers = [tc for tc in state.get("test_strategy", {}).get("test_cases", [])
                     if tc.get("automation_feasibility") == "infeasible"]
    if feasibility == "feasible" and len(test_blockers) > 3:
        conflicts.append({
            "id": f"CONFLICT-{len(conflicts)+1}",
            "type": "dev_feasibility_vs_test_feasibility",
            "position_a": "Architect marked as feasible",
            "position_b": f"{len(test_blockers)} requirements cannot be auto-tested",
        })

    return conflicts
```

#### 8.7.3 仲裁 Agent 实现

```python
# multi_agents/agents/arbitrator.py

class ConflictArbitrator:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def run(self, state: dict) -> dict:
        conflicts = detect_conflicts(state)

        if not conflicts:
            print_agent_output("No conflicts detected.", agent="ARBITRATOR")
            return {}  # 无冲突，不修改状态

        print_agent_output(f"Detected {len(conflicts)} conflicts, arbitrating...", agent="ARBITRATOR")

        prompt = [
            {"role": "system", "content": ARBITRATOR_SYSTEM},
            {"role": "user", "content": f"""Conflicts: {json.dumps(conflicts)}
Requirements: {state.get("parsed_requirements")}
Team: {state.get("task", {}).get("team_info")}
Constraints: {state.get("task", {}).get("constraints")}

For each conflict, make a binding decision and explain your rationale.
Return JSON with 'resolutions' array."""},
        ]

        result = await call_model(prompt, model=state.get("task", {}).get("model"), response_format="json")

        # 应用仲裁结果：根据 resolutions 修改状态字段
        state_updates = self._apply_resolutions(state, result.get("resolutions", []))
        state_updates["arbitration_log"] = result.get("resolutions", [])
        return state_updates

    def _apply_resolutions(self, state, resolutions):
        """根据仲裁决定修改相关状态字段"""
        updates = {}
        for resolution in resolutions:
            # 示例：如果仲裁决定提升优先级
            if resolution.get("conflict_id") and "priority" in str(resolution.get("decision", "")):
                # 更新 parsed_requirements 中对应需求的优先级
                updated_reqs = state.get("parsed_requirements", []).copy()
                req_id = resolution.get("requirement_id")
                for req in updated_reqs:
                    if req.get("id") == req_id:
                        req["priority"] = "P0"  # 或从 decision 中解析
                        req["priority_rationale"] = resolution.get("rationale")
                updates["parsed_requirements"] = updated_reqs
        return updates
```

#### 8.7.4 在工作流中的位置

冲突仲裁放在**风险评估之后、最终发布之前**：

```python
workflow.add_node("arbitrator", agents["arbitrator"].run)
workflow.add_edge("risk", "arbitrator")

# 条件路由：有冲突则仲裁后再到 publisher，无冲突直接到 publisher
workflow.add_conditional_edges(
    "arbitrator",
    lambda state: "has_conflicts" if state.get("arbitration_log") else "no_conflicts",
    {"has_conflicts": "publisher", "no_conflicts": "publisher"}
)
workflow.add_edge("publisher", END)
```

### 8.8 新状态定义

```python
from typing import TypedDict, List, Optional

class RequirementState(TypedDict):
    # ========= 输入 =========
    task: dict                          # 原始需求输入
    # task 内含:
    #   query: str              → 需求标题/摘要
    #   raw_requirement: str    → PRD 全文或用户故事
    #   team_info: dict         → {size, skills, availability}
    #   constraints: dict       → {deadline, budget, tech_constraints}
    #   model: str              → LLM 模型名
    #   guidelines: list        → 评审标准列表
    #   follow_guidelines: bool → 是否启用评审
    #   include_human_feedback: bool → 是否启用人工审批
    #   max_requirements: int   → 最大子需求数
    #   publish_formats: dict   → {markdown, pdf, docx}

    # ========= 需求分析阶段 =========
    parsed_requirements: List[dict]     # 拆解后的子需求
    # 每项: {id, title, description, priority, acceptance_criteria, dependencies, ambiguities}

    # ========= 评估阶段 =========
    technical_assessment: dict          # 架构师的技术评估
    # {feasibility, architecture_notes, tech_stack, effort_estimates[], dependencies[], technical_risks[]}

    test_strategy: dict                 # 测试专家的测试策略
    # {approach, test_cases[], coverage_targets, automation_plan}

    # ========= 评审阶段 =========
    review_feedback: Optional[str]      # 评审意见（None = 通过）
    human_feedback: Optional[str]       # 人工审批意见（None = 通过）
    revision_notes: str                 # 修改说明

    # ========= 规划阶段 =========
    delivery_plan: dict                 # 交付排期计划
    # {sprints[], resource_allocation, timeline, critical_path}

    milestones: List[dict]              # 里程碑定义
    # 每项: {name, date, deliverables, success_criteria}

    # ========= 风险与仲裁阶段 =========
    risk_assessment: List[dict]         # 风险评估清单
    # 每项: {id, category, description, probability, impact, risk_score, mitigation, contingency, owner}

    overall_risk_level: str             # 整体风险等级
    arbitration_log: List[dict]         # 仲裁记录
    # 每项: {conflict_id, description, decision, rationale}

    # ========= 输出 =========
    final_document: str                 # 最终交付计划文档（Markdown）
```

### 8.9 新工作流完整设计

#### 8.9.1 主工作流（LangGraph StateGraph）

```python
def _create_workflow(self, agents):
    workflow = StateGraph(RequirementState)

    # 节点注册
    workflow.add_node("analyst",    agents["analyst"].run)       # 需求分析
    workflow.add_node("architect",  agents["architect"].run)     # 架构评估
    workflow.add_node("test_expert",agents["test_expert"].run)   # 测试规划
    workflow.add_node("reviewer",   agents["reviewer"].run)      # 评审
    workflow.add_node("reviser",    agents["reviser"].run)       # 修改
    workflow.add_node("human",      agents["human"].review_plan) # 人工审批
    workflow.add_node("pm",         agents["pm"].run)            # 排期规划
    workflow.add_node("risk",       agents["risk"].run)          # 风险评估
    workflow.add_node("arbitrator", agents["arbitrator"].run)    # 冲突仲裁
    workflow.add_node("publisher",  agents["publisher"].run)     # 导出发布

    # 边定义
    workflow.set_entry_point("analyst")

    # 阶段一：分析链（串行）
    workflow.add_edge("analyst",     "architect")
    workflow.add_edge("architect",   "test_expert")

    # 阶段二：评审循环
    workflow.add_edge("test_expert", "reviewer")
    workflow.add_conditional_edges("reviewer",
        lambda s: "accept" if s.get("review_feedback") is None else "revise",
        {"accept": "human", "revise": "reviser"}
    )
    workflow.add_edge("reviser", "reviewer")   # 修改后重新评审

    # 阶段三：人工审批
    workflow.add_conditional_edges("human",
        lambda s: "accept" if s.get("human_feedback") is None else "revise",
        {"accept": "pm", "revise": "analyst"}  # 驳回则回到需求分析重做
    )

    # 阶段四：规划链（串行）
    workflow.add_edge("pm",          "risk")
    workflow.add_edge("risk",        "arbitrator")
    workflow.add_edge("arbitrator",  "publisher")
    workflow.add_edge("publisher",   END)

    return workflow
```

#### 8.9.2 工作流拓扑图

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                     需求评审与交付计划系统 — 主工作流                          ║
║                     状态对象: RequirementState                               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  阶段一：需求分析链（串行）                                                     ║
║  ┌──────────┐    ┌──────────┐    ┌──────────┐                               ║
║  │ Analyst  │───▶│Architect │───▶│  Test    │                               ║
║  │ 需求拆解  │    │ 架构评估  │    │  Expert  │                               ║
║  │          │    │          │    │ 测试规划  │                               ║
║  └──────────┘    └──────────┘    └────┬─────┘                               ║
║       ▲                               │                                      ║
║       │                               ▼                                      ║
║  阶段二│：评审循环              ┌──────────┐                                   ║
║       │                       │ Reviewer │                                   ║
║       │                       │  评审    │                                   ║
║       │                       └──┬───┬──┘                                   ║
║       │                        通过  驳回                                     ║
║       │                         │    ▼                                       ║
║       │                         │  ┌──────────┐                              ║
║       │                         │  │ Reviser  │                              ║
║       │                         │  │  修改    │──► Reviewer（循环）            ║
║       │                         │  └──────────┘                              ║
║       │                         ▼                                            ║
║  阶段三│：人工审批       ┌──────────┐                                         ║
║       │               │  Human   │                                          ║
║       │               │ 人工审批  │                                          ║
║       │               └──┬───┬──┘                                           ║
║       │                通过  驳回                                             ║
║       └────────────────────┘ │                                              ║
║                              ▼                                               ║
║  阶段四：规划链（串行）                                                         ║
║  ┌──────────┐    ┌──────────┐    ┌───────────┐    ┌──────────┐              ║
║  │   PM     │───▶│  Risk    │───▶│Arbitrator │───▶│Publisher │───▶ END      ║
║  │ 排期规划  │    │ 风险评估  │    │ 冲突仲裁   │    │ 导出发布  │              ║
║  └──────────┘    └──────────┘    └───────────┘    └──────────┘              ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

**精简文字版**：

```
Analyst ──▶ Architect ──▶ TestExpert ──▶ Reviewer ──条件──┬──▶ Human ──条件──┬──▶ PM ──▶ Risk ──▶ Arbitrator ──▶ Publisher ──▶ END
                                           ▲              │        ▲         │
                                           └── Reviser ◀──┘        └─ Analyst ◀┘
                                              (驳回循环)              (驳回重做)
```

#### 8.9.3 与原系统的对应关系

| 原系统节点 | 新系统节点 | 映射关系 |
|-----------|-----------|---------|
| `browser` (ResearchAgent) | `analyst` (RequirementAnalyst) | 初步研究 → 需求拆解 |
| `planner` (EditorAgent) | `architect` + `test_expert` | 规划大纲 → 技术评估 + 测试规划 |
| `human` (HumanAgent) | `human` (HumanAgent) | 原样复用 |
| `researcher` (EditorAgent 并行) | 无对应 | 删除（不需要并行子图研究） |
| Reviewer→Reviser 子图循环 | `reviewer` → `reviser` 主图循环 | 从子图提升到主图 |
| `writer` (WriterAgent) | `pm` (ProjectManagerAgent) | 写报告 → 排期规划 |
| `publisher` (PublisherAgent) | `publisher` (PublisherAgent) | 复用，改模板 |
| 无 | `risk` (RiskAssessorAgent) | 全新节点 |
| 无 | `arbitrator` (ConflictArbitrator) | 全新节点 |

### 8.10 任务配置文件改造

**原 `task.json`**：

```json
{
  "query": "Is AI in a hype cycle?",
  "max_sections": 3,
  "publish_formats": {"markdown": true, "pdf": true, "docx": true},
  "include_human_feedback": false,
  "follow_guidelines": false,
  "model": "gpt-4o",
  "guidelines": [],
  "verbose": true
}
```

**新 `task.json`**：

```json
{
  "query": "用户管理模块 v2.0 需求评审",
  "raw_requirement": "## 用户管理模块 v2.0\n\n### 背景\n当前用户模块不支持...\n\n### 需求列表\n1. 支持第三方登录...\n2. 用户角色权限管理...",
  "team_info": {
    "size": 5,
    "skills": ["Java", "React", "PostgreSQL"],
    "availability": "3 developers full-time, 1 QA, 1 PM part-time",
    "velocity": "20 story points per sprint"
  },
  "constraints": {
    "deadline": "2026-04-30",
    "budget": "不超过 3 个 sprint",
    "tech_constraints": ["必须兼容现有 Spring Boot 架构", "不引入新数据库"]
  },
  "max_requirements": 10,
  "model": "gpt-4o",
  "guidelines": [
    "每个需求必须有明确的验收标准",
    "P0 需求必须有自动化测试方案",
    "工期估算偏差不超过 30%",
    "高风险项必须有应对措施"
  ],
  "follow_guidelines": true,
  "include_human_feedback": true,
  "publish_formats": {"markdown": true, "pdf": true, "docx": true},
  "verbose": true
}
```

### 8.11 可删除逻辑与保留逻辑汇总

```
保留（零改动）:
  ├── gpt_researcher/llm_provider/      # LLM 调用基础设施
  ├── gpt_researcher/config/            # 配置管理
  ├── gpt_researcher/utils/costs.py     # 费用追踪
  ├── gpt_researcher/utils/llm.py       # create_chat_completion
  ├── backend/server/app.py             # FastAPI 框架
  ├── backend/server/websocket_manager.py # WebSocket 管理
  ├── backend/utils.py                  # PDF/DOCX/MD 转换
  ├── multi_agents/agents/human.py      # 人工审批节点
  └── multi_agents/agents/utils/llms.py # call_model 工具函数

保留（改提示词/模板）:
  ├── multi_agents/agents/reviewer.py   # 改提示词：文章审查 → 需求评审
  ├── multi_agents/agents/reviser.py    # 改提示词：修改文章 → 修改需求
  ├── multi_agents/agents/writer.py     # 改提示词：写报告 → 汇编计划（改为 PM）
  └── multi_agents/agents/publisher.py  # 改 generate_layout() 模板

重写:
  ├── multi_agents/agents/orchestrator.py  # 重写工作流定义
  ├── multi_agents/memory/research.py      # 重写为 RequirementState
  └── multi_agents/task.json               # 重写任务配置

新增:
  ├── multi_agents/agents/analyst.py       # 需求分析师 Agent
  ├── multi_agents/agents/architect.py     # 架构师 Agent
  ├── multi_agents/agents/test_expert.py   # 测试专家 Agent
  ├── multi_agents/agents/pm.py            # 项目经理 Agent
  ├── multi_agents/agents/risk_assessor.py # 风险评估 Agent
  └── multi_agents/agents/arbitrator.py    # 冲突仲裁 Agent

不引用（安全移除）:
  ├── gpt_researcher/retrievers/        # 搜索引擎
  ├── gpt_researcher/scraper/           # 网页抓取
  ├── gpt_researcher/context/           # 上下文压缩
  ├── gpt_researcher/vector_store/      # 向量存储
  ├── gpt_researcher/mcp/               # MCP 协议
  ├── gpt_researcher/skills/deep_research.py
  ├── gpt_researcher/skills/researcher.py
  ├── gpt_researcher/skills/image_generator.py
  ├── multi_agents/agents/researcher.py # 研究 Agent
  └── backend/report_type/              # 原报告类型处理
```

### 8.12 改造工作量估算

| 工作项 | 估计工作量 | 说明 |
|--------|-----------|------|
| 新增 6 个 Agent（代码骨架） | **中（2-3天）** | 参考现有 Agent 结构，模式统一 |
| 编写 9 套 Prompt（核心工作） | **高（4-6天）** | 提示词质量直接决定系统质量，需多轮迭代 |
| 重写 orchestrator 工作流 | **中（1-2天）** | 复用 LangGraph 框架，改节点和边 |
| 实现冲突检测 + 仲裁机制 | **中（2-3天）** | 检测函数 + 仲裁 Agent + 状态更新 |
| 重写 RequirementState | **低（0.5天）** | TypedDict 改写 |
| 重写 task.json 配置 | **低（0.5天）** | 配置结构改写 |
| 改造 Publisher 模板 | **低（1天）** | 修改 `generate_layout()` 输出结构 |
| 适配后端 API | **中（1-2天）** | 新增/修改 API 端点 |
| 适配前端 UI | **中-高（3-5天）** | 需求输入表单、评审看板、甘特图、风险矩阵 |
| 端到端测试与提示词调优 | **中（3-4天）** | 全链路测试，迭代优化提示词 |
| **总计** | **约 18-27 天** | |

### 8.13 总结

**改造本质**：保留 LangGraph 多 Agent 调度骨架 + LLM 调用基础设施 + WebSocket 实时通信 + 文件导出系统，**替换上层业务逻辑**。

**与原系统的核心差异**：

| 维度 | 原系统（GPT Researcher） | 新系统（需求评审与交付计划） |
|------|------------------------|--------------------------|
| **输入** | 一句查询文本 | PRD 文档 + 团队信息 + 约束条件 |
| **数据来源** | 网络搜索 + 网页抓取 | 用户提供的需求文档（无外部搜索） |
| **Agent 职责** | 搜索、研究、写作 | 分析、评估、评审、规划、风险管理 |
| **核心循环** | Reviewer→Reviser（子图内，审文章质量） | Reviewer→Reviser（主图内，审需求质量） |
| **输出** | 研究报告（Markdown） | 交付计划（需求清单 + 技术方案 + 排期 + 风险） |
| **冲突处理** | 无（字段不重叠） | 有（冲突检测 + LLM 仲裁） |
| **结构化程度** | 部分 JSON | 全部 JSON（所有 Agent 输出） |

**一句话总结**：这是一次**"业务层换血、基础设施层零改动"的改造** —— 工作量集中在 Prompt 工程和新 Agent 开发上，LangGraph 调度、LLM 调用、WebSocket 通信、文件导出等基础设施完全复用。

---

## 9. 模块风险等级分类（复杂度 / 耦合度 / 可重构性）

> 本节对项目中所有核心模块进行风险评估，从**复杂度**、**耦合度**、**被依赖程度**三个维度综合打分，划分为四个风险等级。

### 9.1 评估维度说明

| 维度 | 含义 | 衡量方式 |
|------|------|----------|
| **代码复杂度** | 模块自身逻辑的复杂程度 | 代码行数、分支数量、异步嵌套深度、状态变量数量 |
| **耦合度（出向）** | 该模块依赖了多少其他模块 | import 数量，跨层调用数量 |
| **被依赖度（入向）** | 有多少其他模块依赖于它 | 反向 import 数量，改动后的影响面 |
| **循环依赖风险** | 是否存在或接近循环 import | 双向 import 链分析 |

### 9.2 总览矩阵

| 模块 | 代码行数 | 出向依赖 | 入向依赖 | 循环风险 | **风险等级** |
|------|---------|---------|---------|---------|-------------|
| `gpt_researcher/agent.py` | ~720 | ~20 个模块 | 10+ 文件 | 低 | **🔴 红色（禁区）** |
| `gpt_researcher/config/config.py` | ~311 | ~5 个模块 | **30+ 文件** | 低 | **🔴 红色（禁区）** |
| `gpt_researcher/prompts.py` | ~900 | ~5 个模块 | 20+ 文件 | 低 | **🟠 橙色（高危）** |
| `gpt_researcher/utils/llm.py` | ~200 | ~3 个模块 | 10+ 文件 | 低 | **🟠 橙色（高危）** |
| `gpt_researcher/skills/researcher.py` | ~990 | ~8 个模块 | ~3 文件 | 低 | **🟠 橙色（高危）** |
| `gpt_researcher/llm_provider/generic/base.py` | ~317 | ~10（动态） | ~5 文件 | 低 | **🟡 黄色（中危）** |
| `multi_agents/agents/orchestrator.py` | ~119 | ~8 个模块 | ~4 文件 | 中 | **🟡 黄色（中危）** |
| `backend/server/websocket_manager.py` | ~184 | ~8 个模块 | ~2 文件 | 中 | **🟡 黄色（中危）** |
| `backend/server/app.py` | ~454 | ~10 个模块 | ~2 文件 | 低 | **🟡 黄色（中危）** |
| `gpt_researcher/actions/*` | ~1027 | 各自独立 | 经 `__init__` 统一导出 | 低 | **🟢 绿色（安全）** |
| `gpt_researcher/retrievers/*` | 14 个检索器 | 各自独立 | 工厂模式注册 | 低 | **🟢 绿色（安全）** |
| `gpt_researcher/scraper/*` | 9 个抓取器 | 各自独立 | 工厂模式注册 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/researcher.py` | ~80 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/writer.py` | ~70 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/reviewer.py` | ~50 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/reviser.py` | ~50 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/publisher.py` | ~80 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |
| `multi_agents/agents/human.py` | ~40 | ~2 | ~2 | 低 | **🟢 绿色（安全）** |
| `backend/utils.py` | ~100 | ~3 | ~2 | 低 | **🟢 绿色（安全）** |

---

### 9.3 🔴 红色（禁区）—— 不建议轻易改动

#### 9.3.1 `gpt_researcher/agent.py`（GPTResearcher 主类）

**风险定性：项目的"心脏"，改一行可能全身瘫痪。**

| 指标 | 数据 |
|------|------|
| 代码行数 | ~720 行 |
| 出向依赖 | 20 个模块：Config、PromptFamily、GenericLLMProvider、Memory、ResearchConductor、ReportGenerator、BrowserManager、ContextManager、SourceCurator、DeepResearchSkill、ImageGenerator、VectorStoreWrapper、create_chat_completion 等 |
| 入向依赖 | 10+ 文件直接 import：backend 服务层、multi_agents 研究员、CLI、所有报告类型、测试文件 |
| 状态变量 | 30+ 实例属性（query、context、visited_urls、research_costs、agent、role 等） |

**为什么危险：**

```
backend/server/app.py
  └── websocket_manager.py
        └── BasicReport / DetailedReport
              └── GPTResearcher  ← 改这里
                    ├── skills/researcher.py（研究）
                    ├── skills/writer.py（报告）
                    ├── skills/browser.py（抓取）
                    ├── skills/curator.py（筛选）
                    ├── skills/context_manager.py（上下文）
                    └── actions/*（所有动作）

multi_agents/agents/researcher.py
  └── GPTResearcher  ← 也走这里
```

- 所有研究流程最终都经过 `GPTResearcher`，无论是单 Agent 还是多 Agent 模式
- 30+ 个实例属性构成了隐式的"全局状态"，修改任何一个属性都可能影响多个下游模块
- `conduct_research()` 和 `write_report()` 是最高频调用路径

**安全操作边界：**
- ✅ 新增方法（不修改已有方法签名）
- ✅ 新增实例属性（确保有默认值）
- ❌ 修改 `__init__` 参数签名
- ❌ 修改 `conduct_research` / `write_report` 返回值结构
- ❌ 删除或重命名任何公开属性

#### 9.3.2 `gpt_researcher/config/config.py`（Config 配置类）

**风险定性：项目最高被依赖模块，30+ 文件直接引用。**

| 指标 | 数据 |
|------|------|
| 代码行数 | ~311 行 |
| 配置字段数 | 51 个字段（BaseConfig 中定义） |
| 入向依赖 | **30+ 文件**（全项目最高）：agent、prompts、所有 skills、所有 actions、multi_agents/utils、backend/chat、测试文件 |
| 特殊依赖 | `config.py` 第 189 行：`from ..retrievers.utils import get_all_retriever_names`（方法内懒加载） |

**依赖树（入向）：**

```
Config 被以下模块直接 import：
├── gpt_researcher/agent.py
├── gpt_researcher/prompts.py
├── gpt_researcher/skills/curator.py
├── gpt_researcher/actions/web_scraping.py
├── gpt_researcher/actions/report_generation.py
├── gpt_researcher/actions/query_processing.py
├── multi_agents/agents/utils/llms.py
├── backend/chat/chat.py
├── test-your-retriever.py
├── test-your-llm.py
├── test-your-embeddings.py
└── ...（还有 20+ 间接依赖）
```

**为什么危险：**
- 修改一个字段名（如 `FAST_LLM` → `DEFAULT_LLM`）需要全局查找替换 30+ 文件
- 删除一个字段会导致运行时 `AttributeError`，但不会在 import 时报错，难以提前发现
- 配置加载有三层优先级（文件 → 环境变量 → 默认值），逻辑链复杂

**安全操作边界：**
- ✅ 新增配置字段（在 BaseConfig 中加字段 + 默认值）
- ✅ 修改默认值
- ❌ 重命名已有字段
- ❌ 改变字段类型（如 str → int）
- ❌ 修改配置加载优先级逻辑

---

### 9.4 🟠 橙色（高危）—— 可改动但需谨慎，需全面回归测试

#### 9.4.1 `gpt_researcher/prompts.py`（提示词模板体系）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~900 行 |
| Prompt 方法数 | 20+ 个静态方法 |
| Prompt 家族类 | 4 个（PromptFamily + 3 个 Granite 变体） |
| 入向依赖 | 20+ 文件：agent.py、utils/llm.py、actions/report_generation.py、actions/query_processing.py、actions/agent_creator.py、context/compression.py、mcp/tool_selector.py、mcp/research.py |

**为什么高危：**
- 每个 Prompt 方法的输出格式被下游 JSON 解析器硬编码期望——改了 Prompt 输出格式，`json_repair` 可能救不回来
- `PromptFamily` 基类被 3 个子类继承，修改基类签名会连锁影响
- Prompt 的微调会直接影响 LLM 输出质量，效果不可预测

**安全操作边界：**
- ✅ 新增 Prompt 方法
- ✅ 新增 PromptFamily 子类
- ⚠️ 修改已有 Prompt 文本内容（需要测试下游解析是否兼容）
- ❌ 修改 Prompt 方法的参数签名
- ❌ 修改返回值的结构化格式

#### 9.4.2 `gpt_researcher/utils/llm.py`（LLM 调用工具函数）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~200 行 |
| 核心函数 | `create_chat_completion`、`construct_subtopics` |
| 入向依赖 | 10+ 文件：agent.py、skills/writer.py、skills/curator.py、actions/agent_creator.py、actions/query_processing.py、actions/report_generation.py、multi_agents/agents/utils/llms.py、mcp/* |

**为什么高危：**
- `create_chat_completion` 是整个项目中 LLM 调用的统一入口，全部 Agent 和 Action 都通过它调用 LLM
- 修改参数签名或返回值格式会导致 10+ 个调用点同时失败
- 单 Agent 系统和多 Agent 系统都依赖它

**安全操作边界：**
- ✅ 新增工具函数
- ✅ 给已有函数新增可选参数（有默认值）
- ❌ 修改 `create_chat_completion` 的核心参数或返回值
- ❌ 修改错误处理逻辑（下游代码可能依赖特定异常类型）

#### 9.4.3 `gpt_researcher/skills/researcher.py`（ResearchConductor 研究执行器）

| 指标 | 数据 |
|------|------|
| 代码行数 | **~990 行（全项目最大单文件）** |
| 方法数 | 19 个方法 |
| 异步方法 | 15 个 async 方法，含嵌套 `asyncio.gather` |
| 出向依赖 | actions（choose_agent、get_search_results、plan_research_outline）、document 加载器、utils/enum、logging |

**为什么高危：**
- 990 行单文件，认知负担极重
- 包含多层异步嵌套：`conduct_research → _get_context_by_web_search → _process_sub_query → _search + _scrape + _summarize`
- MCP 策略分支（parallel / sequential / hybrid）增加了控制流复杂度
- 是单 Agent 模式下的核心研究流程，所有 BasicReport 和 DetailedReport 最终都走这里

**安全操作边界：**
- ✅ 新增独立的研究策略方法
- ⚠️ 修改 `conduct_research` 内部逻辑（需要理解完整的异步调用链）
- ❌ 修改 `_process_sub_query` 的返回值结构（影响上下文聚合）
- ❌ 修改 `asyncio.gather` 的并发模式（可能引入竞态条件）

---

### 9.5 🟡 黄色（中危）—— 可重构但需理解上下文

#### 9.5.1 `gpt_researcher/llm_provider/generic/base.py`（LLM 提供商抽象层）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~317 行 |
| 提供商数量 | **22 个**（openai、anthropic、azure_openai、ollama、deepseek 等） |
| if/elif 分支 | **23 个**（`from_provider` 方法） |
| 动态导入 | 每个分支都 `importlib` 动态加载 `langchain_*` 包 |

**风险点：**
- 23 个 if/elif 分支的 `from_provider` 方法是典型的"上帝方法"，新增提供商需要修改核心方法
- 动态导入意味着缺少静态类型检查，错误只在运行时暴露
- 但对外接口稳定（`get_chat_model` 返回 ChatModel），内部重构不影响调用方

**安全操作边界：**
- ✅ 新增 provider（在 `_SUPPORTED_PROVIDERS` 和 `from_provider` 中新增分支）
- ✅ 重构为策略模式 / 注册表模式（不改变对外接口）
- ⚠️ 修改 `get_chat_model` 返回值类型
- ❌ 修改 `_SUPPORTED_PROVIDERS` 中已有 provider 的 key 名称

#### 9.5.2 `multi_agents/agents/orchestrator.py`（ChiefEditorAgent 总编辑）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~119 行 |
| 入向依赖 | 4 文件（`__init__`、multi_agents/main、backend/server_utils） |
| 特殊风险 | `__init__.py` 中有注释标注 import 顺序敏感 |

**风险点：**
- 是 LangGraph StateGraph 的唯一定义处，修改 workflow 节点/边就是修改整个多 Agent 执行流
- `multi_agents/agents/__init__.py` 中有显式注释：`# Below import should remain last since it imports all of the above`，说明 import 顺序影响正确性
- 代码行数虽少，但每一行都是关键的 workflow 定义

**安全操作边界：**
- ✅ 新增 workflow 节点（add_node）
- ✅ 新增条件边（add_conditional_edges）
- ⚠️ 修改已有边的连接关系
- ❌ 修改 `__init__.py` 中的 import 顺序
- ❌ 删除已有节点

#### 9.5.3 `backend/server/websocket_manager.py`（WebSocket 管理器）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~184 行 |
| 出向依赖 | report_type（BasicReport、DetailedReport）、GPTResearcher、server_utils |
| 潜在循环 | 与 `server_utils.py` 之间存在间接双向引用 |

**风险点：**
- `run_agent` 函数是报告类型路由的核心分发点，决定了 Basic / Detailed / Multi-Agent 的执行入口
- 与 `server_utils.py` 存在间接双向引用：websocket_manager import server_utils 的 CustomLogsHandler，server_utils import websocket_manager 的 WebSocketManager 类型
- 消息队列和连接管理是实时通信的基础

**安全操作边界：**
- ✅ 新增报告类型的路由分支
- ✅ 扩展消息格式
- ⚠️ 修改消息队列逻辑（影响前端实时显示）
- ❌ 修改 WebSocket 连接生命周期管理

#### 9.5.4 `backend/server/app.py`（FastAPI 应用入口）

| 指标 | 数据 |
|------|------|
| 代码行数 | ~454 行 |
| 路由数量 | 15+ 个 REST/WebSocket 端点 |
| 出向依赖 | websocket_manager、server_utils、report_store、chat、utils |

**风险点：**
- 路由定义、CORS 配置、静态文件服务集中在一个文件
- 15+ 个端点混合了 CRUD 操作和研究任务触发，职责不够清晰
- 但入向依赖只有 2 个（main.py 和可能的测试），改动影响面可控

**安全操作边界：**
- ✅ 新增 API 端点
- ✅ 修改 CORS 配置
- ⚠️ 修改已有端点的请求/响应格式（影响前端）
- ⚠️ 修改中间件顺序
- ❌ 修改 WebSocket 端点路径（前端硬编码依赖）

---

### 9.6 🟢 绿色（安全区）—— 可以安全重构

#### 9.6.1 检索器（`gpt_researcher/retrievers/*`）

| 特征 | 说明 |
|------|------|
| 模块数量 | 14 个独立检索器 |
| 架构模式 | **策略模式 + 工厂注册**：每个检索器独立文件夹，统一接口 |
| 互相依赖 | **零**——检索器之间无任何 import |
| 共享代码 | 仅 `retrievers/utils.py` 提供公共工具函数 |
| 注册方式 | `__init__.py` 统一导出，`actions/retriever.py` 工厂分发 |

**为什么安全：**
- 完美遵循开闭原则（OCP）：新增检索器只需新建文件夹 + 在 `__init__.py` 注册
- 修改任何一个检索器不影响其他检索器
- 删除一个检索器只需移除注册，不影响系统运行

**重构建议：**
- 可以安全地新增、修改、删除任何单个检索器
- 可以重构 `retrievers/utils.py` 的公共逻辑
- 可以将工厂模式改为自动注册（装饰器模式）

#### 9.6.2 抓取器（`gpt_researcher/scraper/*`）

| 特征 | 说明 |
|------|------|
| 模块数量 | 9 个独立抓取器 |
| 架构模式 | **策略模式 + 字典映射分发** |
| 互相依赖 | **零** |
| 注册方式 | `Scraper` 编排类内的字典映射 |

**为什么安全：** 与检索器架构完全一致，同样遵循开闭原则。

#### 9.6.3 Actions 模块（`gpt_researcher/actions/*`）

| 特征 | 说明 |
|------|------|
| 文件数量 | 7 个功能文件 |
| 总导出函数 | 27 个 |
| 依赖方向 | 单向——被 skills 和 agent 调用，自身不反向依赖它们 |
| 互相依赖 | 极低——各 action 文件之间基本独立 |

**各文件独立性：**

| 文件 | 行数 | 导出函数 | 依赖 |
|------|------|---------|------|
| `agent_creator.py` | ~127 | `choose_agent`、`extract_json_with_regex` | prompts、utils/llm |
| `query_processing.py` | ~170 | `get_search_results`、`generate_sub_queries`、`plan_research_outline` | prompts、config、utils/llm |
| `retriever.py` | ~143 | `get_retriever`、`get_retrievers` | retrievers（动态） |
| `web_scraping.py` | ~102 | `scrape_urls`、`filter_urls` | scraper、config、workers |
| `report_generation.py` | ~310 | `generate_report`、`write_report_introduction`、`write_conclusion` | prompts、config、utils/llm |
| `markdown_processing.py` | ~112 | `extract_headers`、`table_of_contents`、`add_references` | 纯标准库（re、markdown） |
| `utils.py` | ~163 | `stream_output`、`calculate_cost` | 仅 logger |

**为什么安全：**
- 函数粒度小，每个函数职责单一
- `markdown_processing.py` 和 `utils.py` 甚至不依赖项目内其他模块，是纯工具函数
- 修改任何一个 action 不影响其他 action

#### 9.6.4 多 Agent 子 Agent（`multi_agents/agents/` 下的各个 Agent）

| Agent | 行数 | 依赖 | 可安全重构 |
|-------|------|------|-----------|
| `researcher.py` | ~80 | GPTResearcher | ✅ 封装了对 GPTResearcher 的调用 |
| `writer.py` | ~70 | utils/llms、prompts | ✅ 独立的写作逻辑 |
| `reviewer.py` | ~50 | utils/llms、prompts | ✅ 独立的审稿逻辑 |
| `reviser.py` | ~50 | utils/llms、prompts | ✅ 独立的修改逻辑 |
| `publisher.py` | ~80 | 文件 I/O | ✅ 独立的发布逻辑 |
| `human.py` | ~40 | websocket | ✅ 独立的人工反馈 |

**为什么安全：**
- 每个 Agent 都是"薄包装"——核心逻辑委托给 LLM 调用或 GPTResearcher
- Agent 之间不直接调用对方，仅通过 LangGraph 状态传递数据
- 修改一个 Agent 的 Prompt 或逻辑不影响其他 Agent

#### 9.6.5 后端工具（`backend/utils.py`）

| 特征 | 说明 |
|------|------|
| 代码行数 | ~100 行 |
| 功能 | Markdown → PDF、Markdown → DOCX 格式转换 |
| 依赖 | md2pdf、python-docx（外部库） |
| 被依赖 | 仅 `app.py` 的文件导出端点 |

**为什么安全：** 纯工具函数，无状态，输入输出明确。

---

### 9.7 依赖拓扑全景图

```
                     ┌──────────────┐
                     │   main.py    │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │   app.py     │ ← 🟡 中危
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
       ┌──────▼──────┐  ┌──▼──────┐  ┌───▼────────┐
       │ websocket   │  │ report  │  │ chat/      │
       │ _manager    │  │ _store  │  │ chat.py    │
       │ 🟡 中危     │  │ 🟢     │  │ 🟢        │
       └──────┬──────┘  └────────┘  └───┬────────┘
              │                         │
    ┌─────────┼────────┐                │
    │         │        │                │
┌───▼──┐ ┌───▼───┐ ┌──▼────────┐      │
│Basic │ │Detail │ │ Multi     │      │
│Report│ │Report │ │ Agents    │      │
│ 🟢  │ │ 🟢   │ │           │      │
└───┬──┘ └───┬───┘ │ ┌────────┤      │
    │         │     │ │orchestr│      │
    │         │     │ │ator    │      │
    │         │     │ │ 🟡    │      │
    │         │     │ └───┬────┘      │
    └────┬────┘     │     │           │
         │          │  ┌──▼────────┐  │
         │          │  │ editor    │  │
         │          │  │ 🟢       │  │
         │          │  └──┬────────┘  │
    ┌────▼──────────┴─────▼───────────▼─┐
    │       GPTResearcher (agent.py)     │ ← 🔴 禁区
    └────┬────┬────┬────┬────┬────┬─────┘
         │    │    │    │    │    │
    ┌────▼┐┌─▼──┐┌▼───┐┌▼──┐┌▼──┐┌▼────────┐
    │skill││skil││skil ││act││act ││actions/ │
    │/res ││l/  ││l/   ││ion││ion ││markdown │
    │ear  ││wri ││brow ││/  ││/   ││_process │
    │cher ││ter ││ser  ││qry││rpt ││ 🟢     │
    │ 🟠 ││ 🟢││ 🟢 ││🟢 ││🟢  │└─────────┘
    └──┬──┘└─┬──┘└──┬──┘└─┬─┘└─┬──┘
       │     │      │     │    │
    ┌──▼─────▼──────▼─────▼────▼──┐
    │    共享基础设施层             │
    ├──────────────────────────────┤
    │ config.py       🔴 禁区     │
    │ prompts.py      🟠 高危     │
    │ utils/llm.py    🟠 高危     │
    │ llm_provider/   🟡 中危     │
    │ retrievers/*    🟢 安全     │
    │ scraper/*       🟢 安全     │
    └──────────────────────────────┘
```

---

### 9.8 重构优先级建议

基于风险等级和改造需求，推荐的重构顺序：

| 优先级 | 模块 | 操作 | 理由 |
|--------|------|------|------|
| **P0** | `retrievers/*`、`scraper/*` | 可随时新增/删除/修改 | 🟢 零耦合，策略模式隔离 |
| **P1** | `multi_agents/agents/` 各子 Agent | 修改 Prompt 和业务逻辑 | 🟢 薄包装，通过状态解耦 |
| **P2** | `actions/*` 各 action 文件 | 新增/修改工具函数 | 🟢 单向依赖，职责清晰 |
| **P3** | `llm_provider/base.py` | 重构为注册表模式消除 23 个 if/elif | 🟡 接口稳定，内部可安全重构 |
| **P4** | `orchestrator.py` | 修改 workflow 拓扑 | 🟡 行数少但每行关键 |
| **P5** | `skills/researcher.py` | 拆分为多个小文件 | 🟠 990 行太大，但需要完整理解异步链 |
| **P6** | `prompts.py` | 分模块拆分 Prompt | 🟠 900 行，但下游有 JSON 格式硬依赖 |
| **⛔** | `agent.py`、`config.py` | **不重构，只扩展** | 🔴 改动影响面覆盖全项目 |

---

### 9.9 小结

| 风险等级 | 模块数量 | 核心特征 | 改动策略 |
|----------|---------|---------|---------|
| 🔴 **红色（禁区）** | 2 个 | 全局入口 + 全局配置，入向依赖 10~30+ | **只扩展，不修改** |
| 🟠 **橙色（高危）** | 3 个 | 体量大或被广泛调用的核心逻辑 | **可改动，需全面回归测试** |
| 🟡 **黄色（中危）** | 4 个 | 路由/调度/通信等"连接器"模块 | **可重构，需理解上下游** |
| 🟢 **绿色（安全）** | 20+ 个 | 插件化架构，零耦合或单向依赖 | **随时安全重构** |

**架构质量总评**：项目整体采用了良好的分层架构和策略模式，**约 70% 的模块处于绿色安全区**，说明扩展性设计较好。风险集中在 `agent.py` 和 `config.py` 两个核心枢纽——这是典型的"God Object"问题，如果未来要大规模重构，建议优先对这两个模块进行依赖注入改造。
