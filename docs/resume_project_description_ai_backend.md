# 多智能体需求评审与交付规划系统（v3.0.0）

## 中文版本

### Version A：2行极简版
1. 面向 PRD 评审与交付规划链路割裂、LLM 输出不稳定的问题，设计并实现基于 LangGraph 的多智能体工作流，串联需求解析、规划、风险识别、评审与报告生成，稳定产出结构化 artifacts。  
2. 将结构化输出、澄清路由、证据检索、子流复用、并行执行、TTL 缓存、FastAPI 异步服务、MCP 接口、trace/eval/tests 组合为可工程化复用的 Agent 后端系统。  

### Version B：4条标准版
- 面向 PRD 评审与交付规划链路分散的问题，设计 LangGraph 多智能体工作流，串联解析、规划、风险、评审与报告节点，并通过澄清路由形成可闭环的自动化评审流程。  
- 针对 LLM 输出易漂移、难落库的情况，构建 Structured Outputs + schema validation + fallback 链路，统一约束核心 Agent 的结构化结果，减少非标准 JSON 对主流程的影响，提升工作流可解析性与可回归性。  
- 为增强风险判断的可解释性与复用性，将证据检索封装为技能体系并接入风险分析子流，结合并行执行与进程内 TTL 缓存，沉淀出可复用的 Agent workflow 组件。  
- 将核心能力封装为 FastAPI 异步服务与 MCP Server，并补齐 trace、eval 和测试体系，支持异步任务提交、运行追踪、报告读取与质量校验，形成可集成的 AI 后端服务。  

### Version C：技术展开版
- 面向需求评审、交付规划和风险识别分散在不同环节的问题，设计基于 LangGraph `StateGraph` 的多智能体编排流程，将 `Parser / Planner / Risk / Reviewer / Reporter` 解耦为独立节点，并通过 `fan-out/fan-in` 与条件路由实现从解析到报告的闭环，最终沉淀统一的评审与交付 artifacts。  
- 针对 LLM 输出字段漂移、JSON 不合法和跨模型能力差异，构建 “tool/function calling 优先 + 文本 JSON fallback + `json_repair` 修复 + Pydantic schema validation” 的结构化调用链路，使 parser、planner、risk、reviewer 节点都能返回可校验、可回退的 schema-compatible 结果。  
- 为降低高歧义输入在单轮评审中的漏检风险，基于 Reviewer 输出设计 risk-driven routing loop，当高风险比例超过阈值时触发 clarify loop 并重新解析需求，形成带 `routing_rounds` 的可审计决策轨迹，强化 Agent orchestration 中的 workflow control。  
- 将本地风险目录检索封装为 `Skill Registry + SkillExecutor` 能力层，支持 evidence retrieval、trace 注入、graceful degradation 与进程内 TTL cache，使 Risk Agent 在工具可用时生成 grounded 风险结论，在工具异常时也能保持主流程可运行。  
- 抽象 `risk_analysis` reusable subgraph，将“证据检索 -> 风险生成”封装为独立子流并接入主图，同时让 `planner` 与 `risk` 分支在主工作流中并行执行，记录并聚合缓存命中、延迟与并行指标，支持后续性能分析与子流复用。  
- 将工作流平台化为 FastAPI async service 与 MCP server 双入口，支持 PRD 提交、异步运行、状态查询和报告读取，并统一落盘 `report.md`、`report.json`、`run_trace.json`，满足 AI 后端服务集成与多客户端接入场景。  
- 建立 trace artifacts、eval framework 与单元测试体系，覆盖 schema、routing loop、risk tool、cache、MCP、runtime metrics 等关键路径，为多智能体系统提供可观测、可回归、可验证的工程化质量保障。  

---

## English Version

### Version A: 2-line concise
1. Built a LangGraph-based multi-agent workflow for PRD review and delivery planning, combining parsing, planning, risk analysis, review, and reporting to produce stable structured artifacts.  
2. Productionized the workflow with structured-output reliability, clarify routing, evidence retrieval, reusable subflow, parallel execution, TTL cache, FastAPI async APIs, MCP integration, and trace/eval/test coverage.  

### Version B: 4 standard bullets
- For fragmented PRD review and delivery-planning flows, architected a LangGraph multi-agent workflow that connects parsing, planning, risk analysis, review, and reporting, then closes the loop with clarification routing for end-to-end automation.  
- To make LLM outputs usable in backend pipelines, built a Structured Outputs stack with schema validation and fallback handling, reducing malformed-response failures and improving workflow reliability and regression readiness.  
- To improve grounding and reuse, packaged risk evidence retrieval into a skill layer and integrated it into a reusable risk-analysis subflow, with parallel execution and in-process TTL caching for more efficient agent workflows.  
- Productized the system as a FastAPI async service and MCP server with trace artifacts, eval checks, and tests, enabling async job execution, report retrieval, workflow observability, and engineering-grade quality gates.  

### Version C: Technical-depth
- Designed a LangGraph `StateGraph` multi-agent orchestration pipeline that decomposes `Parser / Planner / Risk / Reviewer / Reporter` into isolated nodes and connects them with fan-out/fan-in execution and conditional routing, turning fragmented PRD review and delivery-planning steps into a single controllable backend workflow.  
- Built a structured LLM execution path with tool/function-calling first, text-JSON fallback, `json_repair`, and Pydantic schema validation, addressing schema drift, malformed JSON, and provider capability variance while keeping parser/planner/risk/reviewer outputs schema-compatible.  
- Implemented a risk-driven routing loop that re-enters a clarification pass when review results remain high-risk, creating an auditable workflow-control mechanism with recorded routing history rather than a single-pass agent chain.  
- Encapsulated local risk-catalog retrieval behind a `Skill Registry + SkillExecutor` abstraction with trace metadata, graceful degradation, and process-local TTL cache, allowing the risk agent to stay evidence-grounded without making the full workflow depend on tool availability.  
- Extracted a reusable `risk_analysis` subgraph for “evidence retrieval -> risk generation” and integrated it into the main graph, while running planner and risk branches in parallel and exposing runtime metrics for latency, cache hits/misses, and parallel execution behavior.  
- Exposed the workflow through FastAPI async endpoints and an MCP stdio server, supporting request submission, status polling, artifact retrieval, and standardized outputs including `report.md`, `report.json`, and `run_trace.json`.  
- Added trace artifacts, regression evals, and unit tests across schema validation, routing, risk-tool behavior, caching, MCP integration, and runtime metrics, giving the agent system a practical observability and verification layer for iterative releases.  

详细 bullet-to-code mapping 见独立 mapping 文件。

## Resume Usage Guide

- `Version B` 最适合直接贴到一页技术简历；长度和信息密度更接近正式简历 bullet。
- `Version A` 适合放在项目标题下方做 2 行总述，或用于网申系统的“项目简介”栏。
- `Version C` 适合面试展开、项目答辩、技术博客或长版简历，不建议整段直接贴到一页简历首屏。
- 如果只保留 3 条，建议保留 `Version B` 的第 1、2、4 条。
- 如果只保留 3 条且想强调性能工程，可将 `Version B` 的第 3 条并入第 1 条，或用第 3 条替换第 2 条。
