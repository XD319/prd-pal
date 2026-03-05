# Multi-Agent 需求评审系统面试题（V2）

基于当前仓库实现整理，覆盖 LangGraph 工作流、多 Agent 协作、结构化输出、条件路由、风险证据工具、FastAPI、MCP 与评估体系。

## 变更说明（V2.1）
- 本版本补齐：系统整体、Prompt工程、成本/性能、Agent vs RAG、生产化等面试高频点。
- 本次重构按最新简历 bullet 对齐，补充 `【Resume Highlight】` 显式映射与缺口题。

## 简历覆盖映射（V2.1 Resume Sync）
- B1/C1/C4：LangGraph 多 Agent 编排、`StateGraph(ReviewState)`、条件路由与循环。覆盖：Q0-1、Q1、Q13、Q13.1。  
- B2/C2：structured outputs、`json_repair`、schema validation。覆盖：Q5、Q6、Q7。  
- B3/C3/C4：risk evidence retrieval、risk-driven routing loop。覆盖：Q9、Q10、Q11、Q13、Q13.1。  
- B4/C5/C6：FastAPI async service、MCP server、evaluation framework、trace artifacts。覆盖：Q14、Q16、Q16.2、Q17、Q18、Q19、Q20。  

## 第一部分：系统设计

### Q0-1. 系统整体架构是什么？数据如何流动？
【Resume Highlight】对应简历：Version B #1，Version C #1。  
问题  
请从入口到产物说明系统主链路，并给出一个简化流程图。

简要回答  
系统是“HTTP/MCP 入口 + LangGraph 编排 + 多 Agent 执行 + 工具增强 + 工件落盘”的流水线。请求进入后写入共享 state，经过 parser/planner/risk/reviewer/route_decider/reporter，最终输出报告与 trace。

技术要点  
- 主流程编排：`requirement_review_v1/workflow.py`（`StateGraph`、节点与条件边）。  
- 服务入口：`requirement_review_v1/server/app.py`、`requirement_review_v1/mcp_server/server.py`。  
- 工件输出：`requirement_review_v1/run_review.py`、`requirement_review_v1/service/review_service.py`。  
- 可观测链路：`requirement_review_v1/utils/trace.py`。  
- ASCII flow 图：  
```text
HTTP/MCP Request
      |
      v
  requirement_review_v1/server/app.py or requirement_review_v1/mcp_server/server.py
      |
      v
StateGraph(requirement_review_v1/workflow.py)
  parser -> planner -> risk -> reviewer -> route_decider
                                  |            |
                                  |(loop)      |(finish)
                                  v            v
                                clarify ---> reporter
                                               |
                                               v
                                report.md / report.json / run_trace.json
```
Follow-ups
F1. `review_service.review_prd_text_async` 与 `workflow.run_requirement_review` 的职责边界是什么？失败重试应放在哪一层？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. `run_review.py` 落盘 `report.json` 与 `run_trace.json` 时，如何保证同一 `run_id` 的原子一致性？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F3. 如果要新增 WebSocket 实时进度推送，你会复用 `workflow.py` 的 `progress_hook` 还是在 `server/app.py` 做包装？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 统一 HTTP/MCP 双入口共享同一 service 层，和分别维护两套入口逻辑相比，调试复杂度与一致性如何权衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
实施上在 requirement_review_v1/mcp_server/server.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 tests/test_mcp_tools.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
T2. 将编排逻辑放在 `workflow.py` 而非 API 层，带来的可测性收益和跨层排障成本如何平衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
System Variants
S1. 若改成事件驱动架构（队列 + worker），`server/app.py` 需要保留哪些同步能力用于查询与回放？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/server/app.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/run_review.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
S2. 若支持多租户，`run_id` 与 artifacts 目录结构应如何在 `review_service.py` 中扩展租户隔离？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 只讲节点顺序，不讲 `review_service -> workflow -> run_review` 的工程边界。
- 忽略 artifacts 命名与目录规范，后续检索 `get_report` 容易不兼容。

### Q0-2. 为什么使用多 Agent，而不是单 Agent？
问题  
为什么不让一个“大而全”的 Agent 一次性完成解析、规划、风险和评审？

简要回答  
多 Agent 更适合工程化：职责隔离便于独立优化，可观测性更强，组件可替换，且单点失败时可以降级而不是全链路崩溃。

技术要点  
- 职责隔离：`requirement_review_v1/agents/parser_agent.py`、`requirement_review_v1/agents/planner_agent.py`、`requirement_review_v1/agents/risk_agent.py`、`requirement_review_v1/agents/reviewer_agent.py`、`requirement_review_v1/agents/reporter_agent.py`。  
- 可观测性：`requirement_review_v1/utils/trace.py` 为每个节点记录 span/status。  
- 可替换性：Agent 通过 `requirement_review_v1/state.py` 的共享字段解耦。  
- 失败隔离：`requirement_review_v1/utils/llm_structured_call.py` 异常与降级路径 + 各 agent 的异常兜底。
Follow-ups
F1. `reviewer_agent.py` 依赖 `planner_agent.py` 输出时，字段缺失如何在 `state.py` 中降级而不触发级联报错？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/reviewer_agent.py 与 requirement_review_v1/agents/planner_agent.py 明确改动，再用 requirement_review_v1/state.py 做回归验证。
原因：这能限制写冲突，并把故障收敛在单一责任域。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
F2. 如果把 `risk_agent.py` 合并进 `reviewer_agent.py`，你预期 `tests/test_risk_tool.py` 哪些断言会失效？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Trade-offs
T1. 多 Agent 带来更强可观测性，但也增加跨节点序列化成本；在当前 PRD 规模下收益是否显著？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。按 agent 定义字段 ownership，并只允许 partial state 更新。
实施上在 requirement_review_v1/agents/reviewer_agent.py 落策略，在 requirement_review_v1/agents/planner_agent.py 保持契约，并以 requirement_review_v1/state.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
T2. 单 Agent Prompt 更短路径，但责任混合；与 `agents/*.py` 模块化相比，迭代速度如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
实施上在 requirement_review_v1/prompts.py 落策略，在 requirement_review_v1/agents/parser_agent.py 保持契约，并以 requirement_review_v1/workflow.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
System Variants
S1. 若增加 `compliance_agent`，你会在 `workflow.py` 插在 `reviewer` 前还是后，为什么？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若做并行 agent（planner/risk 并发），`ReviewState` 冲突字段如何定义 merge 规则？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Pitfalls
- 只强调“多 Agent 更先进”，忽略小场景下复杂度可能过高。
- 未说明跨 agent 数据契约，面试官会追问字段漂移风险。

### Q0-3. 系统里最复杂/最核心的部分是什么？为什么？
问题  
如果只挑一个“最核心工程点”，你会选什么？

简要回答  
核心是 LangGraph 的条件路由与循环终止机制。它同时决定了系统是否可控、可终止、可解释，是多 Agent 流程从“能跑”到“可上线”的关键。

技术要点  
- 条件路由与循环：`requirement_review_v1/workflow.py` 的 `add_conditional_edges`、`_route_decider_node`、`_clarify_node`。  
- 终止门控：`_HIGH_RISK_THRESHOLD`、`_MAX_REVISION_ROUNDS`。  
- 回归验证：`tests/test_routing_loop.py` 覆盖循环与终止行为。
Follow-ups
F1. `_route_decider_node` 如何处理 reviewer 产出异常（如 `high_risk_ratio` 缺失）以避免错误早停？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. `routing_rounds` 与 `revision_round` 分别解决什么审计问题，为什么两个字段都要保留？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 阈值硬编码在 `workflow.py` 与配置化到 env/config 的取舍是什么？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
T2. 把路由规则做成纯规则引擎 vs LLM 决策器，哪种更可回归？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 如果把 `_MAX_REVISION_ROUNDS` 提升到 4，`eval/run_eval.py` 需要新增哪些指标防止成本失控？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若要支持“人工确认后继续”，你会在 `route_decider` 后插入 `human_gate` 节点还是在 API 层阻塞？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Pitfalls
- 只说“核心是 loop”，但解释不出终止保障和可测试证据。
- 没给出失败场景处理策略（缺字段、空输出、异常路径）。

### 1. 为什么这里使用 LangGraph，而不是简单的线性 pipeline？
【Resume Highlight】对应简历：Version B #1，Version C #1/#4。  
问题  
为什么项目使用 `StateGraph` 来编排，而不是直接按函数顺序调用？

简要回答  
因为流程里存在条件分支与循环（`route_decider -> clarify -> planner...`），LangGraph 对这种状态驱动的分支编排更自然，也更易扩展和追踪。

