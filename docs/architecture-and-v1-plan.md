# GPT-Researcher 架构分析 & V1 需求评审改造方案

> 分支：`feature/requirement-review-v1`
> 日期：2026-02-22

---

## 一、项目入口

### 1.1 CLI 入口

| 入口 | 文件 | 关键函数/类 | 说明 |
|------|------|-------------|------|
| 单 Agent CLI | `cli.py` L138 | `async def main(args)` → `GPTResearcher` | argparse, `conduct_research()` + `write_report()` |
| 多 Agent CLI | `multi_agents/main.py` L52 | `async def main()` → `ChiefEditorAgent` | 读 `task.json` → `run_research_task()` |
| 深度研究 CLI | `backend/report_type/deep_research/main.py` L6 | `async def main(task)` | 独立深度研究入口 |

### 1.2 Web 入口

| 入口 | 文件 | 关键函数/类 | 说明 |
|------|------|-------------|------|
| 启动脚本 | `main.py` (root) L33 | `uvicorn.run(app)` | 导入 `backend.server.app:app` |
| FastAPI 定义 | `backend/server/app.py` L96 | `app = FastAPI(lifespan=lifespan)` | WS `/ws`, POST `/report/`, POST `/api/chat` |
| 备用启动 | `backend/run_server.py` L16 | `uvicorn.run("server.app:app")` | 从 backend 目录启动 |

### 1.3 实际执行起点

- **单 Agent**: `GPTResearcher.__init__()` → `conduct_research()` → `write_report()`
- **多 Agent**: `ChiefEditorAgent.run_research_task()` → `chain.ainvoke({"task": self.task})`

---

## 二、工作流 / 编排核心

### 2.1 主图 — ChiefEditorAgent

**文件**: `multi_agents/agents/orchestrator.py`

```
browser → planner → human →[conditional]→ researcher → writer → publisher → END
                      ↑        revise         ↓
                      └────────────────────────┘
```

| 方法 | 行号 | 作用 |
|------|------|------|
| `_create_workflow(agents)` | L52 | `StateGraph(ResearchState)`, 添加 6 个 node |
| `_add_workflow_edges(workflow)` | L68 | 顺序边 + human conditional edge |
| `init_research_team()` | L83 | 组装 agents + 创建 workflow |
| `run_research_task()` | L95 | `.compile()` → `chain.ainvoke()` |

### 2.2 子图 — EditorAgent

**文件**: `multi_agents/agents/editor.py`

```
researcher → reviewer →[conditional]→ END
                ↑         revise        ↓
                └── reviser ←───────────┘
```

| 方法 | 行号 | 作用 |
|------|------|------|
| `_create_workflow()` | L126 | `StateGraph(DraftState)`, 3 个 node |
| `run_parallel_research()` | L52 | `asyncio.gather(*[chain.ainvoke(...)])` 并发 |

### 2.3 State 定义

| State | 文件 | 字段 |
|-------|------|------|
| `ResearchState` | `multi_agents/memory/research.py` | task, sections, research_data, report 等 13 字段 |
| `DraftState` | `multi_agents/memory/draft.py` | task, topic, draft, review, revision_notes 共 5 字段 |

---

## 三、LLM 调用封装

### 3.1 调用链路

```
call_model()                                ← multi_agents 专用入口
  └→ create_chat_completion()               ← gpt_researcher/utils/llm.py:40
       └→ get_llm(provider, **kwargs)       ← 同文件:26
            └→ GenericLLMProvider.from_provider()  ← llm_provider/generic/base.py:96
                 └→ ChatOpenAI / ChatAnthropic / ... (LangChain 实例)
       └→ provider.get_chat_response()      ← base.py:257
            ├→ self.llm.ainvoke(messages)    ← base.py:260 (非流式)
            └→ self.llm.astream(messages)    ← base.py:277 (流式)
```

### 3.2 关键文件

