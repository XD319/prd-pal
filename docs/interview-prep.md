# Multi-Agent 需求评审系统面试题（V2）

基于当前仓库实现整理，覆盖 LangGraph 工作流、多 Agent 协作、结构化输出、条件路由、风险证据工具、FastAPI、MCP 与评估体系。

## 第一部分：系统设计

### 1. 为什么这里使用 LangGraph，而不是简单的线性 pipeline？
问题  
为什么项目使用 `StateGraph` 来编排，而不是直接按函数顺序调用？

简要回答  
因为流程里存在条件分支与循环（`route_decider -> clarify -> planner...`），LangGraph 对这种状态驱动的分支编排更自然，也更易扩展和追踪。

技术要点  
- `requirement_review_v1/workflow.py` 使用 `StateGraph(ReviewState)`。  
- 主链路和澄清回路共存，依赖 `add_conditional_edges`。  
- 所有节点返回 partial state，框架统一合并。

### 2. 多 Agent 在这套系统里是怎么协作的？
问题  
Parser/Planner/Risk/Reviewer/Reporter 的协作边界是什么？

简要回答  
每个 Agent 只负责一个明确输出域，通过共享 state 解耦；前一节点产出直接作为后一节点输入，避免单个 Agent 过载。

技术要点  
- Parser: `requirement_doc -> parsed_items`。  
- Planner: `parsed_items -> tasks/milestones/dependencies/estimation`。  
- Risk: 计划数据 + 工具证据 -> `risks`。  
- Reviewer: 需求+计划 -> `review_results/plan_review/high_risk_ratio`。  
- Reporter: 纯确定性拼接 `final_report`。

### 3. 如何避免 Agent 间状态混乱？
问题  
多个节点都在读写 state，如何控制状态一致性？

简要回答  
通过 `TypedDict(total=False)` + 节点 partial update 约束写入边界；节点内部不原地改共享对象，统一返回增量结果给 LangGraph merge。

技术要点  
- `state.py` 中 `ReviewState(total=False)`。  
- Agent 内常见模式：`trace = dict(state.get("trace", {}))` 后再 return。  
- 输出字段按责任分离，避免跨域覆盖。

### 4. 为什么把澄清步骤建成独立节点 `clarify`？
问题  
为何不是在 parser 内部做 while 循环？

简要回答  
放在图层做更可观测，路由决策、轮次计数、终止条件都可追踪；节点逻辑保持单一职责。

技术要点  
- `_clarify_node` 复用 parser，仅切换 `parser_prompt_version="v1.1-clarify"`。  
- 路由记录在 `trace["router"]` 与 `trace["routing_rounds"]`。  
- `revision_round` 由路由节点统一维护。

## 第二部分：工程实现

### 5. Structured Outputs 如何保证稳定？
问题  
系统如何尽量稳定地产出结构化 JSON？

简要回答  
先走 provider 工具/函数调用结构化输出；失败时降级为文本 JSON 路径，再用 `json_repair + parse_json_markdown` 解析。

技术要点  
- `utils/llm_structured_call.py` 的 tools/fallback 双路径。  
- `metadata["structured_mode"]` 记录实际模式。  
- 失败抛 `StructuredCallError` 并携带 `raw_output`。

### 6. 为什么需要 schema validation？
问题  
既然拿到 JSON 了，为什么还要 Pydantic 校验？

简要回答  
JSON 只保证语法，不保证业务类型与字段约束；Pydantic 用于做最后一道契约校验与类型归一化。

技术要点  
- `schemas/*.py` 定义 Parser/Planner/Risk/Reviewer 输出模型。  
- `AgentSchemaModel(extra="ignore")` 忽略脏字段。  
- `NormalizedBool`、`SafeStrList` 处理 `"yes"`/`None` 等脏值。

### 7. LLM JSON 解析失败时如何处理？
问题  
如果模型输出不可解析，系统如何避免整个流程崩溃？

简要回答  
Agent 捕获结构化调用异常并降级返回空结果，同时写入 trace 错误信息；流程可继续执行并产出可诊断工件。

技术要点  
- 各 agent `except StructuredCallError` 返回空列表/空字典。  
- `save_raw_agent_output` 保存原始响应，trace 记录 `raw_output_path`。  
- `review_service._derive_status` 根据 trace 统一判定成功/失败。

### 8. temperature=0 在这里的工程意义是什么？
问题  
为什么调用里固定 `temperature=0`？

简要回答  
此场景追求结构一致性与可回归性，优先降低输出波动而不是追求文本多样性。

技术要点  
- `llm_structured_call` fallback 调用 `create_chat_completion(..., temperature=0)`。  
- 与 schema 校验组合，提高可测性。  
- 仍保留 trace 便于定位偶发格式偏差。

## 第三部分：Agent 设计

### 9. Risk Agent 如何降低 hallucination？
问题  
Risk Agent 除了让模型“想”，还做了什么来约束？

简要回答  
先用本地风险目录检索出证据候选，再把证据喂给模型；最终风险项还会补齐 evidence 字段，减少“无依据风险”。

技术要点  
- `tools/risk_catalog_search.py` 本地 TF-IDF 风格检索。  
- `risk_agent.py` 将 `evidence_json` 注入 prompt。  
- `_attach_fallback_evidence` 为缺证据项补默认证据。

### 10. Tool-based evidence retrieval 的作用是什么？
问题  
为什么要给 Risk Agent 接工具，不直接全靠 LLM？