技术要点  
- `requirement_review_v1/workflow.py` 使用 `StateGraph(ReviewState)`。  
- 主链路和澄清回路共存，依赖 `add_conditional_edges`。  
- 所有节点返回 partial state，框架统一合并。
Follow-ups
F1. 你的状态 merge 策略如何避免后写覆盖前写？可结合 `requirement_review_v1/state.py` 和节点 partial update 说明。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/reviewer_agent.py 与 requirement_review_v1/agents/planner_agent.py 明确改动，再用 requirement_review_v1/state.py 做回归验证。
原因：这能限制写冲突，并把故障收敛在单一责任域。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
F2. 如果新增一个 Agent 节点，在哪些地方最小改动接入？可从 `requirement_review_v1/workflow.py` 与 `ReviewState` 字段出发。
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F3. 如何证明 routing 行为可测试？可引用 `tests/test_routing_loop.py`。
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 用 `StateGraph` 处理复杂分支更清晰，但对简单路径引入抽象成本；你如何判断何时不该用图编排？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
T2. 将条件路由集中在 `workflow.py` 提高统一性，但业务规则耦合增强，如何拆分避免文件膨胀？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
System Variants
S1. 如果要让 `planner` 与 `risk` 并行执行，`StateGraph` 的 join 节点应如何设计并验证一致性？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若迁移到其他编排器（如 Temporal），哪些接口可复用，哪些需要重写（state/trace/progress_hook）？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Pitfalls
- 只强调“图更高级”而不解释 loop/termination 的工程必要性。
- 忽略 state 字段演进导致的兼容问题（新增字段未同步 schema/agent）。

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
Follow-ups
F1. `planner_agent.py` 输出 `dependencies` 异常时，`reviewer_agent.py` 如何保持最小可用？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/reviewer_agent.py 与 requirement_review_v1/agents/planner_agent.py 明确改动，再用 requirement_review_v1/state.py 做回归验证。
原因：这能限制写冲突，并把故障收敛在单一责任域。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
F2. `reporter_agent.py` 只做拼接时，如何确保与 `schemas/*.py` 字段变更同步？
简要回答  
从代码落点回答：先在 requirement_review_v1/schemas/base.py 与 requirement_review_v1/schemas/reviewer_schema.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
Trade-offs
T1. 将 Reporter 设为 deterministic 降低波动，但表达能力受限；你如何评估这笔取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 让每个 Agent 独立做 schema validation 和在链路末端统一校验，哪种更易定位问题？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
实施上在 requirement_review_v1/schemas/base.py 落策略，在 requirement_review_v1/schemas/reviewer_schema.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
System Variants
S1. 若新增 `cost_agent` 专门估算 token 成本，应写入 `ReviewState` 哪些字段并在哪里展示？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/reviewer_agent.py 和 requirement_review_v1/agents/planner_agent.py 实现改造，并围绕 requirement_review_v1/state.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
S2. 若引入多模型路由（cheap/expensive），你会在 agent 内部切换还是在 workflow 层统一调度？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Pitfalls
- 协作描述停留在概念层，没有字段级输入输出边界。
- 忽略 agent 间失败传播策略，面试官会追问异常链路。

### 3. 如何避免 Agent 间状态混乱？
问题  
多个节点都在读写 state，如何控制状态一致性？

简要回答  
通过 `TypedDict(total=False)` + 节点 partial update 约束写入边界；节点内部不原地改共享对象，统一返回增量结果给 LangGraph merge。

技术要点  
- `requirement_review_v1/state.py` 中 `ReviewState(total=False)`。  
- Agent 内常见模式：`trace = dict(state.get("trace", {}))` 后再 return。  
- 输出字段按责任分离，避免跨域覆盖。
Follow-ups
F1. `ReviewState(total=False)` 容易出现“字段存在但为空”，你如何区分“未产出”和“产出为空”？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
F2. `trace` 深拷贝后回写时，如何避免并发更新覆盖（尤其未来并行节点）？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/trace.py 与 requirement_review_v1/run_review.py 明确改动，再用 eval/run_eval.py 做回归验证。
原因：它支持回放、版本对比和迭代质量门禁。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Trade-offs
T1. `TypedDict` 轻量但弱约束；相比在 state 层使用 Pydantic model，性能与安全如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
实施上在 requirement_review_v1/schemas/base.py 落策略，在 requirement_review_v1/schemas/reviewer_schema.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
T2. 在节点内做 defensive copy 提高安全性，但会增加对象复制开销，是否可接受？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若需要并发 fan-out/fan-in，是否应引入显式 merge 函数替代默认 dict 合并？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若做跨进程执行，`ReviewState` 序列化协议（JSON/msgpack）如何影响字段类型设计？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 只说“partial update”不说明冲突策略和字段 ownership。
- 把 state 当全局变量随意写，最终难以回归与审计。

### 4. 为什么把澄清步骤建成独立节点 `clarify`？
问题  
为何不是在 parser 内部做 while 循环？

简要回答  
放在图层做更可观测，路由决策、轮次计数、终止条件都可追踪；节点逻辑保持单一职责。

技术要点  
- `_clarify_node` 复用 parser，仅切换 `parser_prompt_version="v1.1-clarify"`。  
- 路由记录在 `trace["router"]` 与 `trace["routing_rounds"]`。  
- `revision_round` 由路由节点统一维护。
Follow-ups
F1. `clarify` 只切 prompt 版本，不换 schema；如果澄清输出字段扩展，兼容策略在哪里落地？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. `revision_round` 是在进入 clarify 前还是后递增？这对 trace 可读性有何影响？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 独立 `clarify` 节点可观测性更强，但链路更长；与 parser 内部自循环相比如何权衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
T2. 复用 parser agent 降低维护成本，但会耦合解析与澄清语义，何时应拆分独立 Clarifier Agent？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。按 agent 定义字段 ownership，并只允许 partial state 更新。
实施上在 requirement_review_v1/agents/reviewer_agent.py 落策略，在 requirement_review_v1/agents/planner_agent.py 保持契约，并以 requirement_review_v1/state.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
System Variants
S1. 若把澄清改为“提问用户”交互式回路，`server/app.py` 应新增什么状态机字段？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若改为一次澄清后直接 reporter（不复审），在 `workflow.py` 哪条边要改，风险是什么？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Pitfalls
- 把 clarify 当成“再跑一次 parser”，忽略其目标是信息增益而非重复解析。
- 未记录轮次和路由原因，后续无法证明 loop 的必要性。

### 4.1 如何从“系统整体”解释这套架构？
问题  
如果面试官要求你在 1-2 分钟讲清系统全貌，你会怎么讲调用链、输入输出与边界？

简要回答  
可以按“入口层 -> 编排层 -> Agent 执行层 -> 工具层 -> 工件层”讲清楚：HTTP/MCP 收到请求后进入 LangGraph，多个 Agent 基于共享状态推进，必要时调用风险目录工具，最终落盘 `report` 与 `trace` 并提供查询。

技术要点  
- 入口层：`requirement_review_v1/server/app.py` 与 `requirement_review_v1/mcp_server/server.py`。  
- 编排层：`requirement_review_v1/workflow.py` 负责节点与条件路由。  
- 执行层：`requirement_review_v1/agents/*.py` 各自负责单域输出。  
- 工件层：`requirement_review_v1/run_review.py` 统一输出 `report.md/report.json/run_trace.json`。
Follow-ups
F1. 如果只给你 60 秒，你会优先讲哪 3 个模块来证明“可上线而不是 demo”？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
F2. `review_service.py` 在架构里的角色是什么，为什么不直接在 API 层调 `workflow.py`？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 架构讲解强调分层清晰，但会牺牲面试时间；如何在“全景”和“深挖”间取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 强调 artifacts/trace 可能压缩业务价值叙述，你怎么平衡工程和业务表达？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
System Variants
S1. 若系统作为 SDK 嵌入而非服务部署，哪些层可以裁剪（server/mcp）？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/mcp_server/server.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 tests/test_mcp_tools.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
S2. 若未来接入消息队列，入口层如何从同步 API 迁移到异步事件消费？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 只讲技术名词，不给调用链与输入输出边界。
- 忽略“失败时怎么处理”，面试官会判定工程性不足。

### 4.2 这个系统和 RAG 的区别是什么？为什么这是 Agent Workflow 而不是 RAG？
问题  
如果面试官问“你这个项目是不是 RAG”，应该如何准确回答？

简要回答  
这是 Agent Workflow 主导、检索能力辅佐的系统。流程推进由状态机和多 Agent 决策控制，检索（风险目录）只在特定节点用于证据增强，不是“检索后直接生成答案”的 RAG 主范式。

技术要点  
- Workflow 主体：`requirement_review_v1/workflow.py`（节点编排、loop、termination）。  
- Agent 分工：`requirement_review_v1/agents/*.py`。  
- 检索增强位置：`requirement_review_v1/tools/risk_catalog_search.py` + `requirement_review_v1/agents/risk_agent.py`。  
- 行为验证：`tests/test_risk_tool.py`、`tests/test_routing_loop.py`。
Follow-ups
F1. 如果去掉 `risk_catalog_search.py`，系统仍是 Agent Workflow 吗？判定标准是什么？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. RAG 常见的“检索-生成”二段式在本项目映射到哪些节点，哪些能力并不属于 RAG？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 将检索仅用于 risk 节点降低复杂度，但可能遗漏 parser/planner 的外部知识增强，如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
T2. 把系统定义为 Agent Workflow 有利于解释控制流，但会不会弱化检索质量的重要性？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
System Variants
S1. 若扩展为 full RAG + Agent 混合架构，你会把向量检索插在哪些节点并如何评估收益？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/reviewer_agent.py 和 requirement_review_v1/agents/planner_agent.py 实现改造，并围绕 requirement_review_v1/state.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
S2. 若引入外部政策库检索，`tools/` 层和 `risk_agent.py` 需要怎样的接口抽象？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Pitfalls
- 把“有检索”直接等同于 RAG，概念边界不清。
- 只谈术语，不落到 `workflow.py` 与 `risk_catalog_search.py` 的代码证据。

