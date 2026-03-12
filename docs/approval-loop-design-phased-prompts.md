# 基于 approval-loop-design 的分步实现提示词

本文档基于外部设计文档 `approval-loop-design (1).md`，并结合当前仓库现状，对项目主架构做出一个更明确的收敛判断：

当前项目的**主架构**建议收缩到“输出评审结果”为止，而不是继续把 bundle、审批、handoff、execution 作为默认主线叙事。

推荐主线：

```text
source connector
  -> complexity/risk gating
  -> requirement normalizer
  -> parallel reviewers
  -> review aggregator
  -> review_result.json / review_report.md
  -> review-only MCP / API
```

后续能力暂时保留在仓库中，但退出主架构定义：

- bundle generation
- approval state machine
- handoff
- execution orchestration
- traceability
- notifications

它们的定位应调整为：

- extension layer
- experimental orchestration layer
- future workflow layer

不是删代码，而是退出默认主线。

---

## 一、主架构收缩原则

### 1.1 主架构只保留到 review result

项目默认对外定位建议改成：

```text
输入：PRD（本地文件 / URL / 飞书等来源）
处理：条件触发的并行评审
输出：结构化评审结果（JSON + Markdown）
```

主线到这里结束。

### 1.2 后半段能力降级为扩展层

以下能力不应再放在 README、架构图、主流程图的第一层：

- `delivery_bundle.json`
- `approve_handoff`
- `handoff_to_executor`
- `execution_tasks.json`
- `traceability_map.json`
- approval records / notification / retry / dashboard

这些能力可以：

- 保留在代码库中
- 保留在扩展文档中
- 保留在后续路线图中
- 保留为实验功能或 future extensions

但不再作为“系统是什么”的第一定义。

### 1.3 这样做的原因

- 当前项目最清晰、最稳定、最有差异化的能力仍然是 PRD review engine
- 后半段 orchestration 虽然已经有实现，但会让系统边界迅速膨胀
- 如果主架构同时讲 review 和 orchestration，定位会摇摆
- `approval-loop-design` 的边界本身就更适合作为主线

---

## 二、适用前提

当前仓库已经具备这些基础，不应重复开发：

- `gating` 与 `parallel_review` 基础骨架
- `normalizer`
- 四个 reviewer agent
- aggregator 与 conflict 基础逻辑
- MCP review 入口
- approval / handoff / execution / traceability 的扩展实现

因此，这份文档的重点不是“从零搭建 Window A”，而是做两件事：

1. 把项目主叙事收敛成 review engine
2. 把现有评审链路补到更接近 `approval-loop-design` 的产品边界和输出质量

---

## 三、推荐推进顺序

推荐按下面顺序推进：

```text
Phase P0  主架构收缩与文档重构
    ->
Phase P1  对齐 review 输出 schema
    ->
Phase P2  reviewer timeout / fallback / partial_review
    ->
Phase P3  语义冲突检测增强
    ->
Phase P4  review_requirement MCP facade
    ->
Phase P5  connector 真实可用化
    ->
Phase P6  A/B 对比评估与 README 收敛
```

原则：

- 先统一定位，再补 contract，再补鲁棒性
- 不删除现有 `approve_handoff`、`handoff_to_executor` 等代码
- 先让这些能力退出“主架构叙事”，再决定后续是否保留为扩展层
- 每一步都必须有测试、eval 或文档产出

### 3.1 全局执行约束

以下约束适用于本文档中的所有 phase 和 step：

- 每个 phase 都必须从 `main` 拉出独立子分支后再开始开发，推荐命名为 `phase/pX-<topic>`。
- 每个 step 完成后都必须立即提交一次，提交只包含该 step 的变更。
- 每个 phase 的最后一步都必须包含：
  - 用 `D:\venvs\marrdp` 中的 Python 跑完整测试
  - 合并回主分支
  - 推送到远端
- 所有测试都必须在 `D:\venvs\marrdp` 虚拟环境内运行，不允许使用系统 Python 或仓库内其他虚拟环境。

推荐 phase 开场命令格式：

```powershell
git checkout main
git switch -c <phase-branch>
```

推荐测试命令格式：

```powershell
& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q
```

推荐 phase 收尾命令格式：

```powershell
& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q
git checkout main
git merge --no-ff <phase-branch>
git push origin main
```

