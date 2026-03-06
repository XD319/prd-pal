# Multi-Agent Requirement Review 面试题（V3）

## 目录
- [变更说明](#sec-changelog)
- [简历重点题速查](#sec-resume-priority)
- [简历覆盖映射](#sec-resume-sync)
- [新增题目索引](#sec-new-index)
- [第一部分：系统设计](#sec-system-design)
  - [Q1. 系统整体架构是什么？数据如何流动？](#q1)
  - [Q2. 为什么用 LangGraph 多智能体工作流，而不是单 Agent 或脚本链？](#q2)
  - [Q3. clarify loop / routing loop 为什么单独设计成工作流控制层？](#q3)
- [第二部分：LLM 工程](#sec-llm-engineering)
  - [Q4. Structured Outputs + schema validation + fallback 是怎么协同的？](#q4)
  - [Q5. 为什么要把风险判断建立在 tool-based evidence retrieval 上？](#q5)
- [第三部分：Agent 与 Workflow 设计](#sec-agent-workflow)
  - [Q6. 为什么要做 Skill Registry / SkillExecutor？](#q6)
  - [Q7. 为什么缓存放在 SkillExecutor，而不是 agent 内部？TTL 缓存边界是什么？](#q7)
  - [Q8. reusable subflow / subgraph 的价值是什么？](#q8)
  - [Q9. 并行化是如何实现的？为什么选择 planner 和 risk 并行？如何避免 state 冲突？](#q9)
- [第四部分：生产化与平台化](#sec-production)
  - [Q10. FastAPI async service 和 MCP server 分别解决什么问题？](#q10)
  - [Q11. 为什么 trace / eval / tests 在这套系统里是核心能力，而不是附属功能？](#q11)
- [第五部分：Debug 与排障](#sec-debug)
  - [Q12. 结构化输出异常、工具降级、路由异常时怎么排查？](#q12)
  - [Q13. 并行与缓存引入后，最容易出现哪些新型问题？如何定位？](#q13)
- [第六部分：Performance Engineering](#sec-performance)
  - [PE-1. eval 为什么慢，优先怎么优化？](#qpe-1)
  - [PE-2. 为什么并行化不能乱加？](#qpe-2)
  - [PE-3. 为什么缓存先做内存 TTL，再考虑持久化？](#qpe-3)
  - [PE-4. cache hit/miss 为什么必须进入 trace 与 metrics？](#qpe-4)
- [第七部分：Architecture Evolution](#sec-architecture-evolution)
  - [AE-1. v1 -> v2 -> v3 的架构演进逻辑是什么？](#qae-1)
  - [AE-2. 为什么 v3 要走平台化，而不是继续堆单点功能？](#qae-2)
  - [AE-3. 为什么 v3 适合单独开分支开发？如何避免“功能越做越碎”？](#qae-3)

<a id="sec-changelog"></a>
## 变更说明

- 本版以最新简历文件 `docs/resume_project_description_ai_backend.md` 为基线，对齐 Version B / Version C 的表达重点。
- `resume_project_description_ai_backend_v3.md` 仓库中不存在，因此本版使用当前最新简历描述作为 v3 简历来源。
- 在 `docs/interview-prep-v2.1.md` 的基础上，补强了 v3 核心主题：Skill Registry / SkillExecutor、TTL cache、reusable subflow、planner/risk 并行、runtime metrics、Architecture Evolution。
- 题目结构统一为：问题、简要回答、技术要点、Follow-ups、Trade-offs、System Variants、Pitfalls，便于直接背诵或面试展开。

<a id="sec-resume-priority"></a>
## 简历重点题速查

- 简历 Version B #1「LangGraph 多智能体工作流 + 澄清路由」：优先准备 [Q1](#q1)、[Q2](#q2)、[Q3](#q3)、[Q9](#q9)、[AE-1](#qae-1)
- 简历 Version B #2「Structured Outputs + schema validation + fallback」：优先准备 [Q4](#q4)、[Q12](#q12)
- 简历 Version B #3「skill / evidence retrieval / subflow / parallel / TTL cache」：优先准备 [Q5](#q5)、[Q6](#q6)、[Q7](#q7)、[Q8](#q8)、[Q9](#q9)、[PE-2](#qpe-2)、[PE-3](#qpe-3)、[PE-4](#qpe-4)
- 简历 Version B #4「FastAPI async service + MCP + trace / eval / tests」：优先准备 [Q10](#q10)、[Q11](#q11)、[Q12](#q12)、[Q13](#q13)、[PE-1](#qpe-1)、[PE-4](#qpe-4)、[AE-2](#qae-2)

- 简历 Version C #1「StateGraph 多智能体编排」：优先准备 [Q1](#q1)、[Q2](#q2)
- 简历 Version C #2「结构化调用链路」：优先准备 [Q4](#q4)、[Q12](#q12)
- 简历 Version C #3「risk-driven routing loop」：优先准备 [Q3](#q3)、[AE-1](#qae-1)
- 简历 Version C #4「Skill Registry / SkillExecutor / TTL cache」：优先准备 [Q5](#q5)、[Q6](#q6)、[Q7](#q7)、[Q13](#q13)、[PE-3](#qpe-3)、[PE-4](#qpe-4)
- 简历 Version C #5「reusable subflow / parallelization / runtime metrics」：优先准备 [Q8](#q8)、[Q9](#q9)、[Q11](#q11)、[PE-2](#qpe-2)、[PE-4](#qpe-4)
- 简历 Version C #6「FastAPI + MCP 平台化」：优先准备 [Q10](#q10)、[AE-2](#qae-2)
- 简历 Version C #7「trace / eval / tests」：优先准备 [Q11](#q11)、[Q12](#q12)、[PE-1](#qpe-1)、[AE-3](#qae-3)

提示  
- 如果只按一页简历的 `Version B` 准备，至少把 [Q1](#q1)、[Q4](#q4)、[Q6](#q6)、[Q7](#q7)、[Q9](#q9)、[Q10](#q10)、[Q11](#q11) 练熟。
- 如果面试更偏系统设计 / AI 后端，再重点补 [PE-2](#qpe-2)、[PE-3](#qpe-3)、[PE-4](#qpe-4)、[AE-1](#qae-1)、[AE-2](#qae-2)、[AE-3](#qae-3)。

<a id="sec-resume-sync"></a>
## 简历覆盖映射

- Resume Version B #1 / Version C #1 / #3：Q1、Q2、Q3、Q9、AE-1
- Resume Version B #2 / Version C #2：Q4、Q12
- Resume Version B #3 / Version C #4 / #5：Q5、Q6、Q7、Q8、Q9、PE-2、PE-3、PE-4
- Resume Version B #4 / Version C #6 / #7：Q10、Q11、Q12、Q13、PE-1、PE-4、AE-2

<a id="sec-new-index"></a>
## 新增题目索引

- 新增：Q6 Skill Registry / SkillExecutor 的设计动机
- 新增：Q7 缓存为什么放在 SkillExecutor、TTL 边界、cache key 设计
- 新增：Q8 reusable subflow / subgraph 的价值
- 重构增强：Q9 并行化实现、并行节点选择、state 冲突规避
- 重构增强：Q11 trace / eval / tests 与并行化、缓存的关系
- 新增：Q13 并行与缓存引入后的排障思路
- 新增：PE-1 eval 为什么慢，怎么优化
- 新增：PE-2 为什么并行化不能乱加
- 新增：PE-3 为什么先做内存 TTL cache
- 新增：PE-4 cache hit/miss 如何纳入 trace 与 metrics
- 新增：AE-1 v1 -> v2 -> v3 架构演进
- 新增：AE-2 为什么 v3 需要平台化
- 新增：AE-3 为什么 v3 单独开分支开发，以及如何避免功能碎片化

<a id="sec-system-design"></a>
## 第一部分：系统设计

<a id="q1"></a>
### Q1. 系统整体架构是什么？数据如何流动？
【Resume Highlight】Version B #1，Version B #4；Version C #1，#6，#7

问题  
请从入口、编排、执行、产物四层说明系统主链路。

简要回答  
系统是“FastAPI/MCP 入口 + LangGraph 编排 + 多 Agent/Skill 执行 + artifacts/trace/eval”四层结构。请求进入 service 层后触发 `workflow.py` 中的状态图，主链路经历 parser、planner、risk、reviewer、route_decider、reporter，最终落盘报告、状态快照和执行追踪，并由 eval/tests 校验关键约束。

技术要点  
- 编排入口：`requirement_review_v1/workflow.py`
- 共享状态与并行 merge：`requirement_review_v1/state.py`
- 运行与落盘：`requirement_review_v1/run_review.py`、`requirement_review_v1/service/review_service.py`
- 服务入口：`requirement_review_v1/server/app.py`、`requirement_review_v1/mcp_server/server.py`
- 观测与质量：`requirement_review_v1/utils/trace.py`、`eval/run_eval.py`、`tests/`

Follow-ups
- F1. 为什么把编排逻辑放在 `workflow.py`，而不是放进 API 层？
  简要回答  
  这样 HTTP、MCP、CLI 都能共享同一套工作流契约，避免入口不同导致业务行为漂移。
  技术要点  
  编排层在 `workflow.py`，入口适配在 `server/app.py`、`mcp_server/server.py`，执行封装在 `service/review_service.py`。
- F2. 为什么 service 层要单独存在？
  简要回答  
  service 层把“如何调用工作流”和“如何暴露接口”拆开，便于复用、测试和后续替换入口。
  技术要点  
  `review_service.py` 对外返回 `ReviewResultSummary`，MCP 和 FastAPI 只消费统一摘要结构。

Trade-offs
- T1. 这种分层会不会让调用链更长？
  简要回答  
  会增加少量代码层级，但换来的是入口复用、回归一致性和更清晰的排障边界，收益明显大于额外复杂度。

System Variants
- S1. 如果以后改成队列 + worker 架构，哪些边界可以不动？
  简要回答  
  可以保留 `run_id -> workflow result -> artifacts` 主契约，只替换任务调度方式；`review_service.py` 仍然是最稳定的复用边界。

Pitfalls
- 只讲 Agent 顺序，不讲 service、workflow、artifacts 之间的工程边界。
- 把系统说成“一个 API 调一个模型”，会弱化平台化与可观测能力。

<a id="q2"></a>
### Q2. 为什么用 LangGraph 多智能体工作流，而不是单 Agent 或脚本链？
【Resume Highlight】Version B #1；Version C #1

问题  
为什么不让一个大 Prompt 一次性完成解析、规划、风险和评审？

简要回答  
因为这个系统的核心不是“生成一段答案”，而是“控制一条可回溯、可循环、可扩展的工作流”。多 Agent + StateGraph 更适合职责拆分、结构化状态管理、条件路由和后续性能优化，而单 Agent 更难稳定落地到后端服务。

技术要点  
- 节点职责拆分：`requirement_review_v1/agents/*.py`
- 状态驱动编排：`requirement_review_v1/workflow.py`、`requirement_review_v1/state.py`
- 条件路由与循环：`route_decider`、`clarify`
- 复用与扩展空间：`subflows/risk_analysis.py`、`skills/`

Follow-ups
- F1. 为什么不是简单 async pipeline？
  简要回答  
  简单 pipeline 能跑通顺序链路，但对条件跳转、循环回退和分支汇合支持较弱；LangGraph 更像工作流运行时，而不是脚本串调用。
  技术要点  
  `add_conditional_edges` 和 fan-out/fan-in 在 `workflow.py` 中都是一等概念。
- F2. 多 Agent 会不会增加延迟？
  简要回答  
  会增加一些 orchestration 开销，但也带来了并行化和局部复用机会，v3 已经用 planner/risk 并行部分抵消了这类开销。
  技术要点  
  并行分支与 runtime metrics 在 `workflow.py`、`metrics/runtime.py` 中落地。

Trade-offs
- T1. 单 Agent 的优势是什么？
  简要回答  
  Prompt 更短、原型更快，但状态不透明、可测性差、调试困难，一旦要加澄清循环、工具调用和缓存，维护成本会迅速上升。

System Variants
- S1. 如果只有 parser + reporter 两步，还值得用 LangGraph 吗？
  简要回答  
  小规模链路可以不用，但当前系统已经有条件路由、并行和子流复用，LangGraph 的收益已经超过它的引入成本。

Pitfalls
- 把“多 Agent”解释成只是“多模型调用”；重点应是 workflow control，不是调用次数。
- 忽略 StateGraph 带来的条件边、并行和状态合并能力。

<a id="q3"></a>
### Q3. clarify loop / routing loop 为什么单独设计成工作流控制层？
【Resume Highlight】Version B #1；Version C #3

问题  
为什么不把澄清逻辑写死在 parser 或 reviewer 里面，而要做 `route_decider` + `clarify`？

简要回答  
因为澄清不是单个 Agent 的局部行为，而是整条工作流的控制策略。把它抽成独立控制层后，循环条件、最大轮次、路由结果都能被统一记录和测试，避免“模型自己决定要不要再来一轮”的黑箱行为。

技术要点  
- 路由判断：`requirement_review_v1/workflow.py`
- 风险阈值与最大轮次：`_HIGH_RISK_THRESHOLD`、`_MAX_REVISION_ROUNDS`
- 回归验证：`tests/test_routing_loop.py`
- 相关状态字段：`ReviewState.revision_round`、`high_risk_ratio`、`routing_reason`

Follow-ups
- F1. 为什么用 Reviewer 的风险比例做 loop 触发器？
  简要回答  
  因为 Reviewer 看到的是“解析结果 + 规划结果”的综合质量，更适合作为是否需要澄清的全局信号。
  技术要点  
  `reviewer_agent.py` 产出风险相关结果，`workflow.py` 统一读取并决定下一跳。
- F2. 为什么一定要限制最大轮次？
  简要回答  
  Agent 工作流需要确定的停止条件，否则在高歧义输入下容易无限循环并拉高成本。
  技术要点  
  `_MAX_REVISION_ROUNDS = 2`，并在 `tests/test_routing_loop.py` 中验证上限行为。

Trade-offs
- T1. 把 loop 放在工作流层会不会让流程更复杂？
  简要回答  
  会，但复杂度换来的是可测试和可审计；如果把 loop 埋进 Prompt，很难回答“为什么这一轮又重跑了”。

System Variants
- S1. 如果以后要按 requirement 粒度做局部 clarify，该怎么改？
  简要回答  
  可以把全局 loop 扩展成“局部 requirement repair subflow”，但这属于未来改造，当前代码仍是全局 round 级控制。

Pitfalls
- 只说“为了提升准确率”，没说明它本质上是 workflow control。
- 忽略停止条件与 trace 记录，是面试里最容易被追问的点。

<a id="sec-llm-engineering"></a>
## 第二部分：LLM 工程

<a id="q4"></a>
### Q4. Structured Outputs + schema validation + fallback 是怎么协同的？
【Resume Highlight】Version B #2；Version C #2

问题  
如果面试官问“你怎么保证 LLM 输出能进后端系统”，该怎么回答？

简要回答  
我不是只依赖模型“尽量输出 JSON”，而是做了分层保障：优先走 provider 的 structured/tool calling，失败后退回文本 JSON 解析，再用 `json_repair` 修复格式，最后通过 Pydantic schema validation 做契约校验。这样可以把“模型能不能生成”和“系统能不能消费”分开处理。

技术要点  
- 统一调用入口：`requirement_review_v1/utils/llm_structured_call.py`
- schema 定义与校验：`requirement_review_v1/schemas/*.py`
- 测试：`tests/test_schema_validation.py`、`tests/test_schemas.py`
- 异常路径：`StructuredCallError`、raw output 持久化

Follow-ups
- F1. 为什么 schema validation 不能省？
  简要回答  
  因为即使 JSON 可解析，也可能字段缺失、类型错误或枚举越界；不做 schema validation，后面的 Agent 会在更远处炸掉。
  技术要点  
  `validate_parser_output`、`validate_planner_output`、`validate_risk_output`、`validate_reviewer_output`
- F2. fallback 会不会掩盖模型真实问题？
  简要回答  
  不会，fallback 只是维持主流程可运行；失败信息和 raw output 仍会进入 trace，便于后续定位模型侧问题。
  技术要点  
  `save_raw_agent_output`、`trace.raw_output_path`、`StructuredCallError`

Trade-offs
- T1. 为什么不直接强绑定单一 provider 的原生 structured API？
  简要回答  
  单 provider 路径更简单，但迁移性差；当前实现保留 provider 能力优先，同时提供跨 provider 的兜底路径，工程弹性更强。

System Variants
- S1. 如果以后引入更强的 JSON-mode provider，还需要 fallback 吗？
  简要回答  
  仍建议保留。fallback 是系统级保险，不应被当作“某个模型表现好所以不需要”的一次性逻辑。

Pitfalls
- 把 Structured Outputs 说成“让模型更听话”；更准确的说法是“把 LLM 输出纳入工程契约”。
- 忽略 repair 和 schema validation 的区别。

<a id="q5"></a>
### Q5. 为什么要把风险判断建立在 tool-based evidence retrieval 上？
【Resume Highlight】Version B #3；Version C #4

问题  
Risk Agent 为什么不直接靠 Prompt 总结风险，而要加本地风险目录检索？

简要回答  
因为风险分析最怕“说得像、但没依据”。接入 tool-based evidence retrieval 后，Risk Agent 的结论不只是模型主观判断，而是尽量绑定到已有风险模式和缓解经验上，提升 grounding、解释性和后续排查能力。

技术要点  
- 本地检索工具：`requirement_review_v1/tools/risk_catalog_search.py`
- Skill 封装：`requirement_review_v1/skills/risk_catalog.py`
- 子流接入：`requirement_review_v1/subflows/risk_analysis.py`
- 测试：`tests/test_risk_tool.py`

Follow-ups
- F1. 工具检索不到结果怎么办？
  简要回答  
  系统会降级为无证据或弱证据模式，而不是直接中断主流程。
  技术要点  
  `tool_status`、graceful degradation、`degraded_disabled` / `degraded_error`
- F2. 为什么用本地 catalog，而不是直接联网搜索？
  简要回答  
  本地 catalog 更稳定、可控、成本低，也更适合回归测试；联网搜索更强但波动更大，当前不在 v3 范围内。
  技术要点  
  当前真实实现是本地 risk catalog；外部搜索属于未来扩展。

Trade-offs
- T1. 证据检索会不会把模型限制死？
  简要回答  
  不会，它提供的是 grounding，不是硬规则；模型仍负责综合当前计划和历史模式生成风险结论。

System Variants
- S1. 如果以后要支持企业私有风险知识库，应该改哪里？
  简要回答  
  优先扩展 skill 层而不是改 Agent Prompt，本地 catalog 可替换为企业检索后端，Agent 契约基本保持不变。

Pitfalls
- 把 evidence retrieval 说成完整 RAG；这里更准确是工具增强的局部 grounding。
- 忽略降级模式，面试官会追问工具失败时系统是否还能运行。

<a id="sec-agent-workflow"></a>
## 第三部分：Agent 与 Workflow 设计

<a id="q6"></a>
### Q6. 为什么要做 Skill Registry / SkillExecutor？
【Resume Highlight】Version B #3；Version C #4

问题  
为什么不在 `risk_agent.py` 或 `risk_analysis.py` 里直接调用 `search_risk_catalog`，而要额外加 Registry 和 Executor？

简要回答  
因为 v3 的目标已经不是“先把工具调起来”，而是把工具能力做成可注册、可校验、可缓存、可追踪、可复用的系统组件。Skill Registry 负责统一声明能力，SkillExecutor 负责统一执行策略，这样工具逻辑就不会散落在各个 Agent 里。

技术要点  
- 技能注册：`requirement_review_v1/skills/registry.py`
- 技能执行：`requirement_review_v1/skills/executor.py`
- 风险检索 skill：`requirement_review_v1/skills/risk_catalog.py`
- 技能消费方：`requirement_review_v1/subflows/risk_analysis.py`

Follow-ups
- F1. Skill Registry 带来的最直接收益是什么？
  简要回答  
  它把“工具长什么样、输入输出是什么、版本是什么、是否可缓存”统一起来，后续新增 skill 时不需要重写一套执行框架。
  技术要点  
  `SkillSpec` 统一声明 `name / input_model / output_model / handler / config_version / cache_ttl_sec`
- F2. SkillExecutor 为什么比“一个 utils 函数”更合适？
  简要回答  
  因为 executor 不只是调用 handler，它还要做输入校验、输出校验、TTL 缓存、trace 写入和异常收口。
  技术要点  
  `execute()` 中包含 validate、cache、trace、error handling 四层责任。

Trade-offs
- T1. 这会不会对只有一个工具的项目来说太重？
  简要回答  
  如果只有一次性脚本，确实偏重；但一旦要做多个工具、MCP/FastAPI 复用和缓存治理，这层抽象会很快回本。

System Variants
- S1. 如果未来要支持多个 skill provider，这一层怎么演进？
  简要回答  
  可以继续保留 `SkillSpec` 作为统一契约，把不同 provider 的 handler 挂到 registry 上，避免 Agent 直接感知底层实现差异。

Pitfalls
- 把 Registry/Executor 说成“为了好看”；重点是统一治理，而不是抽象炫技。
- 忽略校验、trace、cache，这三项才是 SkillExecutor 的真实价值。

<a id="q7"></a>
### Q7. 为什么缓存放在 SkillExecutor，而不是 agent 内部？TTL 缓存边界是什么？
【Resume Highlight】Version B #3；Version C #4

问题  
为什么缓存不直接写在 Risk Agent 里？为什么两次独立 CLI 进程不会命中缓存？

简要回答  
缓存放在 SkillExecutor 是因为缓存的是“技能调用结果”，不是某个 Agent 的局部状态。把缓存下沉到 executor 后，多个 Agent 或子流只要使用同一 skill 契约，就能共享同一套 cache key、trace 和失效策略。当前缓存是进程内 TTL cache，只在当前 Python 进程生命周期内有效，所以两次独立 CLI 进程天然不会共享命中结果。

技术要点  
- TTL cache：`requirement_review_v1/skills/executor.py`
- roadmap 约束：`docs/v3-roadmap.md`
- 缓存测试：`tests/test_skills_cache.py`、`tests/test_risk_tool.py`
- 长生命周期复用场景：FastAPI / MCP 进程

Follow-ups
- F1. cache key 为什么要包含 skill name / input / config / version？
  简要回答  
  因为同一个输入在不同 skill、不同配置版本下不一定语义等价；只用输入做 key 容易产生跨技能或跨版本污染。
  技术要点  
  `_build_cache_key_hash()` 使用 `spec.name + canonical_input_json + spec.config_version`
- F2. 为什么不用 run_id 做 cache key？
  简要回答  
  run_id 会让缓存退化成“每次请求一份”，失去跨请求复用价值；skill cache 更适合按能力语义建 key，而不是按任务实例建 key。
  技术要点  
  当前 key 不含 run_id，这是有意保留的复用能力。

Trade-offs
- T1. 进程内 TTL cache 的局限是什么？
  简要回答  
  它简单、低成本、易测试，但不能跨进程复用，也不适合做分布式一致性；这正是 roadmap 中未来持久化缓存的演进空间。

System Variants
- S1. 如果要做 Redis 持久化缓存，最应该保留哪些边界？
  简要回答  
  应保留 `SkillExecutor.execute()` 这个统一入口，只替换底层 cache backend，而不是让 Agent 直接接 Redis。

Pitfalls
- 把 TTL cache 说成“全局共享缓存”；当前实现只在同一进程内共享。
- 忽略缓存污染问题，cache key 设计是面试高频追问点。

<a id="q8"></a>
### Q8. reusable subflow / subgraph 的价值是什么？
【Resume Highlight】Version B #3；Version C #5

问题  
为什么 v3 要引入 `risk_analysis` subflow，而不是继续把逻辑都写在 Risk Agent 里？

简要回答  
因为“证据检索 -> 风险生成”本身已经形成了稳定的组合能力，适合抽成子流。抽出来之后，主图只关心何时调用风险分析，而子流内部可以独立演进 retrieval、生成、trace 和缓存策略，复用性和演进速度都会更好。

技术要点  
- 子流实现：`requirement_review_v1/subflows/risk_analysis.py`
- 主图接入：`requirement_review_v1/workflow.py`
- 子流标识：`subflow_id = "risk_analysis.v1"`
- 子流契约测试：`tests/test_risk_tool.py`

Follow-ups
- F1. subgraph 和普通 helper function 的区别是什么？
  简要回答  
  helper function 只复用代码，subgraph 复用的是“执行结构”，包括节点、trace、输入输出契约和后续扩展点。
  技术要点  
  `build_risk_analysis_subgraph()` 返回可编译图，而不是单个函数。
- F2. 子流为什么适合风险分析，而不一定适合所有 Agent？
  简要回答  
  风险分析天然包含工具检索和生成两个阶段，结构比 parser/planner 更复合，更适合抽象成子流。
  技术要点  
  当前仅 risk analysis 做了 subflow；其他节点仍保持单 Agent 结构。

Trade-offs
- T1. 引入 subgraph 会不会让调试链路更深？
  简要回答  
  会，但 trace 中记录了 `subflow_id` 和 node_path，复杂度增加是可控的，换来的是更好的复用和边界清晰度。

System Variants
- S1. 未来还有哪些能力适合抽成子流？
  简要回答  
  比如 requirement clarification 或 plan review，都可能演进成独立 subflow；当前仓库里尚未实现，属于未来改造方向。

Pitfalls
- 把 subflow 仅理解为“函数抽取”；真正价值在于 workflow 级复用。
- 不要声称仓库已经有多个 subgraph；当前真实实现的是 `risk_analysis`。

<a id="q9"></a>
### Q9. 并行化是如何实现的？为什么选择 planner 和 risk 并行？如何避免 state 冲突？
【Resume Highlight】Version B #3；Version C #5

问题  
请解释 v3 的并行化设计、节点选择依据，以及 state merge 如何避免冲突。

简要回答  
v3 在 parser 之后做 fan-out，让 planner 和 risk 并行执行，再在 `review_join` 做 fan-in。选择这两个节点，是因为它们都依赖 parser 结果，但彼此不直接依赖。为了避免 state 冲突，v3 一方面让并行分支尽量写不同的主状态域，另一方面在 `ReviewState` 中为 `trace` 和 `evidence` 定义了 merge reducer，确保分支结果能按字典合并，而不是互相覆盖。

技术要点  
- 并行图：`requirement_review_v1/workflow.py`
- merge reducer：`requirement_review_v1/state.py`
- runtime metrics：`requirement_review_v1/metrics/runtime.py`
- 验证：`tests/test_metrics_runtime.py`

Follow-ups
- F1. 为什么不是 reviewer 和 risk 并行？
  简要回答  
  reviewer 依赖规划与风险结果，语义上在 join 之后更合理；而 planner 和 risk 都可直接消费 parser 输出，所以并行收益更自然。
  技术要点  
  `review_join` 之后才进入 `reviewer`
- F2. 如果两个并行节点都写同一个 state key，会发生什么？
  简要回答  
  如果没有 reducer，容易出现后写覆盖；这也是为什么 v3 只对 `trace`、`evidence` 这类聚合字段定义 merge，并避免让并行分支写同一业务字段。
  技术要点  
  `trace: Annotated[..., merge_state_dicts]`、`evidence: Annotated[..., merge_state_dicts]`

Trade-offs
- T1. 并行化为什么不能继续往下扩？
  简要回答  
  因为不是所有节点都真正独立。错误并行会引入语义错误、状态冲突和更难解释的 trace，收益未必大于复杂度。

System Variants
- S1. 如果后续要进一步并行，会优先看什么？
  简要回答  
  先看依赖关系、写入状态域、可观测性是否足够，再看 latency 是否真的构成瓶颈；不能只凭“理论上可并行”就改图。

Pitfalls
- 只说“用了并行，速度更快”，不解释为什么选择这两个节点。
- 忽略 `merge_state_dicts`，这是并行 state 安全的关键落点。

<a id="sec-production"></a>
## 第四部分：生产化与平台化

<a id="q10"></a>
### Q10. FastAPI async service 和 MCP server 分别解决什么问题？
【Resume Highlight】Version B #4；Version C #6

问题  
为什么两个入口都要做？它们分别服务什么场景？

简要回答  
FastAPI async service 解决的是标准后端集成和异步任务管理问题，适合 Web/业务系统调用；MCP server 解决的是 AI 客户端和 Agent 平台接入问题，适合 Claude Desktop、MCP-compatible client 之类的工具生态。两者共享同一 service 层，所以能力一致、入口不同。

技术要点  
- FastAPI：`requirement_review_v1/server/app.py`
- MCP：`requirement_review_v1/mcp_server/server.py`
- 共享执行层：`requirement_review_v1/service/review_service.py`
- MCP 报告读取：`requirement_review_v1/service/report_service.py`

Follow-ups
- F1. FastAPI 为什么要做异步任务，而不是同步阻塞返回？
  简要回答  
  评审链路包含多次 LLM 调用和文件落盘，天然是长任务；异步模式更适合生产环境的超时控制、轮询查询和前端集成。
  技术要点  
  `create_review()` 创建后台 task，`get_review_status()` 轮询状态
- F2. MCP 工具为什么要提供 `get_report`？
  简要回答  
  因为 AI 客户端除了触发任务，还需要读取结果；把报告读取也标准化后，客户端可以做二次 summarization 或继续串联其他 Agent。
  技术要点  
  `mcp_server/server.py` 中的 `review_prd` 与 `get_report`

Trade-offs
- T1. 双入口会不会增加维护成本？
  简要回答  
  会，但通过共享 service 层把成本压在传输层适配上，而不是复制整套业务逻辑，这个取舍是值得的。

System Variants
- S1. 如果以后只保留一个入口，你更倾向保留哪个？
  简要回答  
  取决于业务形态。如果面向传统后端系统集成，优先保留 FastAPI；如果面向 AI 工具生态，优先保留 MCP。

Pitfalls
- 只回答“一个是 API，一个是 MCP”，但没说明它们解决的是不同集成场景。
- 忽略两者复用 `review_service.py` 的工程边界。

<a id="q11"></a>
### Q11. 为什么 trace / eval / tests 在这套系统里是核心能力，而不是附属功能？
【Resume Highlight】Version B #4；Version C #7

问题  
为什么这些能力在 Agent 系统里尤其重要？为什么对并行化和缓存更重要？

简要回答  
因为 Agent 系统的问题往往不是“有没有结果”，而是“为什么这次这样跑、上次那样跑”。一旦引入并行、缓存、降级和条件路由，没有 trace 就很难解释路径，没有 eval/tests 就很难判断改动是否破坏了行为。它们在 v3 里已经从辅助工具变成运行时治理能力。

技术要点  
- trace：`requirement_review_v1/utils/trace.py`
- runtime metrics：`requirement_review_v1/metrics/runtime.py`
- eval：`eval/run_eval.py`
- 测试：`tests/test_schema_validation.py`、`tests/test_routing_loop.py`、`tests/test_risk_tool.py`、`tests/test_skills_cache.py`、`tests/test_metrics_runtime.py`

Follow-ups
- F1. 为什么 trace 对并行化尤其关键？
  简要回答  
  因为并行后仅看最终结果看不出分支时序、重叠区间和 join 是否正确；必须依赖 trace 才能判断并行到底有没有真实收益。
  技术要点  
  `planner_risk_parallel` span 与 `parallel_enabled` 指标
- F2. 为什么 trace 对缓存也关键？
  简要回答  
  因为缓存命中与否会直接影响 latency 和工具调用次数；如果不把 hit/miss 写进 trace，很难证明优化是否生效，甚至无法区分“真的快了”还是“没执行”。
  技术要点  
  `cache_hit`、`cache_hit_count`、`cache_miss_count`

Trade-offs
- T1. 这些保障会不会拖慢开发速度？
  简要回答  
  短期会增加一些实现成本，但能显著降低后续调试和回归成本，尤其在多 Agent 系统中收益非常高。

System Variants
- S1. 如果以后接入 LangSmith / OpenTelemetry，还要保留现有 trace 吗？
  简要回答  
  建议保留当前最小可控 trace 契约，再做外部平台接入；外部平台是增强，不应替代核心运行时证据。

Pitfalls
- 把 eval/tests 说成“上线前补一下”；这会让面试官觉得你还停留在 demo 阶段。
- 忽略并行和缓存带来的新型不可见行为。

<a id="sec-debug"></a>
## 第五部分：Debug 与排障

<a id="q12"></a>
### Q12. 结构化输出异常、工具降级、路由异常时怎么排查？
【Resume Highlight】Version B #2，Version B #4；Version C #2，#3，#7

问题  
如果线上出现“报告不完整 / 风险为空 / 路由异常”，你会怎么查？

简要回答  
我会按“结构化输出 -> 工具调用 -> 工作流控制 -> artifacts”四层排查。先看 `run_trace` 是否有失败 span，再判断是 schema validation、tool degradation、还是 routing 没按预期触发；必要时再回看 raw output 和 `report.json` 的中间状态。

技术要点  
- schema 与 raw output：`utils/llm_structured_call.py`、`utils/io.py`
- 工具与缓存：`skills/executor.py`、`subflows/risk_analysis.py`
- 路由：`workflow.py`、`tests/test_routing_loop.py`
- artifacts：`report.json`、`run_trace.json`

Follow-ups
- F1. 如果 risk 结果为空，但流程没报错，先查哪里？
  简要回答  
  先看 `trace["risk"]` 和子流 trace，确认是输入为空、工具降级、还是 schema 校验失败后走了空结果兜底。
  技术要点  
  `risk_analysis.generate`、`risk_catalog.search`、`raw_output_path`
- F2. 如果 Structured Outputs fallback 频率变高，你怎么判断是 provider 能力退化还是 Prompt 漂移？
  简要回答  
  先比对 trace 中的 `structured_mode`，再结合近期 prompt / provider 变更定位；如果 tools 模式突然大面积降级，优先怀疑 provider 行为变化。
  技术要点  
  `structured_mode`、`Config`、相关 schema tests

Trade-offs
- T1. 为什么不在第一次异常时就直接抛错终止？
  简要回答  
  对 Agent 系统来说，完整的失败证据往往比立刻抛错更有价值；当前设计优先保留 trace 和可用结果，再由上层决定是否判失败。

System Variants
- S1. 如果要做自动化排障 dashboard，最先聚合哪些信号？
  简要回答  
  先聚合 structured_mode、cache_hit、tool_status、parallel_enabled、span status 这些最能解释路径差异的信号。

Pitfalls
- 一上来就看最终 markdown 报告，不先看 trace。
- 把所有失败都归咎于模型，忽略工具、缓存、路由和落盘链路。

<a id="q13"></a>
### Q13. 并行与缓存引入后，最容易出现哪些新型问题？如何定位？
【Resume Highlight】Version B #3，Version B #4；Version C #4，#5，#7

问题  
v3 相比 v2，新增加的复杂度主要体现在哪里？

简要回答  
主要是三类问题：并行分支合并错误、缓存命中语义错误、以及“性能看起来更快但原因不清”。定位时不能只看最终输出，要同时结合 state merge、cache key、trace span 和 metrics。

技术要点  
- 并行 merge：`state.py`
- cache key/hash：`skills/executor.py`
- parallel/cache metrics：`metrics/runtime.py`
- 相关测试：`tests/test_skills_cache.py`、`tests/test_metrics_runtime.py`

Follow-ups
- F1. 如果出现不该命中的缓存，第一反应查什么？
  简要回答  
  查 cache key 组成是否缺少 skill name 或 config_version，再查输入 canonicalization 是否稳定。
  技术要点  
  `_canonical_input_json()`、`_build_cache_key_hash()`
- F2. 如果并行后结果偶发不一致，怎么排查？
  简要回答  
  先查并行分支是否写了同一 state 域，再看 merge reducer 是否覆盖了所有需要聚合的字段，最后看 trace 时序。
  技术要点  
  `merge_state_dicts()`、`planner_risk_parallel`

Trade-offs
- T1. 引入并行和缓存之后，系统会不会更难解释？
  简要回答  
  会，所以 v3 必须同步补 trace、metrics 和 tests；否则这两类优化只会制造新的黑箱。

System Variants
- S1. 如果后面接入分布式缓存，最担心什么？
  简要回答  
  最担心缓存一致性和错误扩散范围，因为错误命中会从单进程问题升级为跨实例问题。

Pitfalls
- 把性能问题只当成“慢”；很多时候更难的是“为什么这次快/慢”。
- 只看 cache hit，不看命中的正确性。

<a id="sec-performance"></a>
## 第六部分：Performance Engineering

<a id="qpe-1"></a>
### PE-1. eval 为什么慢，优先怎么优化？
【Resume Highlight】Version B #4；Version C #7

问题  
为什么 `eval/run_eval.py` 经常会比想象中慢？

简要回答  
因为 eval 本质上是在批量重跑完整工作流，而不是做离线规则检查。它同时包含多次 LLM 调用、子流执行、文件写入和 metrics 校验，所以成本接近“多次端到端真实运行”的叠加。

技术要点  
- 批量执行：`eval/run_eval.py`
- 工作流本体：`workflow.py`
- 质量检查：`_check_trace_complete()`、`_check_metrics_fields_present()`
- 可观测输出：`eval/runs/*`

Follow-ups
- F1. 优先级最高的优化点是什么？
  简要回答  
  先减少不必要的 LLM 重跑，再考虑局部并行和缓存；也就是说优先做 case 控制、命中缓存、复用长生命周期进程，而不是先改复杂调度。
  技术要点  
  结合 `SkillExecutor` 缓存与服务常驻进程验证
- F2. eval 能不能直接并行跑所有 case？
  简要回答  
  理论上可以，但会引入更多 API 并发、资源竞争和 trace 噪声，当前仓库没有做 case 级并行调度。
  技术要点  
  这属于未来改造，当前 `run_eval.py` 是顺序执行。

Trade-offs
- T1. 为什么不先把 eval 改成 mock-only？
  简要回答  
  mock 能提升速度，但会失去对真实运行时行为的约束；当前 eval 更偏集成验证，不是纯单测替代物。

System Variants
- S1. 如果要做分层 eval，你会怎么拆？
  简要回答  
  拆成 schema/unit、workflow integration、service integration 三层，各层目标不同，避免所有问题都压在端到端 eval 上。

Pitfalls
- 把 eval 慢简单归因于“模型慢”；其实还包括 I/O、落盘、检查和流程长度。
- 忽略“常驻进程更适合验证缓存收益”这一点。

<a id="qpe-2"></a>
### PE-2. 为什么并行化不能乱加？
【Resume Highlight】Version B #3；Version C #5

问题  
既然并行能降延迟，为什么不把更多节点都并起来？

简要回答  
因为并行化的前提是语义独立和状态安全。很多节点虽然“能同时跑”，但它们要么存在真实数据依赖，要么会写同一 state 域，要么并行后难以解释结果，收益不一定能覆盖复杂度。

技术要点  
- 当前并行落点：`parallel_start -> planner + risk -> review_join`
- merge reducer：`state.py`
- 并行指标：`metrics/runtime.py`

Follow-ups
- F1. 怎么判断一个节点是否适合并行？
  简要回答  
  看三件事：输入是否独立、输出是否冲突、trace 是否还能解释。
  技术要点  
  依赖图、state ownership、observability
- F2. 并行后如果速度没明显提升怎么办？
  简要回答  
  很可能瓶颈不在这两个节点，或者 join / I/O 抵消了收益；这时要靠 trace 和 metrics 做证据判断，而不是凭感觉继续扩并行。
  技术要点  
  `parallel_wall_time_ms` 在 trace，`parallel_enabled` 在 metrics

Trade-offs
- T1. 并行化和可维护性怎么取舍？
  简要回答  
  在 Agent 系统里，通常先保证路径可解释，再做并行；错误的并行比没有并行更危险。

System Variants
- S1. 如果未来要做 case 级并行和节点级并行混合，需要额外注意什么？
  简要回答  
  要区分“单次运行内部并行”和“多 case 并发”两类竞争，尤其注意共享缓存、API 限流和 trace 隔离。

Pitfalls
- 只从“CPU 利用率”角度谈并行，不讨论语义依赖和状态 merge。
- 忽略并行后调试难度上升。

<a id="qpe-3"></a>
### PE-3. 为什么缓存先做内存 TTL，再考虑持久化？
【Resume Highlight】Version B #3；Version C #4，#5

问题  
为什么 v3 没直接上 Redis / SQLite，而是先做进程内 TTL cache？

简要回答  
因为 v3 的目标是先验证“哪些调用值得缓存、命中语义是否正确、trace/metrics 怎么记录”。进程内 TTL cache 改造面最小、测试成本最低，也足够覆盖常驻 FastAPI/MCP 进程中的重复 skill 调用场景。

技术要点  
- 现有实现：`skills/executor.py`
- 设计边界：`docs/v3-roadmap.md`
- 测试验证：`tests/test_skills_cache.py`

Follow-ups
- F1. 什么情况下才值得升级到持久化缓存？
  简要回答  
  当跨进程复用收益明确、服务实例增多、命中率稳定且 cache key 设计已验证正确时，再考虑 Redis/SQLite 这类持久化后端。
  技术要点  
  当前 roadmap 已明确把持久化缓存列为 future work。
- F2. 为什么 TTL 是必要的？
  简要回答  
  因为即便本地 catalog 相对稳定，配置版本、输入模式和业务规则也可能变化；TTL 可以降低陈旧结果长期污染的风险。
  技术要点  
  `ttl_sec`、过期失效逻辑

Trade-offs
- T1. 先做内存 TTL 会不会限制上限？
  简要回答  
  会，但它把问题分阶段解决：先把缓存语义做对，再谈分布式扩展，工程风险更低。

System Variants
- S1. 如果换成 Redis，哪些逻辑最好不变？
  简要回答  
  保持 `SkillSpec`、cache key 组成、trace 写法不变，只替换底层存储实现。

Pitfalls
- 把“没上 Redis”说成能力不足；正确说法是 staged rollout。
- 忽略先验证缓存语义，再扩展缓存介质的工程顺序。

<a id="qpe-4"></a>
### PE-4. cache hit/miss 为什么必须进入 trace 与 metrics？
【Resume Highlight】Version B #3，Version B #4；Version C #5，#7

问题  
为什么不能只在日志里打印一句 “cache hit”？

简要回答  
因为缓存是性能优化，也是行为分支。只有把 hit/miss 进入 trace 和 run-level metrics，才能在单次运行、跨次回归、以及问题排查中证明缓存是否真正发生、是否真的带来了收益。

技术要点  
- per-skill trace：`skills/executor.py`
- run-level 聚合：`metrics/runtime.py`
- eval 校验：`eval/run_eval.py`
- 相关测试：`tests/test_metrics_runtime.py`

Follow-ups
- F1. 为什么 hit/miss 既要在 trace 里，也要在 metrics 里？
  简要回答  
  trace 负责单次运行解释，metrics 负责跨运行汇总；两者解决的问题不同。
  技术要点  
  trace 中有 `cache_hit`，metrics 中有 `cache_hit_count` / `cache_miss_count`
- F2. 如果 hit 了但延迟没有下降，怎么解释？
  简要回答  
  说明瓶颈可能不在这个 skill，或总耗时被其他 LLM 节点掩盖；这正是为什么要把 cache 与整体 latency 一起看。
  技术要点  
  `total_latency_ms`、`planner_latency_ms`、`risk_latency_ms`

Trade-offs
- T1. 记录这些字段会不会让 trace 太重？
  简要回答  
  会增加少量字段，但比起缺少解释能力，这个成本很小，尤其在并行和缓存并存时几乎是必要的。

System Variants
- S1. 如果以后加入 persistent cache metrics，还要加什么？
  简要回答  
  需要区分 local hit、remote hit、stale miss 等类型，否则命中统计会失去解释力。

Pitfalls
- 只谈“命中率高低”，不谈命中的正确性和收益。
- 把 trace 和 metrics 混为一谈。

<a id="sec-architecture-evolution"></a>
## 第七部分：Architecture Evolution

<a id="qae-1"></a>
### AE-1. v1 -> v2 -> v3 的架构演进逻辑是什么？
【Resume Highlight】Version B #1-#4；Version C #1-#7

问题  
如果面试官追问“你这个项目是怎么一步步长成现在这样的”，怎么回答？

简要回答  
可以概括成三步：v1 先把多 Agent 评审链路跑通；v2 把结构化输出、路由和服务接口工程化；v3 再把系统从“能运行”推进到“能复用、能优化、能平台化”，也就是补上 skill、subflow、parallel、cache、runtime metrics 这些更偏平台层的能力。

技术要点  
- v1/v2 基座：多 Agent、schema、trace、服务入口
- v3 扩展：`skills/`、`subflows/`、`metrics/runtime.py`
- roadmap：`docs/v3-roadmap.md`
- v3 验证：`eval/run_eval.py`、`tests/test_skills_cache.py`

Follow-ups
- F1. v2 到 v3 最大变化是什么？
  简要回答  
  从“工作流正确性”进一步走向“工作流复用与性能治理”，也就是引入 skill、subflow、parallel 和 cache。
  技术要点  
  这几项都能在 v3 新目录和测试里找到落点。
- F2. 为什么说 v3 不只是功能增加，而是架构演进？
  简要回答  
  因为它新增的是系统边界和能力层，例如 executor、subgraph、runtime metrics，而不是单个业务字段。
  技术要点  
  `skills/executor.py`、`subflows/risk_analysis.py`、`metrics/runtime.py`

Trade-offs
- T1. 演进式重构最大的风险是什么？
  简要回答  
  是旧逻辑和新抽象并存时的边界不清，所以 v3 同步补了 tests 和 eval，防止演进过程中行为漂移。

System Variants
- S1. 如果继续做 v4，优先级会是什么？
  简要回答  
  更可能是 persistent cache、更多 subflow、以及更强的平台观测能力，而不是盲目增加 Agent 数量。

Pitfalls
- 把版本演进讲成功能罗列。
- 忽略“为什么这一版是架构层变化”。

<a id="qae-2"></a>
### AE-2. 为什么 v3 要走平台化，而不是继续堆单点功能？
【Resume Highlight】Version B #4；Version C #4，#5，#6，#7

问题  
为什么 v3 的重点不是继续新增更多业务能力，而是平台化？

简要回答  
因为系统已经不只是“做一次评审”的 demo，而是要被不同入口、不同运行场景复用。到这个阶段，真正限制迭代速度的不是少一个 Prompt，而是有没有统一的 skill 执行层、子流复用、服务接口、trace 和质量门禁。平台化能让后续功能继续长在稳定边界上。

技术要点  
- 平台化边界：`service/`、`skills/`、`subflows/`、`server/`、`mcp_server/`
- 质量门禁：`eval/run_eval.py`、`tests/`
- roadmap 目标：`docs/v3-roadmap.md`

Follow-ups
- F1. 平台化最直接的产出是什么？
  简要回答  
  是复用成本下降。新增入口、工具或工作流能力时，不需要改整个系统，只要沿着现有边界扩展。
  技术要点  
  service 层、skill 层、subflow 层都是平台化边界
- F2. 平台化会不会让校招项目看起来过度设计？
  简要回答  
  如果没有真实落点会；但 v3 里这些抽象都有代码、测试和运行指标支撑，所以它不是空抽象。
  技术要点  
  `skills/executor.py`、`subflows/risk_analysis.py`、`tests/test_skills_cache.py`

Trade-offs
- T1. 平台化和功能交付速度怎么平衡？
  简要回答  
  做“最小够用的平台化”：只抽象已经重复出现或明显要复用的能力，避免一次性做成大而全框架。

System Variants
- S1. 如果这是内部一次性项目，还需要这么多平台化吗？
  简要回答  
  不一定。但当前仓库已经同时支持 CLI、FastAPI、MCP、eval、tests，多入口现实决定了平台化是有必要的。

Pitfalls
- 把平台化理解成“做得更复杂”。
- 不说明平台化具体落在什么代码边界上。

<a id="qae-3"></a>
### AE-3. 为什么 v3 适合单独开分支开发？如何避免“功能越做越碎”？
【Resume Highlight】Version B #3，Version B #4；Version C #4，#5，#6，#7

问题  
为什么像 v3 这种改动更适合独立分支？以及在持续迭代里，怎么避免功能越堆越碎？

简要回答  
因为 v3 不是小修小补，而是涉及工作流图、状态定义、技能执行层、子流、缓存和 metrics 的成组改动，风险面广、回归面也大。独立分支更适合把这些关联改动一起推进、一起验证。要避免功能碎片化，关键是让新能力尽量落在稳定层次上，例如 skill、subflow、service、metrics，而不是把逻辑零散塞回各个 Agent。

技术要点  
- 代码证据：`workflow.py`、`state.py`、`skills/`、`subflows/`、`metrics/runtime.py`
- 文档证据：`docs/v3-roadmap.md`
- 回归证据：`eval/run_eval.py`、`tests/test_skills_cache.py`、`tests/test_metrics_runtime.py`
- 说明：本题部分是基于 roadmap 和代码边界的工程决策解释，不是单一函数能直接证明的结论

Follow-ups
- F1. 什么样的改动值得单独开分支？
  简要回答  
  典型特征是会同时改动状态契约、运行时行为、观测指标和测试基线；v3 正好符合这一点。
  技术要点  
  并行、缓存、子流都会影响 runtime 行为和回归结果
- F2. 如何避免“每加一个功能就多一个特判”？
  简要回答  
  新能力优先抽到统一边界里，例如工具进 skill 层、复合链路进 subflow、运行指标进 metrics，而不是在 Agent 里不断加分支。
  技术要点  
  `SkillExecutor`、`risk_analysis` subgraph、`compute_runtime_metrics`

Trade-offs
- T1. 单独分支会不会拉长交付时间？
  简要回答  
  可能会，但它能降低主线不稳定和半成品抽象混入主干的风险，尤其适合这类横切式重构。

System Variants
- S1. 如果团队很小、节奏很快，还值得单独开分支吗？
  简要回答  
  只要改动跨越多个边界且需要系统性验证，就值得；是否开分支取决于改动面和回归成本，不取决于团队人数。

Pitfalls
- 把“开分支”回答成纯 Git 流程问题；本题重点是架构风险控制。
- 只说“为了安全”，不解释为什么 v3 的改动天然是横切式重构。