## 第二部分：工程实现

### 5. Structured Outputs 如何保证稳定？
【Resume Highlight】对应简历：Version B #2，Version C #2。  
问题  
系统如何尽量稳定地产出结构化 JSON？

简要回答  
先走 provider 工具/函数调用结构化输出；失败时降级为文本 JSON 路径，再用 `json_repair + parse_json_markdown` 解析。

技术要点  
- `requirement_review_v1/utils/llm_structured_call.py` 的 tools/fallback 双路径。  
- `metadata["structured_mode"]` 记录实际模式。  
- 失败抛 `StructuredCallError` 并携带 `raw_output`。
Follow-ups
F1. provider tools 与 fallback 各自触发条件是什么？可按 `requirement_review_v1/utils/llm_structured_call.py` 异常分支解释。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F2. raw_output 落盘后如何用于排障与复现？可关联 trace 的 `raw_output_path`。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F3. 如何监控结构化失败率？可从 `run_trace.json` 聚合 `status/error_message` 统计。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Trade-offs
T1. provider tool-calling 稳定性高但受模型能力限制；与统一走 fallback JSON 路径相比如何权衡兼容性与准确性？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
实施上在 requirement_review_v1/utils/llm_structured_call.py 落策略，在 requirement_review_v1/schemas/base.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
T2. 失败即抛 `StructuredCallError` 更可控，但会增加降级分支复杂度；何时选择 hard-fail？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
实施上在 requirement_review_v1/utils/llm_structured_call.py 落策略，在 requirement_review_v1/schemas/base.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
System Variants
S1. 若接入不支持 tools 的模型，`llm_structured_call.py` 如何退化到 parser-first 模式并保持指标可比？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
S2. 若引入“二次自修复重试”层，应该放在 structured call 内还是 agent 层？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 把“能 parse 出 JSON”当成稳定性完成，忽略业务字段缺失与脏值。
- 没有区分 provider 结构化失败和 schema 校验失败两类问题。

### 6. 为什么需要 schema validation？
【Resume Highlight】对应简历：Version B #2，Version C #2。  
问题  
既然拿到 JSON 了，为什么还要 Pydantic 校验？

简要回答  
JSON 只保证语法，不保证业务类型与字段约束；Pydantic 用于做最后一道契约校验与类型归一化。

技术要点  
- `requirement_review_v1/schemas/*.py` 定义 Parser/Planner/Risk/Reviewer 输出模型。  
- `AgentSchemaModel(extra="ignore")` 忽略脏字段。  
- `NormalizedBool`、`SafeStrList` 处理 `"yes"`/`None` 等脏值。
Follow-ups
F1. 哪些字段必须 hard-fail，哪些可以 normalize？可按 `requirement_review_v1/schemas/base.py` 的类型策略说明。
简要回答  
从代码落点回答：先在 requirement_review_v1/schemas/base.py 与 requirement_review_v1/schemas/reviewer_schema.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
F2. schema 升级如何保证向后兼容？可结合 `tests/test_schema_validation.py` 回归说明。
简要回答  
从代码落点回答：先在 requirement_review_v1/schemas/base.py 与 requirement_review_v1/schemas/reviewer_schema.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
F3. 校验失败后系统是否继续？可关联各 agent 对 `StructuredCallError` 的降级返回。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Trade-offs
T1. `extra="ignore"` 提升鲁棒性但可能掩盖字段拼写错误；何时改为 `forbid`？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
实施上在 requirement_review_v1/schemas/base.py 落策略，在 requirement_review_v1/schemas/reviewer_schema.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
T2. 在每个 agent 立即校验 vs 在 reporter 前统一校验，诊断效率与吞吐如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。按 agent 定义字段 ownership，并只允许 partial state 更新。
实施上在 requirement_review_v1/agents/reviewer_agent.py 落策略，在 requirement_review_v1/agents/planner_agent.py 保持契约，并以 requirement_review_v1/state.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
System Variants
S1. 若要支持版本化 schema（v1/v2 并行），`schemas/` 与 `llm_structured_call.py` 如何协同路由？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
S2. 若引入 JSON Schema 校验替代/补充 Pydantic，哪些类型归一化逻辑仍需保留在 `schemas/base.py`？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 把 schema 当万能防线，忽略 prompt 与 tool 输入质量。
- 过度 `extra=ignore` 导致关键字段拼写错误被静默吞掉。

### Prompt Engineering & Prompt Versioning

#### PE-1. prompt 模板如何组织与复用？
问题  
在工程里，system/user prompt 应该如何拆分，如何注入字段化输入并复用模板？

简要回答  
当前做法是把 prompt 作为代码常量集中在 `requirement_review_v1/prompts.py`，按 agent 拆分 `SYSTEM_PROMPT` 与 `USER_PROMPT`，运行时只注入结构化字段（例如 `requirement_doc`、`items_json`、`plan_json`），避免拼接自由文本导致漂移。

技术要点  
- 模板组织：`requirement_review_v1/prompts.py`（`PARSER_*`、`CLARIFY_PARSER_*`、`REVIEWER_*` 等）。  
- 字段渲染：`requirement_review_v1/agents/parser_agent.py`、`requirement_review_v1/agents/planner_agent.py`、`requirement_review_v1/agents/reviewer_agent.py`、`requirement_review_v1/agents/risk_agent.py`。  
- 结构化输出配套：`requirement_review_v1/utils/llm_structured_call.py` + `requirement_review_v1/schemas/*.py`。  
- 当前无独立 Prompt Registry；模板与版本随代码发布（当前做法）。
Follow-ups
F1. `prompts.py` 模板变更后，如何定位具体影响到 `parser/planner/reviewer/risk` 哪个节点？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F2. 当前字段注入方式如何避免把超长 `items_json` 直接塞进 prompt 导致 token 激增？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Trade-offs
T1. prompt 代码内联便于版本对齐，但降低运营可配置性；何时值得引入 Prompt Registry？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
实施上在 requirement_review_v1/prompts.py 落策略，在 requirement_review_v1/agents/parser_agent.py 保持契约，并以 requirement_review_v1/workflow.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
T2. 复用统一模板可降维护成本，但可能牺牲节点个性化表达，如何平衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若按租户下发不同 prompt 版本，`state.py` 与 `server/app.py` 需要新增哪些字段？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/prompts.py 和 requirement_review_v1/agents/parser_agent.py 实现改造，并围绕 requirement_review_v1/workflow.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
S2. 若引入模板渲染引擎（Jinja），如何避免变量缺失导致运行时错误？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- prompt 组织只按文件划分，未绑定节点输入契约。
- 变更 prompt 不做回归，导致线上表现漂移却不可追踪。

#### PE-2. prompt 版本如何管理与回滚？
问题  
如何确保 prompt 变更可追踪、可回滚、可定位影响范围？

简要回答  
当前通过 state 字段显式携带 `parser_prompt_version`，由 workflow 决定何时切换到澄清版本；trace 会记录实际执行版本，出问题可按版本快速回退到稳定值。未来可引入 Prompt Registry 做版本中心化与动态回滚。

技术要点  
- 版本字段：`requirement_review_v1/state.py`（`parser_prompt_version` 默认 `v1.1`）。  
- 切换逻辑：`requirement_review_v1/workflow.py`（`_clarify_node` 设置 `v1.1-clarify`）。  
- 版本可观测：`requirement_review_v1/agents/parser_agent.py` + `requirement_review_v1/utils/trace.py`（`span.set_attr("prompt_version", ...)`）。  
- 回滚方式：当前走代码版本回滚/切换默认值；`TODO/未来改造` 为 Prompt Registry + A/B 配置开关（可结合 env/config 下发）。
Follow-ups
F1. `parser_prompt_version` 目前只覆盖 parser；如果 reviewer 也要版本化，字段设计怎么扩展？
简要回答  
从代码落点回答：先在 requirement_review_v1/prompts.py 与 requirement_review_v1/agents/parser_agent.py 明确改动，再用 requirement_review_v1/workflow.py 做回归验证。
原因：每次输出都可追溯到明确的 prompt 版本与执行路径。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
F2. trace 里记录 `prompt_version` 后，如何在 `eval/run_eval.py` 做跨版本对比统计？
简要回答  
从代码落点回答：先在 eval/run_eval.py 与 tests/test_routing_loop.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：发布前可同时发现质量退化和逻辑回归。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
Trade-offs
T1. 代码回滚简单可靠，但回滚粒度粗；与动态配置回滚相比风险如何？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 按节点独立版本化更灵活，但治理复杂度上升，如何限制版本爆炸？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若采用配置中心热更新 prompt，如何保证运行中任务前后版本一致性？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/prompts.py 和 requirement_review_v1/agents/parser_agent.py 实现改造，并围绕 requirement_review_v1/workflow.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
S2. 若做灰度发布，`server/app.py` 如何基于请求标签分流不同 prompt 版本？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/prompts.py 和 requirement_review_v1/agents/parser_agent.py 实现改造，并围绕 requirement_review_v1/workflow.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
Pitfalls
- 只有版本号，没有对应变更说明与评估结果，回滚依据不足。
- 版本切换不写 trace，导致线上问题无法定位到具体 prompt。

