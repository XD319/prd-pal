# approval-loop-design (2) 差距分析与分阶段实施提示词

> 基于 `D:\download\approval-loop-design (2).md` 与当前仓库实现现状整理。
> 目标不是机械照抄设计稿，而是识别当前代码基线下真正值得实现的能力，并给出可直接执行的 phased prompts。

---

## 1. 现状结论

当前仓库已经具备设计稿主链路中的一部分基础能力：

- `source connector -> gating -> normalizer -> parallel reviewers -> aggregator -> review artifacts`
- `review_requirement` MCP facade
- FastAPI 结果查询接口与前端工作台
- URL / Feishu / Notion / local file 输入连接器
- 并行评审失败降级、`partial_review`、冲突检测、结果产物落盘

但和设计稿 `v5.0` 相比，仍然存在 5 类关键缺口：

1. 评审入口和 gating 还不够“产品化”
2. reviewer 仍以启发式规则为主，缺少工具调用与证据链
3. 缺少设计稿定义的 Clarification Gate 闭环
4. 缺少长期记忆 / seed memory / RAG 注入
5. 前端还无法承接“澄清、证据、冲突裁决、记忆引用”这些新增能力

---

## 2. 设计项对照

### 2.1 已实现或基本实现

| 设计项 | 当前状态 | 备注 |
|---|---|---|
| Source Connector | 已实现 | `local_file`、`url`、`feishu`、`notion` 已存在 |
| Gating 基础模式切换 | 已实现 | 已有 `single_review / parallel_review` 决策 |
| Requirement Normalizer 基础裁剪 | 已实现 | 已有 summary / acceptance / dependency / risk 等提取 |
| 四角色并行评审 | 已实现 | `product / engineering / qa / security` 已存在 |
| Aggregator 基础聚合 | 已实现 | 已有 findings / risks / open_questions / conflicts |
| partial review 容错 | 已实现 | reviewer 超时或失败可降级 |
| `review_result.json` / `review_report.md` | 已实现 | 产物已存在 |
| MCP `review_requirement` | 已实现 | review-only facade 已存在 |
| 前端提审、轮询、结果展示 | 已实现 | 已有首页、运行详情页、历史列表 |

### 2.2 部分实现

| 设计项 | 当前状态 | 缺什么 |
|---|---|---|
| QuickTriage / mode 控制 | 部分实现 | 有 gating，但没有设计稿中的 `skip / quick / full` 产品契约 |
| 动态 reviewer 选择 | 部分实现 | 当前并行评审固定跑四个 reviewer |
| Normalizer 按角色裁剪 | 部分实现 | 有 reviewer input，但字段还不够丰富，缺少 domain tags / scope / cache / memory context |
| 冲突检测 | 部分实现 | 已有 severity + semantic conflict，但没有 Delivery Reviewer 裁决结果 |
| 输出 schema | 部分实现 | 缺 `summary`、`tool_calls`、`clarification`、`evidence`、`similar_reviews_referenced` 等 |
| 前端结果视图 | 部分实现 | 能看基础结果，但不能消费 reviewer 选择、证据、裁决、澄清状态 |

### 2.3 尚未实现

| 设计项 | 当前状态 |
|---|---|
| Clarification Gate（识别关键歧义、收集回答、更新 findings） | 未实现 |
| Delivery Reviewer 冲突裁决 | 未实现 |
| RAG 长期记忆 / seed memory / memory writer | 未实现 |
| reviewer 工具调用链（公网搜索、CVE、Jira、Confluence 等） | 未实现 |
| finding 级 evidence / tool trace | 未实现 |
| `mode=auto/quick/full`、`use_rag`、`on_complete_webhook` 契约 | 未实现 |

---

## 3. 合理性评估

### 3.1 高优先级，建议实现

这些能力和设计稿高度一致，而且对当前仓库的 review-engine 主线有直接收益：

1. `mode=auto/quick/full` 契约与更稳健的 triage
2. 动态 reviewer 选择
3. reviewer 证据与工具调用抽象
4. Clarification Gate 闭环
5. Delivery Reviewer 冲突裁决
6. 轻量长期记忆层与 Normalizer 缓存
7. 前端支持澄清、证据、裁决、记忆引用