如果当前 step 只运行局部测试，step 提交前允许只跑局部测试；但 phase 结束时必须再跑一次完整测试并完成合并、推送。
### 3.2 每个 Phase 提示词的固定收尾段

在执行本文档中的任一 phase 时，必须把下面这段原样附加到该 phase 的提示词末尾，不得省略：

```text
Phase 收尾要求：
1. 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
2. 本 phase 在独立 phase 分支上开发，phase 完成时必须执行：
   - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
   - `git checkout main`
   - `git merge --no-ff <phase-branch>`
   - `git push origin main`
3. 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 四、Phase P0：主架构收缩与文档重构

> 目标：把项目主架构正式收缩到 review result，后半段改为扩展层，不再作为默认主线。

### 预期结果

- README 的主流程只写到 review result
- 架构图和系统定位只覆盖 review engine
- `bundle / approval / handoff / execution` 改到扩展层说明
- MCP/API 文档区分：
  - review-only mainline
  - orchestration extensions

### 给 Codex 的提示词

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。

任务：
0. 如果这是首次开始 Phase P0，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p0-review-engine-positioning`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p0-review-engine-positioning`

1. 先阅读并理解当前文档与入口：
   - `README.md`
   - `docs/handoff-plan.md`
   - `docs/codex-prompts-phased-development.md`
   - `requirement_review_v1/mcp_server/server.py`
   - 如有系统定位文档，也一起阅读

2. 目标不是删除 bundle/approval/handoff/execution 代码，而是把项目主架构收缩到 review result。

3. 具体要求：
   - 重写 `README.md` 的 system position、core capabilities、usage、output、flow 描述
   - 让主流程收敛成：
     - source input
     - review mode gating
     - normalizer
     - parallel reviewers
     - aggregator
     - review artifacts
   - 将以下能力移到扩展层或 future extensions：
     - delivery bundle
     - approval loop
     - handoff
     - execution orchestration
     - traceability
     - notifications
   - 在 README 中明确说明：
     - 这些扩展能力仍在仓库中保留
     - 但不属于当前主架构的第一层定义
   - 调整 `docs/handoff-plan.md` 或相关文档，使其显式成为 extension 文档，而不是主流程文档
   - 如果需要，可新增一份 `docs/review-engine-positioning.md`

4. MCP/API 文档要求：
   - 主工具优先强调 review-only 能力
   - orchestration 相关 tools 单独放在扩展章节

5. 不允许做的事：
   - 不删除现有代码
   - 不删除现有测试
   - 不把扩展能力说成已废弃，除非代码确实移除

6. 输出结果时说明：
   - 新的主架构定义
   - 扩展层定义
   - 哪些文档已被重写或新增

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p0-review-engine-positioning` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p0-review-engine-positioning`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 五、Phase P1：对齐 review 输出 schema

> 目标：把当前并行评审产出从“内部聚合结构”升级成更稳定、适合下游 agent 消费的 review contract。

### 预期结果

- 聚合结果包含更明确字段：
  - `finding_id`
  - `source_reviewer`
  - `severity`
  - `category`
  - `description`
  - `suggested_action`
  - `assignee`
- 输出包含显式 `meta.review_mode`
- 输出文件形态更贴近：
  - `review_result.json`
  - `review_report.md`

### 给 Codex 的提示词

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。

任务：
0. 如果这是首次开始 Phase P1，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p1-review-output-schema`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p1-review-output-schema`

1. 先阅读并理解当前实现：
   - `requirement_review_v1/review/aggregator.py`
   - `requirement_review_v1/review/reviewer_agents/base.py`
   - `requirement_review_v1/workflow.py`
   - `requirement_review_v1/service/review_service.py`

2. 在不破坏现有 review 主链路的前提下，升级并行评审输出 schema，使其更接近 approval-loop-design 文档中的 `review_result.json`。

3. 具体要求：
   - 为聚合 finding 生成稳定 `finding_id`
   - 为每条 finding 保留 `source_reviewer`
   - 在 reviewer 输出或 aggregator 层补齐：
     - `suggested_action`
     - `assignee`
   - 在聚合结果中新增：
     - `meta.review_mode`
     - `meta.reviewers_completed`
     - `meta.reviewers_failed`
   - 新增或调整产物：
     - `review_result.json`
     - `review_report.md`
   - 旧的评审产物如仍需保留，需向后兼容并说明关系

4. 更新测试，至少覆盖：
   - `tests/test_review_aggregator.py`
   - `tests/test_review_service_handoff.py`
   - 如有必要新增 `tests/test_parallel_review_contract.py`

5. 运行：
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_aggregator.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_service_handoff.py -q`
   - `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`