#### PE-3. 如何做 prompt 的 regression evaluation？
问题  
prompt 调整后，如何判断质量是“真的提升”而不是偶然波动？

简要回答  
用固定 case 集跑回归，比较结构完整性与关键指标稳定性，而不是只看单次样例。重点看 `coverage_ratio` 与 `high_risk_ratio` 的分布变化，以及 trace 完整度和失败率是否恶化。

技术要点  
- 回归入口：`eval/run_eval.py` + `eval/cases/prd_test_inputs.jsonl`。  
- 指标来源：`requirement_review_v1/metrics/coverage.py`（`coverage_ratio`）、`requirement_review_v1/agents/reviewer_agent.py`（`high_risk_ratio`）。  
- 结构与可观测校验：`eval/run_eval.py` 的 trace 字段检查（含 `prompt_version`）。  
- 测试补充：`tests/test_schema_validation.py`、`tests/test_routing_loop.py`、`tests/test_risk_tool.py`。  
- 当前 A/B 主要靠离线多次回归对比；`TODO/未来改造` 为在线 A/B 与 Prompt Registry 联动。
Follow-ups
F1. `eval/cases/prd_test_inputs.jsonl` 的 case 采样策略如何避免只覆盖“容易样本”？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F2. 如何将 `tests/test_routing_loop.py` 与 `eval/run_eval.py` 结果联合成发布门禁？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 离线回归可控但时效性低；在线 A/B 更真实但噪声大，如何组合使用？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 单指标优化（如 coverage）可能伤害其他指标，如何定义多指标优先级？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
实施上在 eval/run_eval.py 落策略，在 tests/test_routing_loop.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
System Variants
S1. 若引入 nightly 自动评测，结果应落在哪个 artifacts 目录并如何追踪历史趋势？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若接入 LangSmith/自建可观测平台，`run_trace.json` 需补哪些字段做关联？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 只比平均值，不看失败分布与长尾样本。
- 评测集长期不更新，指标会虚高而失真。

### Q8.x Prompt 为什么要做版本管理？clarify prompt 与 normal prompt 有什么差异？
问题  
为什么 prompt 不能只维护一个版本？澄清轮次为何要用独立 prompt？

简要回答  
版本化是为了可回归和可灰度；clarify prompt 与 normal prompt 的目标不同，前者强调补全缺失与歧义收敛，后者强调标准解析，两者混用会拉低稳定性与可解释性。

技术要点  
- Prompt 定义：`requirement_review_v1/prompts.py`（`PARSER_*` 与 `CLARIFY_PARSER_*`）。  
- 版本切换：`requirement_review_v1/agents/parser_agent.py`（`parser_prompt_version`、`v1.1-clarify`）。  
- 路由触发澄清版本：`requirement_review_v1/workflow.py` 的 `_clarify_node`。  
- 回归入口：`eval/run_eval.py`、`tests/test_schema_validation.py`。
Follow-ups
F1. `v1.1` 与 `v1.1-clarify` 的目标函数分别是什么，如何量化“澄清有效”？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. 当 `parser_prompt_version` 被 route 切换后，trace 中如何串联前后两次 parser 输出差异？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 统一版本降低认知负担，但无法针对澄清场景优化；双版本增加治理成本，如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 版本切换放在 workflow 层集中控制，与 parser agent 内部自治相比哪个更可审计？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
System Variants
S1. 若新增 `v1.2-domain` 行业版 prompt，路由条件应该放在 `route_decider` 还是入口参数？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若要多语言输入支持，是否为每种语言维护独立 clarify prompt？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Pitfalls
- 把 clarify prompt 当“普通 prompt 的改写”，忽略任务目标差异。
- 版本命名无语义，后续难以沟通与追踪。

### Q8.y 如何从系统层面降低 hallucination？
问题  
除了“写好提示词”，系统级还有哪些可执行手段？

简要回答  
靠多层约束而非单点技巧：schema 校验兜底、工具证据锚定、低温度稳定输出、Reporter 确定性生成、失败降级与 trace 审计，形成闭环。

技术要点  
- 结构约束：`requirement_review_v1/schemas/*.py` + `requirement_review_v1/utils/llm_structured_call.py`。  
- 证据约束：`requirement_review_v1/tools/risk_catalog_search.py`、`requirement_review_v1/agents/risk_agent.py`。  
- 生成稳定性：`temperature=0`（`requirement_review_v1/utils/llm_structured_call.py`）。  
- 确定性报告：`requirement_review_v1/agents/reporter_agent.py`。  
- 异常与审计：`requirement_review_v1/utils/trace.py`、`requirement_review_v1/service/review_service.py`。
Follow-ups
F1. 在 `review_service._derive_status` 中，哪些 trace 状态应触发 hard failure，哪些可降级通过？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. 你如何证明风险证据工具实际降低幻觉，而不是只是增加字段数量？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 强约束（schema/tool）可降低幻觉，但可能压制模型发现能力；在评审场景如何定界？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
实施上在 requirement_review_v1/schemas/base.py 落策略，在 requirement_review_v1/schemas/reviewer_schema.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
T2. Reporter 不用 LLM 提升稳定性，但可读性表达受限，是否值得引入可选增强层？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若接入外部法规检索工具，如何在 `risk_agent.py` 增加证据优先级策略？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
S2. 若支持人审反馈闭环，trace 里应新增哪些字段标记“人工修正”来源？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Pitfalls
- 将“低温度”当唯一反幻觉手段，忽略证据和校验链路。
- 没有定义可量化的幻觉评估口径。

### 7. LLM JSON 解析失败时如何处理？
问题  
如果模型输出不可解析，系统如何避免整个流程崩溃？

简要回答  
Agent 捕获结构化调用异常并降级返回空结果，同时写入 trace 错误信息；流程可继续执行并产出可诊断工件。

技术要点  
- 各 agent `except StructuredCallError` 返回空列表/空字典。  
- `save_raw_agent_output` 保存原始响应，trace 记录 `raw_output_path`。  
- `review_service._derive_status` 根据 trace 统一判定成功/失败。
Follow-ups
F1. `StructuredCallError.raw_output` 何时持久化、何时只写摘要，如何处理敏感信息脱敏？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F2. 降级为空结果后，`reporter_agent.py` 如何避免误导性“看起来正常”的报告？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/reviewer_agent.py 与 requirement_review_v1/agents/planner_agent.py 明确改动，再用 requirement_review_v1/state.py 做回归验证。
原因：这能限制写冲突，并把故障收敛在单一责任域。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
Trade-offs
T1. 继续流程提高可用性，但可能放大下游误判；何时应该中断并返回失败？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 保存完整原始输出利于排障，但会增加存储与合规风险，如何权衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若加入“单节点重试”机制，重试应在 agent 内、workflow 层还是 service 层实现？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若要对 JSON 解析失败做自动告警，应该从 `trace.py` 还是 `review_service.py` 发事件？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 只做异常捕获不做错误分类，后续无法针对性优化。
- 降级策略未被评估，可能让问题静默进入生产。

### 8. temperature=0 在这里的工程意义是什么？
问题  
为什么调用里固定 `temperature=0`？

简要回答  
此场景追求结构一致性与可回归性，优先降低输出波动而不是追求文本多样性。

技术要点  
- `llm_structured_call` fallback 调用 `create_chat_completion(..., temperature=0)`。  
- 与 schema 校验组合，提高可测性。  
- 仍保留 trace 便于定位偶发格式偏差。
Follow-ups
F1. 在同模型下 `temperature=0` 仍有非确定性时，你如何通过 trace 证据说明波动来源？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/trace.py 与 requirement_review_v1/run_review.py 明确改动，再用 eval/run_eval.py 做回归验证。
原因：它支持回放、版本对比和迭代质量门禁。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
F2. 哪些节点可考虑不固定 0（如风险描述文本润色），如何避免影响结构字段稳定？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 低温度提高一致性但可能牺牲召回与表达丰富度；在 parser/risk/reviewer 间是否应差异化？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
T2. 全局固定温度简化运维，但限制实验空间，是否应配置化？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若引入双阶段生成（结构化 0 温度 + 文本润色高温度），应如何拆分到不同 agent？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/reviewer_agent.py 和 requirement_review_v1/agents/planner_agent.py 实现改造，并围绕 requirement_review_v1/state.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
S2. 若 provider 不支持精细温度控制，如何用 prompt 约束补偿？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/prompts.py 和 requirement_review_v1/agents/parser_agent.py 实现改造，并围绕 requirement_review_v1/workflow.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
Pitfalls
- 将温度与准确率简单等同，忽略任务类型差异。
- 没有通过回归数据验证温度策略。

