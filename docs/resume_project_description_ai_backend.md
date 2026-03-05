# 多智能体需求评审与交付规划系统（AI工程岗 / Agent工程岗）

## 中文版本
### Version A：2行
1. 设计并实现基于 LangGraph `StateGraph` 的多智能体编排流程（Parser/Planner/Risk/Reviewer/Reporter + Router），通过条件路由与澄清循环统一 PRD 评审与交付规划，解决传统评审链路割裂与高歧义需求漏检问题，稳定产出 `report.json`、`report.md`、`run_trace.json`。  
2. 构建结构化 LLM 工程链路（tool-calling 优先 + JSON repair fallback + Pydantic schema validation）并服务化为 FastAPI 异步 API 与 MCP Server，解决输出不稳定、跨客户端接入和回归验证难题，形成可观测 trace 工件与评测指标（`trace_complete`、`coverage_ratio_present`）。

### Version B：4条 bullet
- 设计并落地 LangGraph 多 Agent 编排（`parser→planner→risk→reviewer→route_decider→reporter`），通过 `ReviewState` 共享状态与节点化职责边界解决需求评审到交付规划的流程割裂问题，形成可扩展的端到端自动化评审系统并稳定沉淀标准化报告产物。  
- 构建结构化输出链路（provider tool-calling + fallback JSON + `json_repair` + Pydantic 校验），针对 LLM 字段漂移与非结构化响应导致的解析失败问题提供兜底机制，显著提升输出可解析性、可验证性与工程可用性。  
- 实现风险驱动决策系统（`high_risk_ratio` 阈值 `0.4`、最多 `2` 轮 clarification，自动切换 `parser_prompt_version=v1.1-clarify`），解决高歧义需求单轮评审覆盖不足问题，产出可审计的 `routing_rounds` 决策轨迹并增强 hallucination/歧义控制。  
- 开发 FastAPI 异步任务接口与 MCP 工具（`review_prd`/`get_report`）并接入 `eval/run_eval.py` 回归评测，解决系统集成与质量门禁缺失问题，实现 API 级调用、报告检索、trace 完整性检查与覆盖率指标验证。  

### Version C：技术深度版
- 设计 `StateGraph(ReviewState)` 工作流并实现异步节点执行、partial state update 与进度 hook，将多阶段 LLM 任务编排为可维护的状态机，解决跨节点状态一致性与可观测性难题，支持从 CLI、FastAPI 到 MCP 的统一复用。  
- 实现统一结构化调用抽象 `llm_structured_call`，采用“工具调用优先 + 文本 JSON 回退 + `json_repair` 修复 + schema 校验”四层策略，解决多模型能力差异和输出抖动问题，确保 parser/planner/risk/reviewer 节点均可返回 schema-compatible 对象。  
- 构建风险证据工具 `risk_catalog_search`（本地 catalog、token 匹配、IDF 加权评分、top-k 召回）并在 Risk Agent 注入 evidence prompt，解决风险结论缺乏依据与可解释性不足问题；当工具不可用时保持 graceful degradation 并记录 `risk_catalog_tool_status`。  
- 设计 Router 决策节点，将 Reviewer 的 `high_risk_ratio` 与轮次上限组合为条件路由策略，形成“评审-澄清-复审”闭环，解决需求不清导致的虚假确定性输出问题，提升高风险场景下的评审鲁棒性。  
- 落地 trace 工件体系（节点级 `start/end/duration_ms/model/status/input_chars/output_chars/prompt_version/raw_output_path/error_message`）与评测框架（`report_json_valid`、`trace_complete`、`coverage_ratio_present`），解决 agent 系统难回归、难审计问题，支持工程化质量门禁与版本对比。  
- 搭建 FastAPI 异步作业模型（`/api/review`、`/api/review/{run_id}`、`/api/report/{run_id}`）与 MCP stdio Server 双入口，解决外部系统接入与交互方式单一问题，实现任务级进度追踪、跨客户端调用和标准化产物交付。  

---

## English Version
### Version A: 2 lines
1. Designed and implemented a LangGraph `StateGraph` multi-agent orchestration pipeline (Parser/Planner/Risk/Reviewer/Reporter + Router) with conditional routing and clarification loops, solving fragmented PRD review and high-ambiguity miss issues, and consistently producing `report.json`, `report.md`, and `run_trace.json`.  
2. Built a structured LLM engineering stack (tool-calling first + JSON-repair fallback + Pydantic schema validation) and productionized it via FastAPI async APIs and an MCP server, solving unstable outputs and integration gaps while enabling trace artifacts and regression metrics (`trace_complete`, `coverage_ratio_present`).

### Version B: 4 bullets
- Architected a LangGraph multi-agent workflow (`parser→planner→risk→reviewer→route_decider→reporter`) with shared `ReviewState` and node-level responsibility boundaries, solving disconnected requirement-to-delivery review flows and delivering a scalable end-to-end automation pipeline with standardized artifacts.  
- Implemented structured-output reliability controls (provider tool-calling + fallback JSON parsing + `json_repair` + Pydantic validation), solving parse failures caused by schema drift and free-form model responses, and improving output stability and engineering usability.  
- Built a risk-driven decision loop (`high_risk_ratio` threshold `0.4`, max `2` clarification rounds, auto-switch to `parser_prompt_version=v1.1-clarify`), solving low-coverage single-pass reviews on ambiguous inputs and producing auditable `routing_rounds` traces for hallucination/ambiguity control.  
- Delivered FastAPI async APIs and MCP tools (`review_prd`, `get_report`) integrated with `eval/run_eval.py`, solving integration and quality-gate gaps and enabling API-based execution, report retrieval, trace completeness checks, and coverage-ratio validation.  

### Version C: Technical-Depth
- Engineered a `StateGraph(ReviewState)` runtime with async node execution, partial state updates, and progress hooks, turning multi-step LLM collaboration into a maintainable state machine and solving cross-node consistency and observability challenges across CLI/FastAPI/MCP entrypoints.  
- Developed a unified `llm_structured_call` abstraction with a four-layer strategy (tool-calling first, text-JSON fallback, `json_repair`, schema validation), solving provider capability variance and output jitter while guaranteeing schema-compatible outputs for parser/planner/risk/reviewer nodes.  
- Integrated a tool-based risk evidence retriever `risk_catalog_search` (local catalog, token matching, IDF-weighted scoring, top-k recall) into the Risk Agent prompt path, solving weakly grounded risk conclusions and improving explainability; added graceful degradation with `risk_catalog_tool_status` tracing when the tool is unavailable.  
- Designed a router node combining Reviewer `high_risk_ratio` with revision limits into a conditional policy, creating a “review-clarify-re-review” loop that solves false certainty on ambiguous requirements and improves robustness in high-risk scenarios.  
- Implemented trace artifact instrumentation (`start/end/duration_ms/model/status/input_chars/output_chars/prompt_version/raw_output_path/error_message`) and a regression evaluator (`report_json_valid`, `trace_complete`, `coverage_ratio_present`), solving auditability and regression gaps in agent systems and enabling quality gates across iterations.  
- Built dual integration surfaces with FastAPI async jobs (`/api/review`, `/api/review/{run_id}`, `/api/report/{run_id}`) and an MCP stdio server, solving single-channel integration bottlenecks and enabling progress tracking, cross-client invocation, and standardized artifact delivery.  