### 3.2 中优先级，建议做成可选增强

这些能力有价值，但应建立在主链路稳定后再落地：

1. Confluence / Jira / CVE 等企业集成
2. `on_complete_webhook`
3. 更复杂的 reviewer tool routing 策略
4. 团队共享型向量库（Qdrant / Weaviate）

### 3.3 现阶段不建议直接照抄

这些点如果直接按设计稿硬上，容易引入不必要复杂度：

1. 用“`< 200 词` 直接 skip”作为唯一 triage 规则
   - 当前仓库主要处理中文 PRD，这个阈值不稳定，应该改成“字符数 + 结构完整性 + 风险关键词”组合判断。
2. Product Reviewer 默认实时做竞品搜索
   - 这会引入额外时延和外部依赖，且对核心 review 质量提升不如 engineering / security 工具调用明显。
3. 一上来就做完整向量数据库方案
   - 当前更合理的是先做本地 file-backed memory abstraction，保留 Chroma 作为可选实现。

---

## 4. 建议实施范围

本次建议真正推进的功能集合如下：

### 4.1 后端

- 统一 review 模式契约：`auto / quick / full`
- 新增 QuickTriage，并和现有 gating 合并
- 并行评审改成动态 reviewer 选择
- reviewer 输出支持 `evidence`、`tool_calls`、`ambiguity_type`
- aggregator 支持：
  - `summary`
  - `tool_calls`
  - `clarification` 元数据
  - Delivery Reviewer 裁决结果
- 新增 Clarification Gate：
  - 识别关键歧义
  - 暂停等待回答
  - 应用回答后二次聚合
- 新增长期记忆 abstraction：
  - `NoopMemoryStore`
  - `FileBackedMemoryStore`
  - seed import
  - normalizer cache

### 4.2 API / MCP

- `review_requirement` 对齐：
  - `mode`
  - `use_rag`
  - `clarification` 状态
  - `reviewers_used`
  - `tool_calls`
- 新增 Clarification 继续执行接口
- 保持 `review_prd` 与现有扩展工作流兼容，不删除旧能力

### 4.3 前端

- 结果总览新增：
  - review mode
  - selected reviewers
  - partial review / manual review banner
  - clarification status
  - memory references
- 新增 reviewer insights 面板：
  - reviewer 级 findings
  - tool evidence
  - failure / timeout 状态
- 新增 conflicts & resolution 面板
- 新增 clarification 回答面板
- 在 run 详情页展示“可继续执行的评审”状态，而不是只展示静态结果

---

## 5. 推荐 phase 顺序

```text
Phase 1  Review Contract + Triage + Dynamic Reviewer Selection
    ->
Phase 2  Reviewer Evidence + Tool Call Abstraction + Frontend Result Upgrade
    ->
Phase 3  Clarification Gate + API/MCP Resume Flow + Frontend Clarification UI
    ->
Phase 4  Delivery Reviewer Conflict Arbitration + Conflict Resolution UI
    ->
Phase 5  Memory Layer + Seed Import + Cache + Frontend Memory Trace
```

顺序原则：

- 先稳住对外 contract，再补 reviewer 能力
- 先补“证据”和“澄清”，再补“长期记忆”
- 前端每个 phase 都跟随后端 contract 一起进化，避免最后一次性重做

---

## 6. 全局执行约束

以下规则适用于所有 phase：

1. 每个 phase 都必须从 `main` 新建独立子分支。
2. 每个 phase 完成后都要先做 merge/push readiness assessment。
3. 所有 Python 测试必须使用：

```powershell
& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest ...
```

4. 如有前端改动，必须额外运行：

```powershell
npm run build
```

5. 只有满足以下条件，才允许合并和推送：
   - phase 对应测试通过
   - 前端构建通过（若有前端改动）
   - 变更范围与 phase 目标一致
   - 无阻断性已知问题

6. readiness assessment 通过后，执行：

```powershell
git checkout main
git pull --ff-only
git merge --no-ff <phase-branch>
git push origin main
```

7. 如果 readiness assessment 不通过：
   - 列出 blocker
   - 不合并
   - 不推送