### 成本与性能（新增）

#### C-1. 如何降低 LLM 调用成本？
问题  
在不明显牺牲质量的前提下，怎么做成本优化？

简要回答  
优先减少调用次数，再做模型分层与缓存；同时压缩 prompt 长度，只在关键节点调用高成本模型，把 token 花在最有价值的步骤上。

技术要点  
- 减少调用：`requirement_review_v1/workflow.py`（条件路由、有限循环）。  
- 关键节点调用：`requirement_review_v1/agents/*.py` 可按节点差异化策略（未来可细化为模型分层，`TODO`）。  
- Prompt 收敛：`requirement_review_v1/prompts.py`。  
- 缓存与去重：仓库当前未实现通用 LLM 响应缓存（`TODO/未来改造`）。  
Follow-ups
F1. 如何在 `workflow.py` 层面识别“可跳过节点”来减少调用次数，而不破坏 trace 完整性？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. 若做缓存，cache key 应包含哪些维度（prompt_version/model/schema/version）？
简要回答  
从代码落点回答：先在 requirement_review_v1/schemas/base.py 与 requirement_review_v1/schemas/reviewer_schema.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
Trade-offs
T1. 激进缓存节省成本但可能引入过期结果；在需求评审场景可接受的 TTL 是多少？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 低成本模型替代可降费，但可能拉低 `coverage_ratio`，如何设置切换阈值？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
实施上在 eval/run_eval.py 落策略，在 tests/test_routing_loop.py 保持契约，并以 tests/test_schema_validation.py 作为发布前证据。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
System Variants
S1. 若接入 Redis 缓存，应该放在 `llm_structured_call.py` 还是 service 层统一包装？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
S2. 若按租户计费，如何在 `trace` 中追加 token/cost 字段做核算？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Pitfalls
- 只谈模型降级，不谈质量回归门禁。
- 缓存命中策略不含版本字段，容易出现错配结果。

#### C-2. 如何优化端到端延迟？
问题  
如何降低一次评审从提交到拿到报告的总时延？

简要回答  
从“流程缩短 + 执行提速 + I/O 减少”三层优化：减少不必要轮次、优化模型与 prompt、对可并行步骤做并发化，并把常用检索结果做缓存。

技术要点  
- 异步执行：`requirement_review_v1/server/app.py`（`asyncio` 任务与状态轮询）。  
- 路由早停：`requirement_review_v1/workflow.py`（阈值+轮次上限）。  
- 观测瓶颈：`requirement_review_v1/utils/trace.py`（节点时延）。  
- 流式返回与工具缓存：当前主链路未实现统一 streaming/caching（`TODO/未来改造`）。
Follow-ups
F1. 当前 `server/app.py` 轮询式进度查询的瓶颈在哪里，何时需要改成 push 模式？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
F2. 从 `run_trace.json` 如何定位最长耗时节点并形成优化优先级？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Trade-offs
T1. 并行化可降时延但增加状态合并复杂度；在当前 `ReviewState` 设计下是否值得？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 提前早停节省时间，但可能牺牲评审完整度，阈值如何平衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若引入分布式 worker，如何保证 `get_review_status` 的一致视图？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/server/app.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/run_review.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
S2. 若增加批量评审接口，如何在 `review_service.py` 控制并发与隔离失败任务？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 把平均时延当唯一指标，忽略 P95/P99 长尾。
- 优化时延时不同时跟踪质量指标，容易“快但不准”。

## 第三部分：Agent 设计

### 9. Risk Agent 如何降低 hallucination？
问题  
Risk Agent 除了让模型“想”，还做了什么来约束？

简要回答  
先用本地风险目录检索出证据候选，再把证据喂给模型；最终风险项还会补齐 evidence 字段，减少“无依据风险”。

技术要点  
- `requirement_review_v1/tools/risk_catalog_search.py` 本地 TF-IDF 风格检索。  
- `requirement_review_v1/agents/risk_agent.py` 将 `evidence_json` 注入 prompt。  
- `_attach_fallback_evidence` 为缺证据项补默认证据。
Follow-ups
F1. evidence 命中为空时为何不直接失败？可解释 degraded 产出的业务取舍。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F2. fallback evidence 如何避免“看起来有证据但实际弱相关”？可结合 `risk_catalog_tool_status` 说明。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F3. 如何验证 hallucination 下降？可用 `tests/test_risk_tool.py` + trace 命中率统计。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Trade-offs
T1. 强依赖 catalog 提升可解释性，但知识覆盖受限；与开放式生成相比如何平衡漏检风险？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
T2. fallback evidence 保证连续性，但可能稀释证据质量，何时应改为 hard-fail？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
System Variants
S1. 若接入向量检索替代 token/IDF，`risk_catalog_search.py` 的评分接口如何重构？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
S2. 若引入多证据源融合，`risk_agent.py` 如何做冲突证据仲裁？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Pitfalls
- 只说“用了检索就不会幻觉”，忽略检索召回质量本身。
- 不区分真实证据与 fallback 证据，导致审计判断失真。

### 10. Tool-based evidence retrieval 的作用是什么？
【Resume Highlight】对应简历：Version C #3，Version B #3。  
问题  
为什么要给 Risk Agent 接工具，不直接全靠 LLM？

简要回答  
工具把风险判断锚定到可复核知识库，降低纯生成幻觉，同时把证据 ID/snapshot 输出到结果中便于审计。

技术要点  
- 风险项包含 `evidence_ids/evidence_snippets`。  
- trace 记录 `risk_catalog_hits/top_ids/tool_status`。  
- 支持 `RISK_AGENT_ENABLE_CATALOG_TOOL` 开关控制。
Follow-ups
F1. tool disabled 与 tool error 的行为差异是什么？可引用 `ok/degraded_*` 状态。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F2. 如何做证据可追溯审计？可从 `evidence_ids` 到 `risk_catalog.json` 映射链解释。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F3. 开关关闭时如何保障最小可用性？可说明 Risk Agent 的降级路径。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Trade-offs
T1. 本地 catalog 可控但更新慢；外部实时检索更新快但不稳定，如何权衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
T2. top-k 召回更全但噪声更高；在 risk 评审中 k 值应如何设置？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
实施上在 requirement_review_v1/agents/risk_agent.py 落策略，在 requirement_review_v1/tools/risk_catalog_search.py 保持契约，并以 tests/test_risk_tool.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
System Variants
S1. 若支持按项目自定义 catalog，`tools/risk_catalog_search.py` 如何加载多份索引？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
S2. 若 evidence 需要来源置信度，`schemas/risk_schema.py` 应新增哪些字段？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/schemas/base.py 和 requirement_review_v1/schemas/reviewer_schema.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
Pitfalls
- 把工具调用结果当“绝对真相”，忽略 top-k 召回偏差。
- 开关策略没有纳入测试与发布检查，线上行为不可预测。

### 11. 工具不可用时系统会怎样？
问题  
如果风险目录检索报错或被禁用，流程会中断吗？

简要回答  
不会中断，Risk Agent 走 degraded 模式继续产出结果，并在 trace 标注退化原因。

技术要点  
- `risk_catalog_tool_status`：`ok/degraded_error/degraded_disabled`。  
- 报错时记录 `risk_catalog_tool_error`。  
- 单元测试覆盖禁用、报错、命中、未命中场景。
Follow-ups
F1. `degraded_error` 与 `degraded_disabled` 在 `review_service._derive_status` 中是否应区分严重级别？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. 工具连续失败时是否应触发熔断，熔断状态存在哪里最合适？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 不中断流程提升可用性，但可能输出低质量风险结论；如何设定可接受下限？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 详细错误写入 trace 便于定位，但可能暴露内部信息，如何做脱敏？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
System Variants
S1. 若引入远程风险服务，网络超时与重试策略应放在 tool 层还是 agent 层？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
S2. 若工具恢复后希望自动补跑 risk 节点，系统是否需要“局部重计算”能力？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Pitfalls
- 只讨论异常捕获，不定义质量退化告警阈值。
- 忽略降级场景的测试覆盖和上线验证。

### 12. 为什么 Reporter Agent 不调用 LLM？
问题  
报告生成为何做成确定性字符串拼接？

简要回答  
报告是可验证工件，确定性渲染更稳定、可回归、可 diff；避免最后一步再引入生成不确定性。

