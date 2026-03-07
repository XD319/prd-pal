# AI Requirement Review and Delivery Orchestration Backend

## 中文版本

### Version A: 2 行极简版
1. 设计并实现面向 PRD 评审、交付规划、审批流与执行交接的 AI 后端系统，基于统一 orchestrator 调度 requirement analysis、risk assessment、delivery bundle 生成与 coding-agent handoff。  
2. 将 Skills、结构化输出校验、traceability、approval gate、FastAPI、MCP 与评测测试体系整合为可落地的工程化工作流，支持从需求评审到交付准备的标准化闭环。  

### Version B: 简历标准版
- 面向 PRD 评审、交付规划和执行交接链路分散、人工同步成本高的问题，设计 AI requirement review and delivery orchestration backend，统一完成需求解析、风险识别、任务拆解、交付物生成与 coding-agent handoff。  
- 构建 `Single Orchestrator + Skills` 能力架构，将 implementation planning、test planning、risk evidence retrieval、prompt handoff、delivery bundle generation 等能力模块化，并通过 schema validation、fallback、TTL cache 与 trace 保证工作流稳定性。  
- 落地标准化交付物与最小审批闭环，输出 `prd_review_report`、`open_questions`、`scope_boundary`、`tech_design_draft`、`test_checklist`、`delivery_bundle` 等 artifacts，引入 `draft / need_more_info / approved / blocked_by_risk` 状态管理。  
- 实现 FastAPI async service 与 MCP server 双入口，支持 PRD 提交、运行追踪、审批确认、handoff 查询与 execution status 回读，并补齐 traceability、eval 和测试体系，形成可集成的 AI backend service。  

### Version C: 技术深度版
- 设计以统一 orchestrator 为核心的 AI workflow backend，将 requirement parsing、risk analysis、review、delivery planning、approval gate、handoff routing 和 execution tracking 组织为可观测、可回归的状态机流程，而不是单纯堆叠多个独立 agent。  
- 构建 `Skill Registry + SkillExecutor` 能力层，封装 `implementation.plan`、`test.plan.generate`、`risk_catalog.search`、`codex.prompt.generate`、`delivery_bundle.generate` 等 Skills，支持输入输出 schema 约束、trace 注入、graceful degradation 和进程内 TTL cache。  
- 为解决 LLM 输出不稳定与流程不可落盘的问题，建立 Structured Outputs + Pydantic validation + fallback parsing 链路，并将审查结果、交付物、审批状态、handoff 记录与 execution task 映射到可查询的结构化 artifacts。  
- 推进交付物标准化，拆分并生成 `prd_review_report.md`、`open_questions.md`、`scope_boundary.md`、`tech_design_draft.md`、`test_checklist.md` 和 `delivery_bundle.json`，使需求评审结果能够直接作为人工审批和下游执行的 source of truth。  
- 引入最小审批闭环与 traceability map，打通 `requirement -> review item -> dev task -> test item -> execution task` 链路，支持 `approved / need_more_info / blocked_by_risk` 等状态流转，提升 AI 产物可审计性和协作可控性。  
- 在交付执行侧实现 handoff orchestration，支持 `agent_assisted / human_only / agent_auto` 模式切换、executor routing、execution status 查询与回写，将系统能力从“生成 handoff 文件”扩展到“管理 handoff 流程”。  
- 通过 FastAPI 异步接口、MCP tools、trace artifacts、回归 eval 和单元测试覆盖关键链路，包括 schema validation、skills cache、approval transition、traceability persistence、handoff rendering 与 execution orchestration，形成可工程化复用的 AI backend。  

---

## English Version

### Version A: 2-line concise
1. Built an AI backend for PRD review, delivery planning, approval gating, and execution handoff, using a single orchestrator to coordinate requirement analysis, risk assessment, delivery-bundle generation, and coding-agent handoff.  
2. Productized the workflow with modular skills, structured-output validation, traceability, approval states, FastAPI, MCP integration, and eval/test coverage to support a standardized requirement-to-delivery-prep loop.  

### Version B: Resume-ready
- Built an AI requirement-review and delivery-orchestration backend to reduce fragmented PRD analysis, planning, and handoff workflows, turning requirement parsing, risk assessment, task decomposition, artifact generation, and coding-agent handoff into one controlled service flow.  
- Designed a `Single Orchestrator + Skills` architecture, modularizing capabilities such as implementation planning, test planning, risk evidence retrieval, prompt handoff, and delivery-bundle generation, with schema validation, fallback handling, TTL cache, and trace instrumentation for reliability.  
- Standardized delivery artifacts and introduced a minimum approval loop by generating `prd_review_report`, `open_questions`, `scope_boundary`, `tech_design_draft`, `test_checklist`, and `delivery_bundle`, with lifecycle states including `draft`, `need_more_info`, `approved`, and `blocked_by_risk`.  
- Exposed the system through FastAPI async APIs and an MCP server, supporting PRD submission, run tracking, approval actions, handoff retrieval, and execution-status queries, backed by traceability, eval checks, and automated tests.  

### Version C: Technical-depth
- Architected an AI workflow backend around a single orchestrator that coordinates requirement parsing, risk analysis, review, delivery planning, approval gates, handoff routing, and execution tracking as a controllable state-machine flow rather than presenting the system as loosely coupled autonomous agents.  
- Built a `Skill Registry + SkillExecutor` capability layer to encapsulate skills such as `implementation.plan`, `test.plan.generate`, `risk_catalog.search`, `codex.prompt.generate`, and `delivery_bundle.generate`, with strict input/output schemas, trace injection, graceful degradation, and in-process TTL caching.  
- Implemented a structured LLM execution path using structured outputs, Pydantic validation, and fallback parsing to reduce malformed-response failures, then persisted review outputs, delivery artifacts, approval records, handoff data, and execution-task metadata as queryable structured artifacts.  
- Standardized delivery outputs into `prd_review_report.md`, `open_questions.md`, `scope_boundary.md`, `tech_design_draft.md`, `test_checklist.md`, and `delivery_bundle.json`, making the review result usable as the source of truth for human approval and downstream execution.  
- Added a minimal approval loop and a traceability map spanning `requirement -> review item -> dev task -> test item -> execution task`, improving auditability, workflow control, and cross-role collaboration for AI-generated delivery artifacts.  
- Extended the system from "handoff file generation" to "handoff process management" with executor routing, `agent_assisted / human_only / agent_auto` execution modes, execution-status tracking, and state write-back.  
- Productized the backend with FastAPI async endpoints, MCP tools, trace artifacts, regression evals, and automated tests across schema validation, skill caching, approval transitions, traceability persistence, handoff rendering, and execution orchestration.  

## Resume Usage Guide

- `Version B` 适合直接放在一页中文或英文技术简历中，叙事重点是 AI backend、workflow orchestration、skills、approval、traceability。  
- `Version A` 适合放在项目标题下的两行摘要，或者网申系统的项目简介字段。  
- `Version C` 适合面试展开、项目答辩、技术博客或长版简历，不建议整段直接塞进首页简历。  
- 如果只保留 3 条 bullet，优先保留 `Version B` 的第 1、2、4 条；它们最能覆盖业务价值、架构设计和工程落地。  
- 如果想强调“不是 AI demo，而是工程化系统”，优先突出 `approval loop`、`traceability`、`execution orchestration` 和 `FastAPI/MCP`。  