6. 完成后说明：
   - 新旧 schema 差异
   - 向后兼容策略

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p1-review-output-schema` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p1-review-output-schema`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 六、Phase P2：reviewer 超时、降级与 partial_review

> 目标：避免某一个 reviewer 超时或失败时整轮并行评审直接失败。

### 预期结果

- 每个 reviewer 有独立 timeout
- 单 reviewer 失败时返回受控 partial result
- 聚合结果显式标记：
  - `partial_review`
  - `reviewers_failed`
- 高风险场景下报告注明需要人工补审

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次开始 Phase P2，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p2-partial-review-resilience`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p2-partial-review-resilience`

1. 阅读以下文件：
   - `requirement_review_v1/review/parallel_review_manager.py`
   - `requirement_review_v1/review/aggregator.py`
   - `requirement_review_v1/workflow.py`

2. 为并行 reviewer 增加 timeout/fallback 机制。

3. 要求：
   - 不改变四个 reviewer 的职责划分
   - 在 `parallel_review_manager.py` 中为每个 reviewer 增加单独 timeout 控制
   - 某 reviewer 超时或报错时：
     - 不中断整个 parallel review
     - 记录失败 reviewer 名称与失败原因
     - 返回空 findings/open_questions/risk_items 的 partial result
   - 聚合结果中增加：
     - `partial_review: bool`
     - `reviewers_completed`
     - `reviewers_failed`
   - `workflow.py` 中将 partial_review 相关信息写入 trace / report metadata
   - 若存在高风险且 reviewer 缺失，在摘要或报告中显式提示“需人工补审”

4. 更新测试：
   - 新增 `tests/test_parallel_review_manager.py`
   - 更新 `tests/test_review_aggregator.py`
   - 必要时更新 `tests/test_review_service_handoff.py`

5. 运行 `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`

6. 最后总结：
   - timeout 默认值
   - partial_review 的对外 contract

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p2-partial-review-resilience` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p2-partial-review-resilience`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 七、Phase P3：语义冲突检测增强

> 目标：把当前的 conflict 检测从“严重级别不一致”提升到“跨角色观点冲突”。

### 预期结果

- 能识别更贴近业务的冲突，例如：
  - Product 认为在 scope 内，Engineering 认为依赖未确认
  - QA 认为验收缺失，Product 认为描述已足够
  - Security 认为必须人工阻断，Engineering 认为可后补
- conflict 带有：
  - `conflict_id`
  - `type`
  - `description`
  - `requires_manual_resolution`

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次开始 Phase P3，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p3-semantic-conflict-detection`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p3-semantic-conflict-detection`

1. 阅读：
   - `requirement_review_v1/review/aggregator.py`
   - `requirement_review_v1/review/reviewer_agents/*.py`

2. 增强 aggregator 的 conflict 检测能力，使其不再只基于 severity mismatch，而是增加面向 reviewer 语义的冲突标记。

3. 实现要求：
   - 保留现有 severity mismatch 逻辑，但不要作为唯一冲突来源
   - 引入最小可维护规则：
     - scope_inclusion vs dependency_blocker
     - acceptance_complete vs testability_gap
     - release_ok vs approval_blocker
   - 输出 conflict schema 至少包含：
     - `conflict_id`
     - `type`
     - `description`
     - `reviewers`
     - `requires_manual_resolution`
   - 冲突描述必须可读，适合直接显示在 Markdown 报告中

4. 更新测试：
   - `tests/test_review_aggregator.py`
   - 至少增加 3 个 conflict case

5. 运行 `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest tests/test_review_aggregator.py -q`

6. 说明：
   - 当前采用的语义冲突规则集
   - 哪些判断仍属于启发式，而不是严格语义理解

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p3-semantic-conflict-detection` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p3-semantic-conflict-detection`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 八、Phase P4：增加 review_requirement MCP facade

> 目标：在保留现有 MCP 多工具能力的同时，提供一个更贴近外部设计文档的“单工具评审入口”。

### 预期结果