技术要点  
- `requirement_review_v1/agents/reporter_agent.py` 明确 “no LLM call”。  
- 通过 `_build_*` 系列函数拼 Markdown。  
- trace 里 reporter model 为 `"none"`。
Follow-ups
F1. `reporter_agent.py` 如何确保 Markdown 渲染顺序稳定，避免字段顺序漂移影响 diff？
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/reviewer_agent.py 与 requirement_review_v1/agents/planner_agent.py 明确改动，再用 requirement_review_v1/state.py 做回归验证。
原因：这能限制写冲突，并把故障收敛在单一责任域。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
F2. 当上游字段缺失时，reporter 如何标记“未知/缺失”而不是默默省略？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 确定性渲染可回归，但文本可读性可能不如 LLM 重写；如何在工程场景取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 将报告完全放在 reporter 生成，和在 service 层拼装模板相比谁更易维护？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若要提供“面向业务方”的润色版报告，是否增加二级 `writer_agent`，如何与审计版并存？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/reviewer_agent.py 和 requirement_review_v1/agents/planner_agent.py 实现改造，并围绕 requirement_review_v1/state.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/reviewer_agent.py、requirement_review_v1/agents/planner_agent.py。
- 回归与验证：requirement_review_v1/state.py。
- 关键设计决策：按 agent 定义字段 ownership，并只允许 partial state 更新。
- 工程原因：这能限制写冲突，并把故障收敛在单一责任域。
S2. 若要输出 HTML/PDF，多格式渲染应放在 reporter 还是独立导出层？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 误把“无 LLM”理解为“无风险”，忽略模板逻辑错误同样会影响交付。
- 没有对报告字段完整性做自动校验。

## 第四部分：系统可靠性

### 13. Conditional routing 如何避免无限循环？
【Resume Highlight】对应简历：Version B #3，Version C #4。  
问题  
澄清回路如何确保可终止？

简要回答  
双重门控：风险比例阈值 + 最大轮次上限。超过阈值且未达上限才循环，否则直接进入 reporter。

技术要点  
- `_HIGH_RISK_THRESHOLD = 0.4`。  
- `_MAX_REVISION_ROUNDS = 2`。  
- `_route_decider_node` 统一写 `routing_reason` 和 `revision_round`。
Follow-ups
F1. 阈值与轮次如何调参？可用 `eval/run_eval.py` 对比 `high_risk_ratio` 分布稳定性。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F2. 如何证明不会死循环？可结合 `tests/test_routing_loop.py` 与 trace `routing_rounds`。
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F3. 若 reviewer 异常导致 ratio=0，是否会提前结束？应如何在 trace 上识别。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/trace.py 与 requirement_review_v1/run_review.py 明确改动，再用 eval/run_eval.py 做回归验证。
原因：它支持回放、版本对比和迭代质量门禁。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Trade-offs
T1. 保守阈值可减少漏检，但会增加澄清轮次与成本；如何用评测数据选择阈值？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 固定轮次上限简单可靠，但对复杂 PRD 可能不足；是否引入动态轮次策略？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若把路由改成“风险分层策略”（高风险重审、低风险直接报告），`workflow.py` 如何扩展条件边？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若引入人工审批节点，`route_decider` 如何输出 machine/human 两类动作？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Pitfalls
- 只依赖单阈值，不设最大轮次硬上限。
- 未记录路由原因，出现误路由时无法复盘。

### 13.1 routing loop 如何设计？
【Resume Highlight】对应简历：Version B #3，Version C #4。  
问题  
如果让你从零设计“评审-澄清-复审”闭环，你会如何定义状态、路由条件与终止条件？

简要回答  
我会把 loop 设计成“可解释的有限状态机”：Reviewer 计算风险信号，Router 依据阈值与轮次上限决策 `clarify` 或 `finish`，每轮把路由原因与轮次写入 trace，保证可终止、可审计、可调参。

技术要点  
- 状态字段：`revision_round`、`high_risk_ratio`、`routing_reason`、`routing_rounds`（`requirement_review_v1/state.py`、`requirement_review_v1/workflow.py`）。  
- 路由策略：`high_risk_ratio > 0.4` 且 `revision_round < 2` 才进入澄清。  
- 澄清动作：`_clarify_node` 切 `parser_prompt_version=v1.1-clarify`，再回主链复审。  
- 审计与调参：通过 `run_trace.json` 观察轮次、原因、耗时与失败点。  
Follow-ups
F1. 你会如何给 `routing_reason` 设计枚举值，避免自由文本导致统计困难？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
F2. 在 `tests/test_routing_loop.py` 中，如何构造边界 case 验证“刚好等于阈值”的行为？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 使用显式规则可解释但僵化；引入学习式路由更灵活但难回归，如何选择？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 将 loop 信号只基于 `high_risk_ratio` 简单高效，但信息维度不足，是否应加入 coverage 信号？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/state.py 保持契约，并以 tests/test_routing_loop.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
System Variants
S1. 若支持多级澄清（parser clarify、planner clarify），状态机应如何拆分子循环？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/state.py 实现改造，并围绕 tests/test_routing_loop.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
S2. 若不同业务线阈值不同，配置应放在 `state` 输入还是全局配置？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 没有定义边界条件（`==阈值`）导致线上行为含糊。
- loop 设计没有对应的测试样例矩阵。

### 14. 系统如何监控 agent 执行状态？
问题  
怎样知道每个节点是否成功、执行到哪一步？

简要回答  
通过 trace span + progress hook 双层观测：节点内记录时延/状态，API 层实时维护 job 进度并暴露查询接口。

技术要点  
- `requirement_review_v1/utils/trace.py` 输出 start/end/duration/model/status 等字段。  
- `requirement_review_v1/workflow.py` 的 `_build_async_node/_build_sync_node` 注入 `progress_hook`。  
- `requirement_review_v1/server/app.py` 维护 `JobRecord.node_progress`。
Follow-ups
F1. `trace.py` 与 `JobRecord.node_progress` 可能不一致时，状态查询以谁为准？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. 节点耗时统计是否包含工具调用与 I/O，如何保证口径一致？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 细粒度 trace 提升诊断能力，但会增加落盘开销；如何控制采样或字段精度？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
T2. API 实时状态更新及时，但实现复杂；与任务完成后一次性回写相比如何取舍？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若接入外部 observability（Prometheus/OTel），`trace.py` 应如何映射 span 字段？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
S2. 若要跨服务链路追踪，是否在 `run_id` 外增加 `trace_id` 并透传到 MCP/HTTP？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/mcp_server/server.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 tests/test_mcp_tools.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
Pitfalls
- 只监控成功率，不追踪节点级失败原因和时延分布。
- trace 字段定义频繁变化却没有兼容策略。

### 15. 失败后还能拿到什么结果？
问题  
某个 Agent 失败时，系统是全失败还是部分可用？

简要回答  
是“部分可用 + 可诊断”：失败节点返回空结构并写错误 trace，已有中间结果仍会落盘到 report/trace 工件。

技术要点  
- `requirement_review_v1/run_review.py` 无论成功失败都写 `report.json` 与 `run_trace.json`。  
- `review_service` 可基于 trace 推导最终 `status`。  
- API 查询可读取已有 run 目录进行恢复展示。
Follow-ups
F1. `report.json` 部分字段为空时，前端/调用方如何区分“未生成”与“生成为空”？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F2. `review_service._derive_status` 如何避免把“部分失败”错误标成 success？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
Trade-offs
T1. 允许部分可用提升鲁棒性，但可能让调用方误判质量；是否需要质量等级字段？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 始终落盘便于审计，但会保留大量失败工件，存储清理策略如何设计？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若支持失败任务恢复执行，如何从 `run_trace.json` 选择重跑起点节点？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
S2. 若引入结果签名/哈希，如何保证 artifacts 未被篡改？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 只讲“不中断”，不讲结果可靠性边界。
- 没有定义失败语义（hard fail/soft fail）给上游系统。

### 16. 为什么要把 trace 单独写成 run_trace.json？
【Resume Highlight】对应简历：Version C #5，Version B #4。  
问题  
report.json 里已有 trace，为什么还单独存一份？

简要回答  
单独工件便于监控系统或脚本快速读取执行链，不必扫描完整业务报告；也方便增量写入和调试。

技术要点  
- `run_review.write_outputs` 同时写 `report.md/report.json/run_trace.json`。  
- `requirement_review_v1/server/app.py` 可从 `run_trace.json` 回推节点进度。  
- `eval/run_eval.py` 对 trace 做完整性校验。
Follow-ups
F1. `run_trace.json` 与 `report.json.trace` 双写时，冲突检测策略是什么？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F2. 你会如何设计 trace schema 版本，避免历史 run 文件无法被新工具解析？
简要回答  
从代码落点回答：先在 requirement_review_v1/schemas/base.py 与 requirement_review_v1/schemas/reviewer_schema.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/schemas/base.py、requirement_review_v1/schemas/reviewer_schema.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：在 schema 层定义 hard-fail 与 normalize 规则，阻止脏值下游扩散。
- 工程原因：即使 prompt 输出漂移，schema 契约也能保持工作流稳定。
Trade-offs
T1. 单独 trace 文件检索快，但维护双份数据一致性成本高，是否值得？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
T2. trace 保留更多原始字段利于排障，但会增加隐私/存储风险，如何裁剪？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
System Variants
S1. 若迁移到数据库存储 trace，`get_review_status` 如何兼容文件与库两种后端？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/server/app.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/run_review.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
S2. 若要支持实时 tail trace，现有文件落盘机制需要怎样改造？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Pitfalls
- 双写无校验，出现 report/trace 不一致。
- trace schema 演进不做版本控制，后续工具链断裂。

