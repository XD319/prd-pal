# Multi-Agent Requirement Review & Delivery Planning System

基于 LangGraph 的多 Agent 需求评审与交付规划系统——输入一份 PRD，自动完成需求拆解、交付计划生成、风险识别、质量评审，并输出结构化报告。

> 本项目在 [GPT-Researcher](https://github.com/assafelovic/gpt-researcher) 基础上扩展，复用其 LLM 调用链路（`gpt_researcher.utils.llm`）和配置体系（`gpt_researcher.config.Config`），新增 `requirement_review_v1/` 模块实现需求评审管线。

---

## Architecture

```
                          requirement_review_v1 — LangGraph Pipeline
                          ==========================================

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                                                                          │
  │   docs/sample_prd.md                                                     │
  │         │                                                                │
  │         ▼                                                                │
  │   ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐       │
  │   │  Parser   │────▶│ Planner  │────▶│   Risk   │────▶│ Reviewer │       │
  │   │  Agent    │     │  Agent   │     │  Agent   │     │  Agent   │       │
  │   └──────────┘     └──────────┘     └──────────┘     └──────────┘       │
  │     LLM call         LLM call         LLM call         LLM call         │
  │   requirement_doc   parsed_items     tasks/miles/deps  parsed_items      │
  │   → parsed_items    → tasks,         → risks           + plan            │
  │                       milestones,                      → review_results  │
  │                       dependencies,                    + plan_review     │
  │                       estimation                                         │
  │                                                           │              │
  │                                                           ▼              │
  │                                                     ┌──────────┐        │
  │                                                     │ Reporter │        │
  │                                                     │  Agent   │        │
  │                                                     └──────────┘        │
  │                                                     No LLM call         │
  │                                                     → final_report      │
  │                                                           │              │
  │                                                           ▼              │
  │                                                     outputs/<run_id>/    │
  │                                                     ├── report.md        │
  │                                                     ├── report.json      │
  │                                                     └── run_trace.json   │
  └──────────────────────────────────────────────────────────────────────────┘

  Pipeline:  parser ──▶ planner ──▶ risk ──▶ reviewer ──▶ reporter ──▶ END
```

### Agent 职责

| Node | 文件 | LLM | 输入 → 输出 |
|------|------|-----|-------------|
| **Parser** | `agents/parser_agent.py` | Yes | `requirement_doc` → `parsed_items`（结构化需求列表） |
| **Planner** | `agents/planner_agent.py` | Yes | `parsed_items` → `tasks`, `milestones`, `dependencies`, `estimation` |
| **Risk** | `agents/risk_agent.py` | Yes | `tasks/milestones/deps/estimation` → `risks`（交付风险清单） |
| **Reviewer** | `agents/reviewer_agent.py` | Yes | `parsed_items` + delivery plan → `review_results` + `plan_review` |
| **Reporter** | `agents/reporter_agent.py` | No | 全部 state → `final_report`（Markdown 报告，纯字符串拼接） |

---

## Quickstart

### 1. 环境准备

```bash
# 克隆仓库
git clone <repo-url>
cd Multi-Agent-Requirement-Review-and-Delivery-Planning-System

# 安装依赖（推荐 Python 3.10+）
pip install -e .

# 配置 .env
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY（必须）
# 如需代理，添加 HTTP_PROXY / HTTPS_PROXY（见 Troubleshooting）
```

### 2. 一条命令运行

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
```

运行完成后输出类似：

```
Report : outputs/20260223T085510Z/report.md
State  : outputs/20260223T085510Z/report.json
Trace  : outputs/20260223T085510Z/run_trace.json
```

### 3. 调试单个 Agent

```bash
# 仅运行 Parser Agent
python -m requirement_review_v1.debug --agent parser

# 仅运行 Reviewer Agent（使用内置 mock 数据）
python -m requirement_review_v1.debug --agent reviewer

# 运行全部 Agent（parser + reviewer）
python -m requirement_review_v1.debug --agent all

# 指定自定义需求文档
python -m requirement_review_v1.debug --agent all --input docs/sample_prd.md
```

### 样例输入

仓库提供多份示例 PRD，可直接用于演示：

| 文件 | 场景 | 需求条数 |
|------|------|----------|
| `docs/sample_prd.md` | 用户管理模块（轻量） | 5 条 |
| `examples/example_prd_admin.md` | ToB 商户运营后台 | 4 大功能 + 非功能需求 |
| `examples/example_prd_app_feature.md` | ToC 社交 App "附近的人" | 4 大功能 + 非功能需求 |

```bash
# 跑通不同场景
python -m requirement_review_v1.main --input docs/sample_prd.md
python -m requirement_review_v1.main --input examples/example_prd_admin.md
python -m requirement_review_v1.main --input examples/example_prd_app_feature.md
```

以下是最简样例 `docs/sample_prd.md` 的内容：

```markdown
# Sample PRD — User Management Module

## 1. User Registration
The system shall allow users to register with email and password.
- Passwords must be at least 8 characters with one uppercase letter and one digit.
- A confirmation email must be sent within 30 seconds of registration.

## 2. Login
The system should provide a fast and user-friendly login experience.

## 3. Account Deactivation
Admin users shall be able to deactivate any user account, and the change must take effect immediately.

## 4. Password Reset
Users should be able to reset their password easily through a self-service flow.

## 5. Audit Logging
All authentication events must be logged for compliance purposes, with appropriate detail.
```

---

## Outputs

每次运行在 `outputs/<run_id>/` 目录下生成以下产物（`run_id` 格式为 UTC 时间戳 `YYYYMMDDTHHMMSSZ`）：

| 文件 | 格式 | 说明 |
|------|------|------|
| `report.md` | Markdown | 人类可读的完整评审报告，包含需求列表、逐条评审详情（Clarity / Testability / Ambiguity）、风险汇总、交付计划（任务分解 / 里程碑 / 工时估算）、交付风险登记册、计划评审意见 |
| `report.json` | JSON | 完整 state 快照，包含 `parsed_items`、`review_results`、`tasks`、`milestones`、`estimation`、`risks`、`plan_review` 等全部中间结果，附带 `schema_version`、`run_id`、`model`、`provider` 元数据 |
| `run_trace.json` | JSON | 各 Agent 节点的执行追踪：`start`/`end` 时间、`duration_ms`、`model`、`status`、`input_chars`/`output_chars`、`prompt_version` |
| `raw_agent_outputs/` | 目录 | 当 Agent 输出 JSON 解析失败时，LLM 原始响应会保存为 `<agent_name>.txt`，用于调试 |

### report.md 报告结构

```
# Requirement Review Report
## 1. Requirement List          — 结构化需求表（ID / Description / AC）
## 2. Review Details            — 逐条评审（Clear / Testable / Ambiguous / Issues / Risk Level）
## 3. Risk Summary              — 需求质量风险统计（High / Medium / Low 计数与占比）
## 4. Delivery Plan
   ### 4.1 Task Breakdown       — 任务分解（ID / Title / Owner / Dependencies / Est. Days）
   ### 4.2 Milestones           — 里程碑（ID / Title / Tasks / Target Days）
   ### 4.3 Estimation           — 工时汇总（total_days + buffer_days）
## 5. Delivery Risk Register    — 交付风险登记册（Impact / Mitigation / Buffer Days）
## 6. Plan Review               — 计划评审意见（Coverage / Milestones / Estimation）
```

---

## Metrics

系统在 `report.json` 的 `metrics` 字段中输出可回归、可比较的结构化指标（由 `requirement_review_v1/metrics/coverage.py` 计算）。

### coverage_ratio 语义

- 定义：`coverage_ratio = covered_requirements / total_requirements`
- `total_requirements`：Parser 产出的需求 ID 总数（`parsed_items[*].id`）
- `covered_requirements`：至少被一个任务引用的需求数（`tasks[*].requirement_ids`）
- 取值范围：`[0, 1]`，并保留 4 位小数
- 边界行为：当无可统计需求（`total_requirements == 0`）时返回 `0.0`

### 相关指标字段

| 字段 | 类型 | 含义 |
|------|------|------|
| `coverage_ratio` | float | 需求覆盖率（0~1） |
| `uncovered_requirements` | list[str] | 未被任何任务覆盖的需求 ID 列表 |
| `requirement_to_tasks` | dict[str, list[str]] | 每个需求 ID 对应的任务 ID 列表 |

---

## Eval

项目提供最小回归评估脚本 `eval/run_eval.py`，用于批量执行测试 case 并校验核心质量门禁：

- `report_json_valid`：`report.json` 顶层关键字段存在且类型正确
- `trace_complete`：5 个 Agent（`parser/planner/risk/reviewer/reporter`）的 trace 完整
- `coverage_ratio_present`：`metrics.coverage_ratio` 存在且值在 `[0, 1]`

默认输入 case 文件为 `eval/cases/prd_test_inputs.jsonl`，每行一个 JSON case。

### 运行 Eval

```bash
# 使用默认路径运行全部 case
python eval/run_eval.py

# 指定 case 文件、输出报告和运行产物目录
python eval/run_eval.py \
  --cases eval/cases/prd_test_inputs.jsonl \
  --out eval/eval_report.json \
  --runs-dir eval/runs
```

运行后将生成：

- 汇总报告：`eval/eval_report.json`
- 每个 case 的产物目录：`eval/runs/<case_id>_<timestamp>/`
  - `report.md`
  - `report.json`
  - `run_trace.json`

> CI 集成说明：当存在 `failed` 或 `error` case 时，`eval/run_eval.py` 将返回非 0 退出码。

### 运行示例

```bash
# 1) 先跑一次主流程，生成单次报告
python -m requirement_review_v1.main --input docs/sample_prd.md

# 2) 再跑回归评估，验证 report/trace/metrics 关键约束
python eval/run_eval.py
```

---

## Testing

完整测试报告见 [`docs/v1-test-report.md`](docs/v1-test-report.md)。

### 测试环境

| 项 | 值 |
|----|----|
| Python | 3.10.4 |
| LLM | `gpt-4.1` (OpenAI) |
| 关键依赖 | `langgraph>=0.2.76`, `langchain-core>=1.0.0`, `json-repair>=0.29.8` |

### 性能数据（docs/sample_prd.md, 5 条原始需求）

| 节点 | 耗时 | 输出 |
|------|------|------|
| Parser Agent | 9.534s | 7 条结构化需求（REQ-001 ~ REQ-007） |
| Reviewer Agent | 5.088s | 7 条评审结果（含 3 条 High Risk） |
| Reporter Agent | ~0s | 4,857 字符 Markdown 报告 |
| **总计** | **~14.6s** | — |

> 注：以上数据来自 3-node 管线（parser → reviewer → reporter）测试。当前 5-node 管线（parser → planner → risk → reviewer → reporter）增加了 Planner 和 Risk 两次 LLM 调用，总耗时会相应增加。

### 样例评审结果

| 需求 | Clear | Testable | Ambiguous | Risk |
|------|-------|----------|-----------|------|
| REQ-001 User Registration | Yes | Yes | No | Low |
| REQ-002 Password Validation | Yes | Yes | No | Low |
| REQ-003 Confirmation Email | Yes | Yes | No | Low |
| REQ-004 Login Experience | No | No | Yes | **High** — "fast", "user-friendly" 是主观描述 |
| REQ-005 Account Deactivation | Yes | Yes | No | Low |
| REQ-006 Password Reset | No | Yes | Yes | **High** — "easily" 未定义 |
| REQ-007 Audit Logging | No | Yes | Yes | **High** — "appropriate detail" 含义模糊 |

### 测试结论

| 测试项 | 状态 |
|--------|------|
| Parser Agent 单独运行 | Pass |
| Reviewer Agent 单独运行 | Pass |
| Reporter Agent（随完整管线） | Pass |
| LangGraph Workflow 编排 | Pass |
| CLI 入口 + 输出持久化 | Pass |
| 报告内容质量 | Pass — 高风险需求识别正确 |

---

## Troubleshooting

### 1. Windows 代理 / SSL 错误

**症状**：`pip install` 或 LLM 调用报 `SSLError` / `ProxyError` / `Connection error`。

**原因**：Windows 系统代理将 HTTPS 协议配置为 `https://127.0.0.1:port`，导致 `httpx` / `pip` 对代理服务器发起 TLS 握手失败（本地代理通常只接受 HTTP 连接）。

**解决**：在 `.env` 或终端中显式设置代理协议为 `http://`：

```bash
# .env
HTTP_PROXY=http://127.0.0.1:7897
HTTPS_PROXY=http://127.0.0.1:7897

# 或在 PowerShell 中临时设置
$env:HTTP_PROXY="http://127.0.0.1:7897"
$env:HTTPS_PROXY="http://127.0.0.1:7897"
```

> 关键：`HTTPS_PROXY` 的值应为 `http://...`（不是 `https://...`），因为它指的是代理服务器的连接协议，而非目标 URL 的协议。

### 2. PowerShell 终端 Emoji 乱码

**症状**：终端输出中的 emoji（如报告里的风险等级标记）显示为乱码方块。

**原因**：Windows PowerShell 默认使用 GBK（代码页 936）编码，不支持 UTF-8 emoji 字符。

**解决**：

```powershell
# 方法 1：当前会话切换 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001

# 方法 2：使用 Windows Terminal（默认 UTF-8，推荐）

# 方法 3：查看输出文件（文件内容始终为 UTF-8，不受终端编码影响）
# 直接用 VS Code 或浏览器打开 outputs/<run_id>/report.md
```

> 注：这是纯终端显示问题，`report.md` 和 `report.json` 文件内容始终正确。

### 3. OPENAI_API_KEY 未配置

**症状**：运行报 `AuthenticationError` 或提示 API key missing。

**解决**：

```bash
# 复制示例文件并填入 key
cp .env.example .env
# 编辑 .env，设置 OPENAI_API_KEY=sk-...
```

### 4. 模块导入失败 / ModuleNotFoundError

**症状**：`ModuleNotFoundError: No module named 'gpt_researcher'` 或 `No module named 'requirement_review_v1'`。

**解决**：确保以可编辑模式安装了项目：

```bash
pip install -e .
```

项目通过 `pyproject.toml` 定义依赖，`-e .` 会将根目录加入 `sys.path`，使 `gpt_researcher` 和 `requirement_review_v1` 均可导入。

---

## Project Structure

```
requirement_review_v1/
├── __init__.py
├── main.py                    # CLI 入口：python -m requirement_review_v1.main --input <file>
├── debug.py                   # 调试入口：单 Agent 测试
├── workflow.py                # LangGraph StateGraph 定义（5 节点线性管线）
├── state.py                   # ReviewState(TypedDict) — 共享状态定义
├── prompts.py                 # 全部 Agent 的 System/User Prompt 模板
├── agents/
│   ├── __init__.py
│   ├── parser_agent.py        # 需求拆解
│   ├── planner_agent.py       # 交付计划生成
│   ├── risk_agent.py          # 交付风险识别
│   ├── reviewer_agent.py      # 需求质量评审 + 计划交叉检查
│   └── reporter_agent.py      # Markdown 报告生成（无 LLM）
└── utils/
    ├── __init__.py
    ├── io.py                  # raw_agent_outputs 持久化
    └── trace.py               # 轻量级 Span 计时追踪

examples/
├── example_prd_admin.md       # ToB 商户运营后台 PRD
└── example_prd_app_feature.md # ToC 社交 App 功能 PRD

docs/
├── sample_prd.md              # 轻量示例 PRD（Quickstart 输入）
├── v1-test-report.md          # V1 完整测试报告
└── architecture-and-v1-plan.md # 架构分析与改造方案

outputs/<run_id>/              # 每次运行的产物目录
├── report.md
├── report.json
├── run_trace.json
└── raw_agent_outputs/         # LLM 原始响应（仅在解析失败时生成）
```

---

## Configuration

LLM 模型和 Provider 通过 `gpt_researcher.config.Config` 从环境变量读取：

| 环境变量 | 说明 | 示例 |
|----------|------|------|
| `OPENAI_API_KEY` | OpenAI API 密钥（必须） | `sk-...` |
| `SMART_LLM` | 模型配置 `provider:model`，不设则默认 OpenAI | `openai:gpt-4.1` |
| `HTTP_PROXY` / `HTTPS_PROXY` | 代理地址（可选） | `http://127.0.0.1:7897` |

---

## License

MIT