| 层级 | 文件 | 函数/类 |
|------|------|---------|
| multi_agents 封装 | `multi_agents/agents/utils/llms.py` | `call_model(prompt, model, response_format)` |
| 统一调用入口 | `gpt_researcher/utils/llm.py` | `create_chat_completion(messages, model, llm_provider, ...)` |
| Provider 工厂 | `gpt_researcher/llm_provider/generic/base.py` | `GenericLLMProvider.from_provider(llm_provider, **kwargs)` |
| 配置 | `gpt_researcher/config/config.py` | `Config` 类, 解析 `SMART_LLM="provider:model"` |

### 3.3 LLM 传递方式

LLM **不是**预实例化传入 agent 的。每次调用 `create_chat_completion` 都通过 `Config()` on-the-fly 读环境变量创建 provider 实例。

---

## 四、V1 改造最小落点方案

### 4.1 新增文件清单

```
requirement_review_v1/
├── __init__.py
├── state.py                # ReviewState(TypedDict)
├── prompts.py              # 需求拆解/评审/汇总 prompt
├── agents/
│   ├── __init__.py
│   ├── parser_agent.py     # 需求拆解 node: requirement_doc → parsed_items
│   ├── reviewer_agent.py   # 逐条评审 node: parsed_items → review_results
│   └── reporter_agent.py   # 汇总输出 node: review_results → final_report
├── workflow.py             # StateGraph(ReviewState) 图定义 + compile
└── main.py                 # CLI 入口: argparse + asyncio.run
```

### 4.2 挂载位置

**仓库根目录 `requirement_review_v1/`**，与 `multi_agents/` 平级。

理由：
- `multi_agents/` 就是这样独立挂的，有自己的 `main.py`、`memory/`、`agents/`
- V1 直接复用 `gpt_researcher/utils/llm.py` 的 `create_chat_completion()` 和 `Config`
- 零侵入，不影响原有功能

### 4.3 workflow.py 核心骨架

```python
from langgraph.graph import StateGraph, END
from .state import ReviewState
from .agents import parser_agent, reviewer_agent, reporter_agent

def build_review_graph():
    workflow = StateGraph(ReviewState)

    workflow.add_node("parser", parser_agent.run)
    workflow.add_node("reviewer", reviewer_agent.run)
    workflow.add_node("reporter", reporter_agent.run)

    workflow.set_entry_point("parser")
    workflow.add_edge("parser", "reviewer")
    workflow.add_edge("reviewer", "reporter")
    workflow.add_edge("reporter", END)

    return workflow.compile()
```

### 4.4 LLM 复用方式

```python
from gpt_researcher.utils.llm import create_chat_completion
from gpt_researcher.config.config import Config

cfg = Config()
response = await create_chat_completion(
    model=cfg.smart_llm_model,
    messages=lc_messages,
    llm_provider=cfg.smart_llm_provider,
    llm_kwargs=cfg.llm_kwargs,
)
```

### 4.5 一条命令运行 V1

```bash
python -m requirement_review_v1.main --input docs/prd.md
```

### 4.6 main.py 骨架

```python
import asyncio
import argparse
from dotenv import load_dotenv
from .workflow import build_review_graph

def parse_args():
    parser = argparse.ArgumentParser(description="Requirement Review V1")
    parser.add_argument("--input", type=str, required=True, help="需求文档路径")
    return parser.parse_args()

async def main():
    load_dotenv()
    args = parse_args()
    with open(args.input, "r", encoding="utf-8") as f:
        doc = f.read()
    graph = build_review_graph()
    result = await graph.ainvoke({"requirement_doc": doc})
    print(result["final_report"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 五、后续扩展方向

| 阶段 | 内容 |
|------|------|
| V1.1 | 增加 human-in-the-loop conditional edge（评审结果人工确认） |
| V1.2 | reviewer_agent 拆分为多维度并行评审（可行性、完整性、一致性） |
| V1.3 | 接入 Web 入口，在 `backend/server/app.py` 增加 `/api/review` endpoint |
| V2 | 支持多文档关联评审、历史版本 diff 评审 |