### 16.2 trace artifacts 有什么作用？
【Resume Highlight】对应简历：Version C #5，Version B #4。  
问题  
在 Agent 系统里，为什么要把 trace 当成“正式产物”而不是临时日志？

简要回答  
trace artifacts 是工程化质量闭环的基础：用于故障定位、回归对比、质量门禁和合规审计。没有 trace，系统只能“看到结果”，看不到过程质量。

技术要点  
- 节点级可观测：`start/end/duration_ms/model/status/input_chars/output_chars/prompt_version/error_message`。  
- 回归门禁：`eval/run_eval.py` 校验 `trace_complete`、`coverage_ratio_present` 等指标。  
- 诊断闭环：结构化失败可定位到 `raw_output_path` 与对应节点。  
- 版本对比：可比较不同 prompt/model/workflow 版本的执行差异。  
Follow-ups
F1. 哪些 trace 字段是“回归门禁最小集合”，哪些只是调试增强？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/trace.py 与 requirement_review_v1/run_review.py 明确改动，再用 eval/run_eval.py 做回归验证。
原因：它支持回放、版本对比和迭代质量门禁。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
F2. `raw_output_path` 生命周期如何管理，防止长期积压与敏感信息泄露？
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Trade-offs
T1. 保留完整 trace 提升可审计性，但治理成本高；何时做采样或分级保留？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
T2. 将 trace 作为正式产物会提升流程刚性，与快速迭代需求如何平衡？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将 trace 作为一等工件并维护稳定字段，而不是临时日志。
实施上在 requirement_review_v1/utils/trace.py 落策略，在 requirement_review_v1/run_review.py 保持契约，并以 eval/run_eval.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
System Variants
S1. 若要做跨版本对比报表，`eval/run_eval.py` 应新增哪些聚合维度？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 eval/run_eval.py 和 tests/test_routing_loop.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
S2. 若接入外部审计系统，trace 导出格式是 JSONL 还是标准事件协议更合适？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/llm_structured_call.py 和 requirement_review_v1/schemas/base.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
Pitfalls
- 把 trace 当普通日志，不设稳定字段契约。
- 只采集不消费，无法形成真实质量闭环。

### 16.1 生产化落地时，你会优先补哪些能力？
问题  
从“能跑”到“可上线”，这套系统还需要哪些关键工程能力？

简要回答  
优先补齐任务队列+Worker、幂等键、限流鉴权、trace/metrics 持久化、回放与 prompt registry。当前仓库已具备基础异步任务和 trace，但多数生产能力仍是 `TODO/未来改造`。

技术要点  
- 现状基础：`requirement_review_v1/server/app.py`（内存 `JobRecord` + `asyncio`）、`requirement_review_v1/utils/trace.py`。  
- 现状接口：`requirement_review_v1/mcp_server/server.py`、`requirement_review_v1/server/app.py`。  
- `TODO/未来改造`：外部队列与 Worker、幂等存储、全局限流/鉴权、metrics 持久化、任务回放、prompt registry。  
- 回归门禁可复用：`eval/run_eval.py`、`tests/test_mcp_tools.py`、`tests/test_routing_loop.py`。
Follow-ups
F1. 从内存 `JobRecord` 迁移到外部队列时，哪些接口契约必须保持不变以兼容现有客户端？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. 幂等键应绑定请求体哈希还是业务主键，如何处理重放请求？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 先补队列可扩展性高，但复杂度上升；与先补鉴权限流相比优先级如何定？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. prompt registry 增强灵活性，但会引入配置漂移风险，如何治理？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
实施上在 requirement_review_v1/prompts.py 落策略，在 requirement_review_v1/agents/parser_agent.py 保持契约，并以 requirement_review_v1/workflow.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/prompts.py、requirement_review_v1/agents/parser_agent.py。
- 回归与验证：requirement_review_v1/workflow.py。
- 关键设计决策：在 state 中携带 prompt 版本，并仅通过路由逻辑切换。
- 工程原因：每次输出都可追溯到明确的 prompt 版本与执行路径。
System Variants
S1. 若多区域部署，artifacts 存储如何做跨区域一致与就近读取？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若引入审批流，发布门禁应放在 CI、服务侧还是两者都要？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 生产化路线只列清单，不给落地顺序与验收标准。
- 忽略迁移过程的兼容层，容易一次性重构失败。

## 第五部分：扩展能力

### 17. MCP Server 在这套系统里的作用是什么？
【Resume Highlight】对应简历：Version B #4，Version C #6。  
问题  
为什么还要提供 MCP server，而不只保留 HTTP API？

简要回答  
MCP 提供标准工具接口，便于 AI 客户端（如支持 MCP 的助手）直接以 tool call 方式触发评审和取报告。

技术要点  
- `requirement_review_v1/mcp_server/server.py` 基于 `FastMCP("requirement-review-v1")`。  
- 暴露 `ping/review_prd/get_report` 三个工具。  
- 通过 stdio transport 运行，适配本地代理链路。
Follow-ups
F1. 何时优先 MCP、何时优先 HTTP？可从调用方形态（Agent 客户端 vs Web 服务）回答。
简要回答  
从代码落点回答：先在 requirement_review_v1/mcp_server/server.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 tests/test_mcp_tools.py 做回归验证。
原因：这可避免多集成间行为漂移，并简化回归测试。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
F2. MCP tool 输入输出契约如何与 `review_service` 对齐？可结合 `review_prd/get_report` 字段说明。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
F3. MCP 故障定位看哪里？可从 tool 返回错误与 run artifacts 路径切入。
简要回答  
从代码落点回答：先在 requirement_review_v1/agents/risk_agent.py 与 requirement_review_v1/tools/risk_catalog_search.py 明确改动，再用 tests/test_risk_tool.py 做回归验证。
原因：这可避免静默幻觉，并在工具失败时保持可审计性。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Trade-offs
T1. MCP 对 Agent 生态友好，但部署与权限治理复杂；和 HTTP-only 相比成本如何？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
实施上在 requirement_review_v1/mcp_server/server.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 tests/test_mcp_tools.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
T2. stdio transport 简单本地化，但跨机器调用受限；何时需要升级到网络 transport？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
实施上在 requirement_review_v1/mcp_server/server.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 tests/test_mcp_tools.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
System Variants
S1. 若要给多客户端暴露同一能力，是否保留 MCP+HTTP 双栈还是通过网关统一抽象？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/mcp_server/server.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 tests/test_mcp_tools.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
S2. 若接入企业 SSO，MCP tool 调用上下文如何透传身份信息到 `review_service`？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/agents/risk_agent.py 和 requirement_review_v1/tools/risk_catalog_search.py 实现改造，并围绕 tests/test_risk_tool.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/agents/risk_agent.py、requirement_review_v1/tools/risk_catalog_search.py。
- 回归与验证：tests/test_risk_tool.py。
- 关键设计决策：风险输出强制包含 evidence + tool_status，并保留可追踪的降级模式。
- 工程原因：这可避免静默幻觉，并在工具失败时保持可审计性。
Pitfalls
- 把 MCP 当成“另一个 REST”，忽略其 tool-call 协议语义。
- 只讲接入便利，不讲权限边界与运行隔离（当前需额外工程化补齐）。

### 18. 如何把系统集成到 AI 客户端？
【Resume Highlight】对应简历：Version B #4，Version C #6。  
问题  
外部智能体如何调用这个系统？

简要回答  
两种方式：MCP 工具调用（推荐给 Agent 客户端）或 FastAPI HTTP 调用（推荐给 Web/服务端集成）。

技术要点  
- MCP: `review_prd` 返回 run_id/metrics/artifacts。  
- HTTP: `POST /api/review` + `GET /api/review/{run_id}` + `GET /api/report/{run_id}`。  
- run_id 统一作为异步任务关联键。
Follow-ups
F1. MCP `review_prd` 与 HTTP `POST /api/review` 的返回字段应如何保持契约一致？
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. AI 客户端丢失 run_id 后，是否提供按时间/请求摘要检索任务的能力？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 统一 run_id 契约降低接入成本，但会暴露内部实现；是否需要对外映射公共 ID？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 让客户端轮询状态简单可靠，但请求量高；与回调/WebSocket 相比如何选择？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。API 层负责任务生命周期，评审执行下沉到 service/workflow。
实施上在 requirement_review_v1/server/app.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/run_review.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
System Variants
S1. 若客户端需要批量提交，接口应新增 batch endpoint 还是由客户端并发调用单条接口？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若要支持跨会话续查，run 元数据应落盘到文件还是数据库？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 接口文档只写 happy path，不写错误码与超时语义。
- 忽视 run_id 生命周期管理，导致检索与清理冲突。

### 19. FastAPI API 层做了哪些工程化设计？
【Resume Highlight】对应简历：Version B #4，Version C #6。  
问题  
API 层如何承载异步长任务并反馈进度？

简要回答  
通过内存 JobRecord + asyncio task 后台执行，前台轮询查询进度；支持输入文本或文件路径。