简要回答  
工具把风险判断锚定到可复核知识库，降低纯生成幻觉，同时把证据 ID/snapshot 输出到结果中便于审计。

技术要点  
- 风险项包含 `evidence_ids/evidence_snippets`。  
- trace 记录 `risk_catalog_hits/top_ids/tool_status`。  
- 支持 `RISK_AGENT_ENABLE_CATALOG_TOOL` 开关控制。

### 11. 工具不可用时系统会怎样？
问题  
如果风险目录检索报错或被禁用，流程会中断吗？

简要回答  
不会中断，Risk Agent 走 degraded 模式继续产出结果，并在 trace 标注退化原因。

技术要点  
- `risk_catalog_tool_status`：`ok/degraded_error/degraded_disabled`。  
- 报错时记录 `risk_catalog_tool_error`。  
- 单元测试覆盖禁用、报错、命中、未命中场景。

### 12. 为什么 Reporter Agent 不调用 LLM？
问题  
报告生成为何做成确定性字符串拼接？

简要回答  
报告是可验证工件，确定性渲染更稳定、可回归、可 diff；避免最后一步再引入生成不确定性。

技术要点  
- `reporter_agent.py` 明确 “no LLM call”。  
- 通过 `_build_*` 系列函数拼 Markdown。  
- trace 里 reporter model 为 `"none"`。

## 第四部分：系统可靠性

### 13. Conditional routing 如何避免无限循环？
问题  
澄清回路如何确保可终止？

简要回答  
双重门控：风险比例阈值 + 最大轮次上限。超过阈值且未达上限才循环，否则直接进入 reporter。

技术要点  
- `_HIGH_RISK_THRESHOLD = 0.4`。  
- `_MAX_REVISION_ROUNDS = 2`。  
- `_route_decider_node` 统一写 `routing_reason` 和 `revision_round`。

### 14. 系统如何监控 agent 执行状态？
问题  
怎样知道每个节点是否成功、执行到哪一步？

简要回答  
通过 trace span + progress hook 双层观测：节点内记录时延/状态，API 层实时维护 job 进度并暴露查询接口。

技术要点  
- `utils/trace.py` 输出 start/end/duration/model/status 等字段。  
- `workflow.py` 的 `_build_async_node/_build_sync_node` 注入 `progress_hook`。  
- `server/app.py` 维护 `JobRecord.node_progress`。

### 15. 失败后还能拿到什么结果？
问题  
某个 Agent 失败时，系统是全失败还是部分可用？

简要回答  
是“部分可用 + 可诊断”：失败节点返回空结构并写错误 trace，已有中间结果仍会落盘到 report/trace 工件。

技术要点  
- `run_review.py` 无论成功失败都写 `report.json` 与 `run_trace.json`。  
- `review_service` 可基于 trace 推导最终 `status`。  
- API 查询可读取已有 run 目录进行恢复展示。

### 16. 为什么要把 trace 单独写成 run_trace.json？
问题  
report.json 里已有 trace，为什么还单独存一份？

简要回答  
单独工件便于监控系统或脚本快速读取执行链，不必扫描完整业务报告；也方便增量写入和调试。

技术要点  
- `run_review.write_outputs` 同时写 `report.md/report.json/run_trace.json`。  
- `server/app.py` 可从 `run_trace.json` 回推节点进度。  
- `eval/run_eval.py` 对 trace 做完整性校验。

## 第五部分：扩展能力

### 17. MCP Server 在这套系统里的作用是什么？
问题  
为什么还要提供 MCP server，而不只保留 HTTP API？

简要回答  
MCP 提供标准工具接口，便于 AI 客户端（如支持 MCP 的助手）直接以 tool call 方式触发评审和取报告。

技术要点  
- `mcp_server/server.py` 基于 `FastMCP("requirement-review-v1")`。  
- 暴露 `ping/review_prd/get_report` 三个工具。  
- 通过 stdio transport 运行，适配本地代理链路。

### 18. 如何把系统集成到 AI 客户端？
问题  
外部智能体如何调用这个系统？

简要回答  
两种方式：MCP 工具调用（推荐给 Agent 客户端）或 FastAPI HTTP 调用（推荐给 Web/服务端集成）。

技术要点  
- MCP: `review_prd` 返回 run_id/metrics/artifacts。  
- HTTP: `POST /api/review` + `GET /api/review/{run_id}` + `GET /api/report/{run_id}`。  
- run_id 统一作为异步任务关联键。

### 19. FastAPI API 层做了哪些工程化设计？
问题  
API 层如何承载异步长任务并反馈进度？

简要回答  
通过内存 JobRecord + asyncio task 后台执行，前台轮询查询进度；支持输入文本或文件路径。

技术要点  
- `ReviewCreateRequest` 强约束“二选一输入”。  
- `_run_job` 内调用 `review_prd_text_async`。  
- `get_review_status` 支持运行中/落盘后状态回读。

### 20. Evaluation framework 如何保障迭代质量？
问题  
项目如何做回归评估，不只是“能跑就行”？

简要回答  
有独立评估脚本和针对关键能力的测试集，验证 report 结构、trace 完整性、覆盖率字段与关键路由/工具行为。

技术要点  
- `eval/run_eval.py`：批量 case 回归，生成聚合报告。  
- `tests/test_routing_loop.py`：循环与终止条件。  
- `tests/test_risk_tool.py`：证据工具命中/降级路径。  
- `tests/test_schema_validation.py`：schema 校验与类型归一化。