- 新增 `review_requirement`
- 它是 `review_prd` 的 facade，不重复实现底层逻辑
- 返回内容更接近 review engine 产品 contract，而不是整个大工作流 contract

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次开始 Phase P4，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p4-review-requirement-facade`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p4-review-requirement-facade`

1. 阅读：
   - `requirement_review_v1/mcp_server/server.py`
   - `requirement_review_v1/service/review_service.py`

2. 在不删除现有 MCP tools 的前提下，新增一个 facade tool：
   - `review_requirement`

3. 要求：
   - 支持输入：
     - `source`
     - `prd_text`
     - `prd_path`
     - `metadata` 或 `options`
   - 内部复用现有 review service
   - 输出尽量对齐 approval-loop-design：
     - `review_id` 或 `run_id`
     - `findings`
     - `open_questions`
     - `risk_items`
     - `conflicts`
     - `report_path`
     - `review_mode`
   - 不把 bundle、approval、handoff、execution 的字段混进该工具默认返回
   - 需要在文档或代码注释中说明：
     - `review_requirement` 是 review-only facade
     - `review_prd` 仍保留更完整的工作流输出，但不再是项目主定位的唯一表达

4. 更新测试：
   - `tests/test_mcp_tools.py`
   - 必要时新增 `tests/test_mcp_review_requirement.py`

5. 运行 `& 'D:\venvs\marrdp\Scripts\python.exe' -m pytest -q`

6. 最后输出：
   - `review_requirement` 与 `review_prd` 的职责边界

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p4-review-requirement-facade` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p4-review-requirement-facade`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 九、Phase P5：connector 真实可用化

> 目标：让外部设计文档中的 source connector 不再停留在“识别 source 但不可读取”。

### 现状

当前仓库中：

- `LocalFileConnector` 可用
- `URLConnector` 仍是占位
- `FeishuConnector` 仍是占位

因此这一阶段分两步走，先把 URL 读取做成可选能力，再决定是否接飞书。

### Step P5-1：URLConnector 可选抓取

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次开始 Phase P5，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p5-connectors-hardening`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p5-connectors-hardening`

1. 阅读：
   - `requirement_review_v1/connectors/url.py`
   - `requirement_review_v1/connectors/registry.py`
   - `requirement_review_v1/service/review_service.py`

2. 将 `URLConnector` 从纯占位升级为“受控可用”版本。

3. 要求：
   - 优先保证安全和可测试性
   - 只支持抓取公开 http/https 文本页面
   - 若内容类型不是文本或 markdown/html，返回受控错误
   - 若网络不可用，要返回明确错误，不得静默降级为空内容
   - 将抓取结果标准化为 `SourceDocument`
   - 不引入复杂外部依赖，优先使用轻量实现

4. 更新测试：
   - `tests/test_source_connectors.py`
   - 如有必要新增 `tests/test_url_connector.py`

5. 如果受限于测试环境网络，至少补 mock 测试并说明未做真实联网回归。

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p5-connectors-hardening` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p5-connectors-hardening`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

### Step P5-2：FeishuConnector 决策实现

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次进入 Phase P5，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p5-connectors-hardening`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p5-connectors-hardening`

1. 评估 `FeishuConnector` 是应该：
   - 继续保持 stub
   - 还是升级为最小可用版本

2. 如果实现最小可用版本，要求：
   - 通过环境变量读取配置
   - 受控处理认证失败、权限失败、文档不存在
   - 输出统一 `SourceDocument`
   - 不让飞书能力影响本地文件主链路

3. 若当前仓库和运行环境不适合落地真实飞书集成，则不要硬实现。
   改为：
   - 完善错误信息
   - 完善 metadata
   - 明确 README 中的可选集成边界

4. 更新测试并说明最终决策。

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p5-connectors-hardening` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p5-connectors-hardening`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 十、Phase P6：A/B 评估与 README 收敛

> 目标：证明并行评审增强是有价值的，而不是只新增代码路径，同时让 README 与主架构收缩后的定位一致。

### 预期结果

- 能对比 single review 与 parallel review
- 至少对比：
  - findings 数量
  - open questions 数量
  - risk items 数量
  - conflicts 数量
  - latency
- README 或 docs 明确说明：
  - review-only 能力边界
  - 扩展 orchestration 能力边界

### 给 Codex 的提示词