技术要点  
- `ReviewCreateRequest` 强约束“二选一输入”。  
- `_run_job` 内调用 `review_prd_text_async`。  
- `get_review_status` 支持运行中/落盘后状态回读。
Follow-ups
F1. 为什么用内存 `JobRecord`，它的边界是什么？可指出重启丢失与单实例限制。
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
F2. 状态查询如何在任务结束后恢复？可解释 `run_trace.json` 回读逻辑。
简要回答  
从代码落点回答：先在 requirement_review_v1/utils/llm_structured_call.py 与 requirement_review_v1/schemas/base.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：它将解析错误与契约错误分离，使故障可定位。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/utils/llm_structured_call.py、requirement_review_v1/schemas/base.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用分层链路：tools-first、fallback JSON 解析、再做 schema 校验。
- 工程原因：它将解析错误与契约错误分离，使故障可定位。
F3. 未来如何扩展到多 worker？可对比当前实现与 `TODO` 队列化方案。
简要回答  
从代码落点回答：先在 requirement_review_v1/server/app.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/run_review.py 做回归验证。
原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
Trade-offs
T1. 内存任务管理实现快但不可横向扩展；与外部任务系统相比何时该升级？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. API 返回“已接收”提升吞吐，但调用方复杂度上升；同步返回结果是否有必要保留？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若引入 Celery/RQ，`get_review_status` 如何映射外部任务状态到现有字段？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/server/app.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/run_review.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/server/app.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/run_review.py。
- 关键设计决策：API 层负责任务生命周期，评审执行下沉到 service/workflow。
- 工程原因：入口变化可被隔离，同时 run_id 与 artifacts 保持一致。
S2. 若支持文件上传大文档，`ReviewCreateRequest` 应如何扩展并控制 I/O 压力？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 把“异步 task”误认为“已具备分布式任务系统”。
- 忽略幂等键与重复提交控制，导致同一请求重复执行。

### 20. Evaluation framework 如何保障迭代质量？
【Resume Highlight】对应简历：Version B #4，Version C #5。  
问题  
项目如何做回归评估，不只是“能跑就行”？

简要回答  
有独立评估脚本和针对关键能力的测试集，验证 report 结构、trace 完整性、覆盖率字段与关键路由/工具行为。

技术要点  
- `eval/run_eval.py`：批量 case 回归，生成聚合报告。  
- `tests/test_routing_loop.py`：循环与终止条件。  
- `tests/test_risk_tool.py`：证据工具命中/降级路径。  
- `tests/test_schema_validation.py`：schema 校验与类型归一化。
Follow-ups
F1. `eval/run_eval.py` 中 `trace_complete` 与 `coverage_ratio_present` 的门限怎么定，谁来维护？
简要回答  
从代码落点回答：先在 eval/run_eval.py 与 tests/test_routing_loop.py 明确改动，再用 tests/test_schema_validation.py 做回归验证。
原因：发布前可同时发现质量退化和逻辑回归。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
F2. 评测失败后如何快速定位到具体节点和具体版本（prompt/model/workflow）？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/state.py 明确改动，再用 tests/test_routing_loop.py 做回归验证。
原因：这样可保证循环行为可预测、可测试、且便于安全调参。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/state.py。
- 回归与验证：tests/test_routing_loop.py。
- 关键设计决策：将路由集中在 route_decider，并用 revision_round + high_risk_ratio 控制循环。
- 工程原因：这样可保证循环行为可预测、可测试、且便于安全调参。
Trade-offs
T1. 严格门禁可保质量但会降低迭代速度；如何设计“阻断发布”与“告警通过”双阈值？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 单元测试快但覆盖窄，离线评测慢但贴近真实；CI 中如何组合？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若新增线上 shadow eval，如何避免对主链路延迟和成本造成明显影响？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 eval/run_eval.py 和 tests/test_routing_loop.py 实现改造，并围绕 tests/test_schema_validation.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：eval/run_eval.py、tests/test_routing_loop.py。
- 回归与验证：tests/test_schema_validation.py。
- 关键设计决策：采用双门禁：数据集评测看分布漂移，单测覆盖边界规则。
- 工程原因：发布前可同时发现质量退化和逻辑回归。
S2. 若接入业务反馈指标（人工评分），如何与离线技术指标合并成发布决策？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Pitfalls
- 评测只关注通过率，不追踪退化幅度与原因。
- 指标定义变化后未做历史可比性处理。

### 20.1 如果要支持企业级生产发布，你会如何扩展？
问题  
当业务量提升到多团队共用时，系统扩展路线应该是什么？

简要回答  
按“平台化能力”扩展：统一任务队列与存储、标准化评测门禁、模型与 prompt 配置中心、租户级鉴权与配额，再把关键链路做成可复用服务能力。

技术要点  
- 服务化：异步任务队列 + 持久化作业状态。  
- 治理化：版本化评测门禁与发布准入。  
- 多租户：API key/租户隔离/配额与审计日志。
Follow-ups
F1. 企业级发布下，`mcp_server/server.py` 与 `server/app.py` 的鉴权策略应如何统一？
简要回答  
从代码落点回答：先在 requirement_review_v1/mcp_server/server.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 tests/test_mcp_tools.py 做回归验证。
原因：这可避免多集成间行为漂移，并简化回归测试。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/mcp_server/server.py、requirement_review_v1/service/review_service.py。
- 回归与验证：tests/test_mcp_tools.py。
- 关键设计决策：MCP 与 HTTP 共享同一 service 契约，仅传输层不同。
- 工程原因：这可避免多集成间行为漂移，并简化回归测试。
F2. 多租户配额超限后，系统返回码与降级行为如何定义才便于上游治理？
简要回答  
从代码落点回答：先在 requirement_review_v1/workflow.py 与 requirement_review_v1/service/review_service.py 明确改动，再用 requirement_review_v1/utils/trace.py 做回归验证。
原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。同时说明异常处理与降级路径，不能只讲 happy path。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
Trade-offs
T1. 强隔离提升安全但提高运维复杂度；与共享池模型如何权衡成本与性能？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
T2. 引入更多治理组件（网关/队列/审计）提升稳态，但会拉长故障链路，如何控制复杂度？
简要回答  
取舍优先级应是“可观测、可回归”高于局部优化。将编排、执行、观测分层，避免跨层耦合。
实施上在 requirement_review_v1/workflow.py 落策略，在 requirement_review_v1/service/review_service.py 保持契约，并以 requirement_review_v1/utils/trace.py 作为发布前证据。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
System Variants
S1. 若要求私有化部署，哪些组件必须本地化（模型、存储、日志、评测）？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/workflow.py 和 requirement_review_v1/service/review_service.py 实现改造，并围绕 requirement_review_v1/utils/trace.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/workflow.py、requirement_review_v1/service/review_service.py。
- 回归与验证：requirement_review_v1/utils/trace.py。
- 关键设计决策：将编排、执行、观测分层，避免跨层耦合。
- 工程原因：稳定边界能让你基于 run_id 与 trace 快速排障，无需重复检查每个入口。
S2. 若支持混合云，artifacts 与 trace 的跨环境同步方案如何设计？
简要回答  
变体改造时先保持 `run_id -> state -> artifacts` 主契约不变，再扩展架构。
具体在 requirement_review_v1/utils/trace.py 和 requirement_review_v1/run_review.py 实现改造，并围绕 eval/run_eval.py 补充验证，避免破坏现有链路。
技术要点
- 关键代码模块：requirement_review_v1/utils/trace.py、requirement_review_v1/run_review.py。
- 回归与验证：eval/run_eval.py。
- 关键设计决策：将 trace 作为一等工件并维护稳定字段，而不是临时日志。
- 工程原因：它支持回放、版本对比和迭代质量门禁。
Pitfalls
- 只谈扩容，不谈安全合规与审计闭环。
- 没有分阶段里程碑，企业级方案容易停留在口号。

## Code Map

| 能力点 | 关键模块/文件 |
| --- | --- |
| LangGraph 编排与条件路由 | `requirement_review_v1/workflow.py`, `requirement_review_v1/state.py` |
| Prompt 模板与版本切换 | `requirement_review_v1/prompts.py`, `requirement_review_v1/agents/parser_agent.py`, `requirement_review_v1/workflow.py` |
| Structured Outputs 与降级解析 | `requirement_review_v1/utils/llm_structured_call.py` |
| Schema 校验与类型归一化 | `requirement_review_v1/schemas/*.py`, `requirement_review_v1/schemas/base.py` |
| 风险证据检索与注入 | `requirement_review_v1/tools/risk_catalog_search.py`, `requirement_review_v1/agents/risk_agent.py` |
| 评审指标（coverage/high_risk） | `requirement_review_v1/metrics/coverage.py`, `requirement_review_v1/agents/reviewer_agent.py` |
| 可观测与 Trace | `requirement_review_v1/utils/trace.py`, `requirement_review_v1/run_review.py`, `requirement_review_v1/service/review_service.py` |
| FastAPI 异步任务接口 | `requirement_review_v1/server/app.py` |
| MCP 工具化接入 | `requirement_review_v1/mcp_server/server.py` |
| 回归评测与测试门禁 | `eval/run_eval.py`, `tests/test_routing_loop.py`, `tests/test_risk_tool.py`, `tests/test_schema_validation.py`, `tests/test_mcp_tools.py` |