---

## 7. 每个 phase 的固定收尾模板

执行下面任一 phase 时，把这段原样附在 prompt 末尾：

```text
Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / not applicable / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff <phase-branch>`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 8. Phase 1：Review Contract、Triage 与动态 Reviewer 选择

**分支名**：`phase/p1-review-contract-triage`

### 目标

- 把当前 `review_mode_override` 收敛成设计稿友好的 `mode=auto/quick/full`
- 增加 QuickTriage
- 并行评审按 PRD 特征动态选择 reviewer
- 前端显示 mode、gating reasons、selected reviewers、partial review 状态

### 给 Codex 的提示词

```text
你正在 `Multi-Agent-Requirement-Review-and-Delivery-Planning-System` 仓库中工作。

如果这是首次开始本 phase，请先创建并切换分支：
- `git checkout main`
- `git switch -c phase/p1-review-contract-triage`

如果该分支已存在，则：
- `git switch phase/p1-review-contract-triage`

任务目标：
实现 review-engine 的第一阶段收敛：统一 review contract、增加 QuickTriage、启用动态 reviewer 选择，并补齐前端基础展示。

先阅读以下文件：
- `requirement_review_v1/review/gating.py`
- `requirement_review_v1/review/normalizer.py`
- `requirement_review_v1/review/parallel_review_manager.py`
- `requirement_review_v1/workflow.py`
- `requirement_review_v1/service/review_service.py`
- `requirement_review_v1/mcp_server/server.py`
- `requirement_review_v1/server/app.py`
- `frontend/src/pages/RunDetailsPage.jsx`
- `frontend/src/components/ReviewSummaryPanel.jsx`
- `frontend/src/utils/derivers.js`

实现要求：
1. 在 review service / MCP / workflow 中引入统一 `mode` 契约：
   - `auto`
   - `quick`
   - `full`
   同时兼容当前 `review_mode_override`，但对外文档和新接口优先使用 `mode`。

2. 在 gating 层新增 QuickTriage：
   - 不要使用“< 200 词”作为唯一规则
   - 改成“字符数 + 结构完整性 + 风险关键词 + 跨系统信号”的组合判断
   - 输出：
     - selected_mode
     - reasons
     - whether skipped
   - 若信息极度不足，可返回 `skip`

3. 在 parallel review 中实现动态 reviewer 选择：
   - 不再默认总是跑四个 reviewer
   - 根据 normalized requirement 决定是否启用：
     - product
     - engineering
     - qa
     - security
   - 将 `reviewers_used`、`reviewers_skipped`、`gating_reasons` 写入聚合结果和 report metadata

4. 扩展输出 schema：
   - `meta.review_mode`
   - `meta.gating`
   - `meta.reviewers_used`
   - `meta.reviewers_skipped`
   - `summary.overall_risk`
   - `summary.in_scope`
   - `summary.out_of_scope`
   - 仍保持现有结果兼容

5. 更新 FastAPI / MCP：
   - `review_requirement` 支持 `mode`
   - `review_requirement` 返回 `reviewers_used`
   - API 结果接口能暴露 gating 信息

6. 前端改动：
   - 在 run detail summary 区新增：
     - mode badge
     - selected reviewers
     - skipped reviewers
     - partial/manual review banner
   - 在结果页增加一个简洁的 gating info 区块

7. 测试要求：
   - 更新或新增：
     - `tests/test_gating.py`
     - `tests/test_parallel_review_manager.py`
     - `tests/test_mcp_review_requirement.py`
     - `tests/test_server_app_review_result.py`
   - 如有前端改动，确保 `npm run build` 通过

8. 必跑命令：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_gating.py tests/test_parallel_review_manager.py tests/test_mcp_review_requirement.py tests/test_server_app_review_result.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`
   - `npm run build`

Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff phase/p1-review-contract-triage`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 9. Phase 2：Reviewer 证据链、工具调用抽象与前端结果升级

**分支名**：`phase/p2-reviewer-evidence-and-ui`

### 目标

- 给 reviewer 加入可扩展的 evidence / tool call 抽象
- 先实现“本地可验证 + 可配置外部增强”的最小能力
- 前端可以展示证据、tool calls、reviewer 级结果

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

如果这是首次开始本 phase，请先创建并切换分支：
- `git checkout main`
- `git switch -c phase/p2-reviewer-evidence-and-ui`

如果该分支已存在，则：
- `git switch phase/p2-reviewer-evidence-and-ui`

任务目标：
把 reviewer 从“纯启发式黑盒”升级为“带证据和工具轨迹的 reviewer framework”，并同步补齐前端展示。

优先阅读：
- `requirement_review_v1/review/reviewer_agents/base.py`
- `requirement_review_v1/review/reviewer_agents/*.py`
- `requirement_review_v1/review/aggregator.py`
- `requirement_review_v1/tools/risk_catalog_search.py`
- `requirement_review_v1/subflows/risk_analysis.py`
- `requirement_review_v1/service/review_service.py`
- `frontend/src/components/FindingsPanel.jsx`
- `frontend/src/components/RisksPanel.jsx`
- `frontend/src/pages/RunDetailsPage.jsx`

实现要求：
1. 为 reviewer output 新增结构字段：
   - `evidence`
   - `tool_calls`
   - `ambiguity_type`
   - `clarification_question`
   - `reviewer_status_detail`

2. 设计一个最小工具抽象层：
   - 不要求一上来接通全部公网搜索
   - 先支持：
     - 本地 risk catalog / rule evidence
     - 可选的 web search adapter 接口
     - 可选的 CVE / Jira / Confluence adapter stub
   - 没有配置时必须优雅降级

3. reviewer 行为要求：
   - engineering / security 优先补 evidence
   - qa 可接本地 defect heuristic 或 stub
   - product 暂不强制做实时竞品搜索，但保留 tool hook

4. aggregator 要能汇总：
   - finding 级 evidence
   - run 级 `tool_calls`
   - reviewer-level notes

5. 输出 contract 至少新增：
   - `meta.tool_calls`
   - finding 的 `evidence`
   - reviewer 级 `status_detail`

6. 前端改动：
   - 在 RunDetails 页面新增 reviewer insights 区块
   - findings 卡片支持展开 evidence
   - 增加 tool call 列表或 trace 面板
   - 对 reviewer timeout / skipped / completed 做状态徽标

7. 测试要求：
   - `tests/test_review_aggregator.py`
   - `tests/test_parallel_review_manager.py`
   - 如需要新增：
     - `tests/test_reviewer_evidence_contract.py`
     - `tests/test_review_requirement_mcp_tool_calls.py`

8. 必跑命令：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_aggregator.py tests/test_parallel_review_manager.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`
   - `npm run build`

Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff phase/p2-reviewer-evidence-and-ui`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 10. Phase 3：Clarification Gate、可恢复评审接口与前端澄清 UI

**分支名**：`phase/p3-clarification-gate`

### 目标

- 实现设计稿中最关键但目前完全缺失的 Clarification Gate
- 支持“生成问题 -> 用户回答 -> 应用回答 -> 更新结果”
- 前端直接在 run 详情页完成澄清，不需要手工改 PRD 再重跑

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

如果这是首次开始本 phase，请先创建并切换分支：
- `git checkout main`
- `git switch -c phase/p3-clarification-gate`

如果该分支已存在，则：
- `git switch phase/p3-clarification-gate`

任务目标：
实现 post-review Clarification Gate，使高严重度且不可推断的问题可以暂停等待回答，并在回答后更新 findings。

优先阅读：
- `requirement_review_v1/review/aggregator.py`
- `requirement_review_v1/workflow.py`
- `requirement_review_v1/service/review_service.py`
- `requirement_review_v1/server/app.py`
- `requirement_review_v1/mcp_server/server.py`
- `frontend/src/pages/RunDetailsPage.jsx`
- `frontend/src/components/OpenQuestionsPanel.jsx`
- `frontend/src/hooks/useReviewRun.js`

实现要求：
1. 新增 `clarification_gate.py` 或等价模块，能力包括：
   - 识别需要 clarification 的 finding
   - 限制问题数 <= 3
   - 只针对：
     - severity = high
     - ambiguity_type = unanswerable

2. review result 中新增 clarification 结构：
   - `triggered`
   - `status` (`pending` / `answered` / `not_needed`)
   - `questions`
   - `answers_applied`
   - `findings_updated`

3. 增加继续执行接口：
   - FastAPI: 例如 `POST /api/review/{run_id}/clarification`
   - MCP: 例如 `answer_review_clarification`
   - 输入 answers 后，重新评估受影响 findings，而不是整轮从零重跑

4. 若暂时无法做到严格增量重评估：
   - 允许“复用 normalizer/cache 后重新聚合”
   - 但必须保证对外呈现为 clarification resume flow

5. 输出更新要求：
   - finding 支持：
     - `clarification_applied`
     - `original_severity`
     - `user_clarification`

6. 前端改动：
   - Open Questions 区升级成 Clarification Panel
   - 当 run 存在待回答问题时，显示回答表单
   - 回答提交后刷新结果
   - 显示哪些 findings 已被 clarification 更新

7. 测试要求：
   - 新增：
     - `tests/test_clarification_gate.py`
     - `tests/test_server_app_clarification.py`
     - `tests/test_mcp_review_clarification.py`
   - 如需要更新：
     - `tests/test_review_service_handoff.py`

8. 必跑命令：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_clarification_gate.py tests/test_server_app_clarification.py tests/test_mcp_review_clarification.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`
   - `npm run build`

Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff phase/p3-clarification-gate`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 11. Phase 4：Delivery Reviewer 冲突裁决与冲突展示升级

**分支名**：`phase/p4-conflict-arbitration`

### 目标

- 在现有 conflict detection 之上，新增裁决能力
- 把“检测到冲突”升级成“给出 resolution / requires_manual_resolution”
- 前端展示冲突及裁决建议

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

如果这是首次开始本 phase，请先创建并切换分支：
- `git checkout main`
- `git switch -c phase/p4-conflict-arbitration`

如果该分支已存在，则：
- `git switch phase/p4-conflict-arbitration`

任务目标：
为高严重度冲突引入 Delivery Reviewer 裁决能力，并将 resolution 纳入 review contract 与前端展示。

优先阅读：
- `requirement_review_v1/review/aggregator.py`
- `requirement_review_v1/review/reviewer_agents/*.py`
- `requirement_review_v1/service/review_service.py`
- `frontend/src/pages/RunDetailsPage.jsx`
- `frontend/src/utils/derivers.js`

实现要求：
1. 新增 `delivery_reviewer.py` 或等价实现：
   - 输入 conflict + product / engineering / qa / security 视角摘要
   - 输出：
     - `recommendation`
     - `reasoning`
     - `decided_by`
     - `needs_human`

2. aggregator 更新：
   - 对高严重度 conflict 触发 arbitration
   - 冲突结果中新增：
     - `resolution`
     - `requires_manual_resolution`
   - 仍保留已有 conflict detection 规则

3. 如果当前阶段不接入 LLM：
   - 允许先做规则化 arbitration
   - 但结构必须对齐未来 LLM/agent 裁决输出

4. review report / review result 要能显示：
   - unresolved conflicts
   - resolved conflicts
   - 裁决理由

5. 前端改动：
   - 新增 ConflictResolutionPanel
   - 按“已裁决 / 需人工处理”分组显示
   - 展示 recommendation 与 reasoning

6. 测试要求：
   - 更新：
     - `tests/test_review_aggregator.py`
   - 新增：
     - `tests/test_delivery_reviewer.py`

7. 必跑命令：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_aggregator.py tests/test_delivery_reviewer.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`
   - `npm run build`

Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff phase/p4-conflict-arbitration`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 12. Phase 5：Memory Layer、Seed Import、Normalizer Cache 与记忆可视化

**分支名**：`phase/p5-review-memory`

### 目标

- 做一个适合当前仓库阶段的轻量长期记忆层
- 先支持本地持久化和 seed 导入，再保留向量库为可选增强
- 前端能看到“本次评审引用了哪些历史记忆”

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

如果这是首次开始本 phase，请先创建并切换分支：
- `git checkout main`
- `git switch -c phase/p5-review-memory`

如果该分支已存在，则：
- `git switch phase/p5-review-memory`

任务目标：
实现轻量 review memory abstraction、seed import、normalizer cache，并把 memory references 暴露给 API/MCP/前端。

优先阅读：
- `requirement_review_v1/review/normalizer.py`
- `requirement_review_v1/review/gating.py`
- `requirement_review_v1/service/review_service.py`
- `requirement_review_v1/run_review.py`
- `data/`
- `frontend/src/components/ReviewSummaryPanel.jsx`

实现要求：
1. 新增 memory abstraction：
   - `BaseMemoryStore`
   - `NoopMemoryStore`
   - `FileBackedMemoryStore`
   - 可选预留 `ChromaMemoryStore`

2. 先不要强依赖外部向量库。
   - 默认使用 Noop 或 file-backed
   - 如果配置了路径或开关，再启用持久化 memory

3. 实现 seed import：
   - 在仓库内新增 `memory/seeds/` 或等价目录
   - 提供初始高质量案例
   - 首次启动或显式命令时导入

4. Normalizer/cache 要求：
   - 相同 PRD 内容可复用 normalizer 结果
   - 缓存命中信息写入 meta
   - memory retrieval 的引用 ID 写入：
     - `meta.similar_reviews_referenced`
     - `meta.rag_enabled`

5. 输出中新增：
   - `memory_hits`
   - `similar_reviews_referenced`
   - `normalizer_cache_hit`

6. 前端改动：
   - 在 summary / reviewer insight 中显示 memory hit 数量
   - 支持展开查看引用的 seed 或历史案例摘要

7. 测试要求：
   - 新增：
     - `tests/test_review_memory.py`
     - `tests/test_normalizer_cache.py`
   - 更新：
     - `tests/test_mcp_review_requirement.py`

8. 必跑命令：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_memory.py tests/test_normalizer_cache.py tests/test_mcp_review_requirement.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`
   - `npm run build`

Phase 收尾要求：
1. 先输出本 phase 的 merge/push readiness assessment，必须明确写出：
   - tests passed / failed
   - frontend build passed / failed
   - blockers
   - whether this phase is merge-ready and push-ready
2. 如果结论是 merge-ready and push-ready，再执行：
   - `git checkout main`
   - `git pull --ff-only`
   - `git merge --no-ff phase/p5-review-memory`
   - `git push origin main`
3. 如果存在 blocker，则停止在 phase 分支，不要合并也不要推送。
4. 所有 Python 测试必须在 `D:\venvs\marrdp` 虚拟环境内运行。
```

---

## 13. 建议暂缓的设计项

以下内容不建议放进上述 5 个 phase 的主线：

1. `on_complete_webhook`
2. 团队共享向量库（Qdrant / Weaviate）
3. Product Reviewer 默认竞品实时搜索
4. Jira / Confluence / CVE 的真实在线接通

如果后续确实需要，建议单独开“Phase X Optional Integrations”，不要和主线 review contract 混做。

---

## 14. 建议实际执行顺序

推荐这样下发给 Codex：

1. `Phase 1`
2. `Phase 2`
3. `Phase 3`
4. `Phase 4`
5. `Phase 5`

原因：

- `Phase 1` 先把 contract 和 reviewer orchestration 基线打稳
- `Phase 2` 再让 reviewer 输出真正“可解释”
- `Phase 3` 是最关键的用户闭环
- `Phase 4` 在 Clarification 基础上再做 conflict arbitration，效果最好
- `Phase 5` 最适合在 schema 和闭环稳定后补 memory

---

## 15. 最终判断

从当前仓库基线出发，设计稿里真正“值得做”的不是整篇全部照搬，而是下面这条收敛后的路线：

```text
稳住 review contract
  -> 动态 reviewer 选择
  -> reviewer 证据链
  -> clarification gate
  -> conflict arbitration
  -> memory layer
  -> 前端完整承接这些状态
```

这样落地之后，项目会明显更接近设计稿中的“多 Agent PRD 评审系统”，同时不会因为一次性引入过多企业集成和外部基础设施而失控。