```text
你正在当前仓库中工作。

任务：
0. 如果这是首次开始 Phase P6，先创建并切换到 phase 分支：
   - `git checkout main`
   - `git switch -c phase/p6-ab-eval-and-readme`
   如果该分支已经存在且你是在继续这个 phase，则改用：
   - `git switch phase/p6-ab-eval-and-readme`

1. 阅读：
   - `eval/`
   - `docs/`
   - `README.md`

2. 为并行评审增强增加最小 A/B 对比验证。

3. 要求：
   - 在 `eval/` 下新增一个 comparison 脚本
   - 对至少 2 份不同复杂度 PRD，比较：
     - `single_review`
     - `parallel_review`
   - 输出指标：
     - findings count
     - open questions count
     - risk items count
     - conflicts count
     - duration_ms
   - 若无法稳定统计 token，可明确写为 `not available`

4. 更新 README 或新增 docs 文档，明确：
   - 项目主架构到 review result 为止
   - `review_requirement` 面向 review engine 使用场景
   - `review_prd` 可继续保留，但不应继续作为唯一主流程叙事
   - bundle / approval / handoff / execution 属于扩展层，而不是主架构第一层

5. 如可行，补最小自动化测试；若 eval 只能人工运行，也要给出运行命令。

7. Phase 收尾要求：
   - 当前 phase 内的每个 step 完成后都要立即 commit，一次 commit 只对应一个 step。
   - 本 phase 在 `phase/p6-ab-eval-and-readme` 分支上开发，phase 完成时必须执行：
     - `& ''D:\venvs\marrdp\Scripts\python.exe'' -m pytest -q`
     - `git checkout main`
     - `git merge --no-ff phase/p6-ab-eval-and-readme`
     - `git push origin main`
   - 只有完整测试通过、分支已合并、远端已推送，这个 phase 才算结束。
```

---

## 十一、扩展层的保留方式

如果当前决定把后半段退出主架构，建议按下面方式保留，而不是删除：

### 11.1 代码层

保留目录与实现：

- `packs/`
- `execution/`
- `workspace/`
- `notifications/`
- `monitoring/`
- 对应 MCP tools

### 11.2 文档层

改成以下类型的文档：

- `extension docs`
- `future workflow docs`
- `experimental orchestration docs`

例如：

- `docs/handoff-plan.md`
- approval / execution / traceability 说明

### 11.3 README 层

主流程不再展示这些能力，只在扩展章节简单说明：

- 仓库中保留了交付编排相关原型
- 可作为 review result 之后的扩展层使用
- 当前不作为项目主架构默认定义

---

## 十二、建议的实际执行顺序

如果目标是尽快把这份设计落进当前仓库，建议按下面顺序给 Codex 下任务：

1. `Phase P0`
2. `Phase P1`
3. `Phase P2`
4. `Phase P4`
5. `Phase P3`
6. `Phase P6`
7. `Phase P5`

原因：

- `P0` 决定整个项目要如何被定义
- `P1` 和 `P2` 决定 review contract 是否稳定
- `P4` 能快速把能力产品化
- `P3` 提升质量，但不阻塞主链路
- `P6` 决定这条路线是否有展示价值
- `P5` 依赖运行环境，最容易被外部条件卡住

---

## 十三、哪些不要做

这份设计接入当前项目时，不建议做以下事情：

- 不要删除 `approve_handoff`
- 不要删除 `handoff_to_executor`
- 不要删除 execution / traceability 相关代码
- 不要把整个 MCP server 收缩成只剩一个 tool
- 不要为了对齐外部文档而直接移除现有扩展实现
- 不要在没有 eval 的情况下宣称 parallel review 明显优于 single review

---

## 十四、最终定位

如果按本文档推进，当前项目会形成两层能力：

### 1. Mainline Review Engine

- 入口：`review_requirement` 或 review-only API
- 聚焦：PRD 评审
- 输出：结构化 findings / risks / open questions / conflicts / report
- 这是项目的主架构与对外默认定位

### 2. Extension Workflow Layer

- 入口：`review_prd` 后继续进入 bundle / approval / handoff / execution
- 聚焦：从评审结果走向交付准备与执行编排
- 输出：bundle、approval records、execution tasks、traceability
- 这部分继续保留在仓库中，但不作为主架构第一层定义

这种分层，比继续把“评审 -> bundle -> 审批 -> handoff -> execution”整体放在主架构里更清晰，也更符合 `approval-loop-design` 的设计边界。






