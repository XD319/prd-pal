# Codex 分阶段开发提示词（基于 v2.1 Window A 计划的剩余功能）

基于 `D:\download\Development-Plan-v2.1-windowA.md` 与当前仓库代码现状，对“已完成能力”和“未完成能力”重新对齐。本文档只保留 **尚未完成** 的功能，并将其拆成可直接交给 Codex 执行的分阶段提示词，避免重复开发已经落地的 v5 / v6 能力。

---

## 一、现状结论

### 已完成能力

当前仓库中，以下能力已经有代码与测试支撑，不建议再按旧提示词重复开发：

- v5 交付物标准化：
  - `DeliveryBundle`
  - `ArtifactSplitter`
  - 最小审批状态机
  - `generate_delivery_bundle`
  - `approve_handoff`
- v6 执行编排：
  - `ExecutionTask` / `ExecutionMode` / `ExecutionTaskStatus`
  - `ExecutorRouter`
  - `task_lifecycle`
  - `TraceabilityMap`
  - `handoff_to_executor`
  - `get_execution_status`
  - `get_traceability`
- 文档版本号已经到 `6.0.0`

### 仍未完成的功能

按照 `Development-Plan-v2.1-windowA.md` 对照当前仓库，主要缺口集中在以下 7 类：

1. Source Connector 抽象层未落地  
   当前入口仍主要是 `prd_text / prd_path`，还没有 `FeishuConnector / LocalFileConnector / URLConnector` 的统一接口与 source metadata。

2. Review Workspace / 审批快照未落地  
   已有最小 `DeliveryBundle` 审批状态，但没有独立的 `approval_records.json`、`status_snapshot.json`、workspace 状态读写层。

3. 真实 Adapter 层未落地  
   目前只有 handoff pack / prompt / execution task 的编排，没有 `BaseAdapter / CodexAdapter / ClaudeCodeAdapter` 的统一抽象，也没有真实执行日志回写协议。

4. 异步执行回流机制未落地  
   当前 `handoff_to_executor` 是路由与落盘，不包含 callback / polling 状态推进、执行结果写回、checkpoint 更新。

5. 平台化增强未落地  
   包括通知集成、Prompt / 模板版本化、监控与审计归档、失败重试策略。

6. 工具链扩展预留未落地  
   尚未抽出 Confluence / Notion / Jira connector 接口与 Generic Markdown Adapter。

7. Window A 并行 Reviewer 增强未落地  
   文档里定义的 gating / normalizer / parallel reviewers / aggregator 当前仓库还没有对应模块。

---

## 二、推荐开发顺序

按风险与收益排序，建议从这里开始：

```text
Phase D  Source Connector 统一接入
    ↓
Phase E  Review Workspace + 审批快照
    ↓
Phase F  Adapter 层 + 异步执行回流
    ↓
Phase G  平台化增强（通知 / 版本化 / 监控）
    ↓
Phase H  工具链扩展预留
    ↓
Phase I  Window A 并行 Reviewer
```

原则：

- 先补主链路缺口，再做增强项
- Window A 最后做，避免打断当前稳定主线
- 每一步都要求补测试，不接受“只有文档没有代码”

---

## 三、Phase D：Source Connector 统一接入

> 目标：把当前 `prd_text / prd_path` 输入升级为标准化 Source Connector 层，并统一产出 source metadata。

### Step D-1：定义 Connector 抽象与统一 schema

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。
从当前 main 创建新分支：`git checkout -b feature/v7-source-connectors`

任务：
1. 在 `requirement_review_v1/connectors/` 下创建：
   - `__init__.py`
   - `base.py`
   - `schemas.py`

2. 设计统一输入抽象：
   - `SourceType`：`local_file / url / feishu`
   - `SourceMetadata`
   - `SourceDocument`
   - `BaseConnector`

3. 要求：
   - 使用 Pydantic v2，继承项目已有 `AgentSchemaModel`
   - `SourceDocument` 至少包含：
     - `source_type`
     - `source`
     - `title`
     - `content_markdown`
     - `metadata`
     - `fetched_at`
   - `BaseConnector` 定义：
     - `can_handle(source: str) -> bool`
     - `get_content(source: str) -> SourceDocument`

4. 在 `tests/` 新增 `test_source_connector_schema.py`，验证：
   - schema 可实例化
   - metadata 默认值正确
   - connector 抽象接口可被最小子类实现

5. 运行：
   - `python -m pytest tests/test_source_connector_schema.py -v`
   - `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v7): define source connector base abstractions and schemas"`
```

### Step D-2：实现 LocalFileConnector 与 URLConnector

```text
你正在 `feature/v7-source-connectors` 分支上工作。

任务：
1. 在 `requirement_review_v1/connectors/` 下创建：
   - `local_file.py`
   - `url.py`
   - `registry.py`

2. 实现：
   - `LocalFileConnector`
   - `URLConnector`
   - `ConnectorRegistry`

3. 具体要求：
   - `LocalFileConnector` 支持读取 `.md` / `.txt`
   - 输出统一 `SourceDocument`
   - `URLConnector` 先只做接口与安全占位实现：
     - 当前版本不实际联网抓取
     - 对 http/https URL 做格式校验
     - 返回明确的 `NotImplementedError` 或受控错误，保留后续扩展点
   - `ConnectorRegistry.resolve(source)` 能根据入参返回合适 connector

4. 新增 `tests/test_source_connectors.py`，覆盖：
   - 本地 Markdown 文件读取
   - txt 文件读取
   - 不支持后缀报错
   - URL 路由正确
   - 未实现 URL 抓取时返回预期错误

5. 运行：
   - `python -m pytest tests/test_source_connectors.py -v`
   - `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v7): add local-file and url connector implementations with registry"`
```

### Step D-3：把 review_service / FastAPI / MCP 接入 Connector 层

```text
你正在 `feature/v7-source-connectors` 分支上工作。

任务：
1. 修改以下文件：
   - `requirement_review_v1/service/review_service.py`
   - `requirement_review_v1/server/app.py`
   - `requirement_review_v1/mcp_server/server.py`

2. 改造目标：
   - 保持现有 `prd_text / prd_path` 向后兼容
   - 新增统一入口 `source`
   - 当提供 `source` 时，优先走 `ConnectorRegistry`
   - 将 `SourceDocument.metadata` 写入：
     - `report.json`
     - `run_trace.json`
     - `delivery_bundle.json.metadata`

3. 新增一个受控的 `FeishuConnector` 占位类：
   - 文件：`requirement_review_v1/connectors/feishu.py`
   - 仅做 token/url 识别与错误提示
   - 不做真实飞书 API 调用

4. 更新测试：
   - `tests/test_mcp_tools.py`
   - `tests/test_review_service_handoff.py`
   - 必要时新增 `tests/test_server_app_source_input.py`
   验证：
   - `prd_path` 旧路径仍可用
   - `source=本地路径` 能正常评审
   - source metadata 被写入产物
   - `feishu://` 输入会返回明确的“暂未实现”错误，而不是静默失败

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v7): integrate source connectors into review service, FastAPI, and MCP entrypoints"`
```

---

## 四、Phase E：Review Workspace 与审批快照

> 目标：让审批不再只是一条 bundle 状态，而是有可持久化的记录与状态快照。

### Step E-1：建立 Review Workspace 状态模型

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v8-review-workspace`

任务：
1. 在 `requirement_review_v1/workspace/` 下创建：
   - `__init__.py`
   - `models.py`
   - `repository.py`

2. 定义：
   - `WorkspaceStatus`：`confirmed / need_more_info / deferred / out_of_scope / blocked_by_risk`
   - `ReviewWorkspaceRecord`
   - `ApprovalRecord`
   - `StatusSnapshot`

3. 持久化文件目标：
   - `approval_records.json`
   - `status_snapshot.json`

4. `repository.py` 负责：
   - 从 `run_dir` 加载/保存上述文件
   - 对 bundle 状态与 workspace 状态做最小映射

5. 新增 `tests/test_workspace_repository.py`，验证：
   - 初始化空仓库
   - 保存后可重新加载
   - 状态枚举序列化正确

6. 运行：
   - `python -m pytest tests/test_workspace_repository.py -v`
   - `python -m pytest -q`

7. 提交：
   `git commit -am "feat(v8): add review workspace models and file-based repository"`
```

### Step E-2：审批操作回写 approval_records 与 status_snapshot

```text
你正在 `feature/v8-review-workspace` 分支上工作。

任务：
1. 修改：
   - `requirement_review_v1/service/review_service.py`
   - `requirement_review_v1/packs/approval.py`

2. 目标：
   - 每次 `approve_handoff` / `need_more_info` / `block_by_risk` / `reset_to_draft`
     除了更新 `delivery_bundle.json` 之外，还要同步：
     - 写入 `approval_records.json`
     - 更新 `status_snapshot.json`
   - `status_snapshot.json` 至少包含：
     - `run_id`
     - `bundle_id`
     - `bundle_status`
     - `workspace_status`
     - `updated_at`

3. 更新 `requirement_review_v1/mcp_server/server.py`：
   - 为审批接口返回新增的记录路径

4. 更新测试：
   - `tests/test_approval.py`
   - `tests/test_mcp_tools.py`
   验证：
   - 审批动作会生成两个新文件
   - 记录内容和状态转换一致
   - 非法状态转换不应污染快照

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v8): persist approval records and workspace status snapshots during handoff approval"`
```

### Step E-3：补充查询接口

```text
你正在 `feature/v8-review-workspace` 分支上工作。

任务：
1. 在 `requirement_review_v1/mcp_server/server.py` 中新增 MCP tool：

   `get_review_workspace(run_id: str | None = None, bundle_id: str | None = None, options: dict[str, Any] | None = None) -> dict[str, Any]`

2. 功能要求：
   - 支持按 `run_id` 或 `bundle_id` 查询
   - 返回：
     - bundle 基本信息
     - approval_history
     - approval_records
     - status_snapshot

3. 在 `requirement_review_v1/service/` 中补充对应 service 函数

4. 更新 `tests/test_mcp_tools.py` 覆盖：
   - 正常查询
   - run_id / bundle_id 查找
   - 文件缺失时的受控错误

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v8): add MCP query for review workspace, approval records, and status snapshots"`
```

---

## 五、Phase F：Adapter 层与异步执行回流

> 目标：补齐“可交付给执行方”与“执行结果可回流”的真实工程接口，而不是只停留在静态 handoff 文件。

### Step F-1：实现 Adapter 抽象层

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v9-adapters-and-callbacks`

任务：
1. 在 `requirement_review_v1/adapters/` 下创建：
   - `__init__.py`
   - `base.py`
   - `codex.py`
   - `claude_code.py`

2. 设计要求：
   - `BaseAdapter` 定义：
     - `build_pack(handoff_bundle: dict) -> dict`
     - `build_prompt(pack_dir: str) -> str`
     - `create_execution_request(task: ExecutionTask, bundle: DeliveryBundle) -> dict`
   - 不做真实外部命令执行
   - 当前版本只生成 adapter-specific request payload 与执行上下文文件

3. 产物要求：
   - `codex_request.json`
   - `claude_code_request.json`
   - `execution_context.md`

4. 新增 `tests/test_adapters.py`，验证：
   - BaseAdapter 子类行为
   - request payload 字段
   - prompt / context 生成功能

5. 运行：
   - `python -m pytest tests/test_adapters.py -v`
   - `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v9): add adapter abstraction and codex/claude-code request builders"`
```

### Step F-2：把 handoff_to_executor 升级为生成 adapter request

```text
你正在 `feature/v9-adapters-and-callbacks` 分支上工作。

任务：
1. 修改：
   - `requirement_review_v1/service/execution_service.py`
   - `requirement_review_v1/execution/router.py`

2. 目标：
   - 在 `handoff_to_executor` 路由完 `ExecutionTask` 后
   - 根据 `executor_type` 调用对应 adapter
   - 为每个 task 落盘：
     - adapter request 文件
     - execution context 文件
   - 把这些路径写入 `execution_tasks.json`

3. 向后兼容：
   - 没有 adapter 的 executor_type 要返回明确错误
   - 不能破坏现有 `traceability_map.json` 与 task 持久化格式

4. 更新测试：
   - `tests/test_executor_router.py`
   - `tests/test_mcp_tools.py`
   - 如有必要新增 `tests/test_execution_service_adapter_requests.py`

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v9): generate adapter-specific execution requests during executor handoff"`
```

### Step F-3：实现 execution callback / polling 状态推进

```text
你正在 `feature/v9-adapters-and-callbacks` 分支上工作。

任务：
1. 在 `requirement_review_v1/service/execution_service.py` 中新增：
   - `update_execution_task_for_mcp(...)`
   - `append_execution_event(...)`
   - 对 task lifecycle 的持久化包装

2. 在 `requirement_review_v1/mcp_server/server.py` 中新增 MCP tool：
   - `update_execution_task`
   - `list_execution_tasks`

3. 目标能力：
   - 支持外部执行方通过 polling / callback 风格回写：
     - `assigned`
     - `in_progress`
     - `waiting_review`
     - `completed`
     - `failed`
     - `cancelled`
   - 可附带：
     - `result_summary`
     - `checkpoint detail`
     - `artifact_paths`

4. 每次更新都要：
   - 持久化 `execution_tasks.json`
   - 更新 `status_snapshot.json`
   - 在 `run_trace.json` 追加 execution update trace

5. 更新测试：
   - `tests/test_task_lifecycle.py`
   - `tests/test_mcp_tools.py`
   - 必要时新增 `tests/test_execution_updates.py`

6. 运行 `python -m pytest -q`

7. 提交：
   `git commit -am "feat(v9): add execution task update APIs for polling and callback-style result writeback"`
```

---

## 六、Phase G：平台化增强

> 目标：补齐通知、模板版本化、监控审计这几个企业化缺口。

### Step G-1：Prompt / 模板版本化

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v10-platform-governance`

任务：
1. 在 `requirement_review_v1/templates/` 下创建：
   - `__init__.py`
   - `registry.py`
   - `models.py`

2. 抽象以下模板版本：
   - review prompt
   - delivery artifact template
   - adapter prompt

3. 要求：
   - 每个模板有 `template_id`、`template_type`、`version`、`description`
   - 现有 hard-coded 模板先迁入 registry
   - `run_trace.json` 中显式记录模板版本

4. 更新测试：
   - `tests/test_handoff_renderer.py`
   - `tests/test_prompt_generation_trace.py`
   - 必要时新增 `tests/test_template_registry.py`

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v10): add template registry and explicit prompt version tracking"`
```

### Step G-2：监控、审计与失败重试元数据

```text
你正在 `feature/v10-platform-governance` 分支上工作。

任务：
1. 在 `requirement_review_v1/monitoring/` 下创建：
   - `__init__.py`
   - `audit.py`
   - `retry.py`

2. 目标：
   - 统一记录关键操作审计事件：
     - review
     - bundle generation
     - approval
     - handoff
     - execution update
   - 审计落盘文件：
     - `audit_log.jsonl`
   - 为非阻断步骤增加 retry metadata 结构，但先不做复杂调度器

3. 集成点：
   - `review_service.py`
   - `execution_service.py`
   - `mcp_server/server.py`

4. 更新测试：
   - 新增 `tests/test_audit_logging.py`
   - 新增 `tests/test_retry_metadata.py`

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v10): add audit logging and retry metadata for workflow governance"`
```

### Step G-3：通知接口预留

```text
你正在 `feature/v10-platform-governance` 分支上工作。

任务：
1. 在 `requirement_review_v1/notifications/` 下创建：
   - `__init__.py`
   - `base.py`
   - `feishu.py`
   - `wecom.py`

2. 目标：
   - 先实现 notifier 抽象层与 dry-run payload 生成
   - 不做真实网络发送
   - 支持以下通知类型：
     - approval requested
     - blocked by risk
     - executor handoff created
     - execution completed / failed

3. 集成：
   - 在 `approve_handoff`、`handoff_to_executor`、`update_execution_task` 中生成通知 payload
   - 默认只落盘到 `notifications.jsonl`

4. 更新测试：
   - 新增 `tests/test_notifications.py`
   - 更新 `tests/test_mcp_tools.py` 验证关键动作会留下通知记录

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v10): add notifier abstraction and dry-run notification records for approval and execution events"`
```

---

## 七、Phase H：工具链扩展预留

> 目标：补上文档计划里的扩展接口，但先只做可扩展结构，不接真实外部服务。

### Step H-1：补充企业工具 connector stub

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v11-integration-stubs`

任务：
1. 在 `requirement_review_v1/connectors/` 下新增：
   - `confluence.py`
   - `notion.py`
   - `jira.py`
   - `markdown_adapter.py`

2. 要求：
   - 这些 connector 先实现：
     - source 识别
     - 输入校验
     - 错误提示
     - registry 注册
   - 不做真实 API 调用

3. `GenericMarkdownAdapter` 要支持：
   - 输入原始文本
   - 输出标准 `SourceDocument`

4. 更新测试：
   - 新增 `tests/test_connector_stubs.py`
   - 验证 registry 可以识别这些来源

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v11): add confluence/notion/jira connector stubs and generic markdown adapter"`
```

---

## 八、Phase I：Window A 并行 Reviewer

> 目标：按 `Development-Plan-v2.1-windowA.md` 的 11.5 节，把复杂需求评审升级成“条件触发的并行 Reviewer 窗口”。

### Step I-1：实现 Gating 与 Requirement Normalizer

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v12-window-a-parallel-review`

任务：
1. 在 `requirement_review_v1/review/` 下创建：
   - `__init__.py`
   - `gating.py`
   - `normalizer.py`

2. `gating.py` 负责：
   - 根据长度、模块数、角色数、风险关键词、跨系统迹象
   - 判断 `single_review` 还是 `parallel_review`

3. `normalizer.py` 负责：
   - 从 PRD 提取：
     - 摘要
     - 场景列表
     - 验收标准
     - dependency hints
     - risk hints
   - 为不同 reviewer 生成裁剪后的输入

4. 数据结构要求：
   - `WindowAConfig`
   - `ReviewModeDecision`
   - `NormalizedRequirement`

5. 新增 `tests/test_window_a_gating.py`，覆盖：
   - 低复杂度样例走单路评审
   - 高复杂度样例命中 `parallel_review`
   - 风险关键词阈值逻辑

6. 运行 `python -m pytest tests/test_window_a_gating.py -v`

7. 提交：
   `git commit -am "feat(v12): add Window A gating and requirement normalizer"`
```

### Step I-2：实现多角色 Reviewer Agent 与 Aggregator

```text
你正在 `feature/v12-window-a-parallel-review` 分支上工作。

任务：
1. 创建目录：
   - `requirement_review_v1/review/reviewer_agents/`
   - `requirement_review_v1/review/aggregator.py`
   - `requirement_review_v1/review/parallel_review_manager.py`

2. 先实现 4 个 reviewer：
   - `product_reviewer.py`
   - `engineering_reviewer.py`
   - `qa_reviewer.py`
   - `security_reviewer.py`

3. 当前版本不强依赖真实并发框架，允许先用 `asyncio.gather` 并发调度。

4. 每个 reviewer 输出固定 schema：
   - findings
   - open_questions 或风险字段
   - 限制 Top N，避免长文本失控

5. `aggregator.py` 负责：
   - 去重
   - 风险归一化
   - 冲突标记
   - 输出统一：
     - `review_report.json`
     - `risk_items.json`
     - `open_questions.json`
     - `review_summary.md`

6. 新增测试：
   - `tests/test_parallel_review_manager.py`
   - `tests/test_review_aggregator.py`

7. 运行 `python -m pytest -q`

8. 提交：
   `git commit -am "feat(v12): add parallel reviewer agents and unified aggregation for Window A"`
```

### Step I-3：接入主评审流程并完成 A/B 对比验证

```text
你正在 `feature/v12-window-a-parallel-review` 分支上工作。

任务：
1. 修改：
   - `requirement_review_v1/workflow.py`
   - `requirement_review_v1/service/review_service.py`
   - 必要时修改相关 agent 调度代码

2. 集成目标：
   - 默认仍走原有单路评审
   - 当 gating 命中时，切换到 Window A
   - 将 `window_a_meta` 写入：
     - `report.json`
     - `run_trace.json`
     - `delivery_bundle.json.metadata`

3. 新增验证脚本：
   - `eval/window_a_compare.py`
   功能：
   - 对 2~3 份不同复杂度 PRD
   - 对比单路评审与 Window A 模式
   - 统计：
     - open questions 数量
     - risk items 数量
     - token / 耗时

4. 更新测试：
   - `tests/test_review_service_handoff.py`
   - 必要时新增 `tests/test_window_a_integration.py`

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v12): integrate Window A into main review flow with comparison evaluation"`
```

---

## 九、执行建议

### 不要再重复执行的旧阶段

以下旧提示词已经过时，不建议继续使用：

- 旧文档中的 `Phase A`
- 旧文档中的 `Phase B`
- 旧文档中的 `Phase C`

原因：

- 它们对应的大部分代码已经在当前仓库中落地
- 继续按旧步骤执行，容易产生重复修改、无意义测试和冲突提交

### 当前最合理的推进顺序

如果你想先补主线价值，优先做：

1. `Phase D`
2. `Phase E`
3. `Phase F`

如果你想先补“面试/展示”价值，优先做：

1. `Phase I`
2. `Phase G`
3. `Phase D`

### 每步通用要求

每个步骤执行时都要求：

1. 先确认当前分支
2. 先读取相关现有实现，不要凭空重写
3. 代码改动后必须补测试
4. 最后运行 `python -m pytest -q`
5. 只有测试通过才提交

---

## 十、最终建议

如果目标是尽快让项目更像“企业研发流程中台”，建议优先补：

- Source Connector
- Review Workspace / approval records
- Adapter + execution callback

如果目标是提升项目差异化与面试亮点，建议优先补：

- Window A 并行 Reviewer
- 模板版本化
- 通知与审计

这两条路线都成立，但不要同时全面铺开，否则容易再次进入“功能很多、主线不清”的状态。


---

## 十一、Phase G+：通知 / 审计 / 模板版本化深化

> 目标：把当前 Phase G 从“抽象层与 dry-run 落盘”推进到“可查询、可切换、可联动”的治理能力。

### Step G-4：模板注册中心接入 FastAPI / MCP 查询

```text
你正在仓库中工作。
基于 `feature/v10-platform-governance` 继续开发，不要新开分支。

任务：
1. 在后端新增模板查询能力：
   - FastAPI: `GET /api/templates`
   - FastAPI: `GET /api/templates/{template_type}`
   - MCP tool: `get_template_registry`

2. 返回内容至少包括：
   - `template_id`
   - `template_type`
   - `version`
   - `description`
   - `is_default`
   - `status`

3. 在 `requirement_review_v1/templates/registry.py` 中补充：
   - 默认模板查找
   - 按类型查找
   - 按版本查找
   - 模板不存在时的受控错误

4. 在 `run_trace.json` 中保留本次运行实际命中的模板版本，不允许只记录默认值。

5. 更新测试：
   - `tests/test_template_registry.py`
   - `tests/test_mcp_tools.py`
   - 如有必要新增 `tests/test_template_api.py`

6. 运行 `python -m pytest -q`

7. 提交：
   `git commit -am "feat(v10): expose template registry through FastAPI and MCP with explicit version resolution"`
```

### Step G-5：通知投递器与审计日志联动

```text
你正在 `feature/v10-platform-governance` 分支上工作。

任务：
1. 在 `requirement_review_v1/notifications/` 中新增：
   - `dispatcher.py`
   - `models.py`

2. 目标：
   - 将当前 dry-run notification record 升级为统一 dispatch 流程
   - 每条通知都生成：
     - notification id
     - event type
     - channel
     - payload
     - dispatch status
     - created_at
     - dispatched_at

3. 集成到以下动作：
   - `approve_handoff`
   - `handoff_to_executor`
   - `update_execution_task`
   - 高风险阻断

4. 审计联动要求：
   - 通知创建写入 `notifications.jsonl`
   - 投递结果写入 `audit_log.jsonl`
   - 失败时保留错误原因，不得静默吞掉

5. 仍然不做真实外部网络发送，但要把 dispatch 生命周期做完整，便于以后替换成真实 Feishu / WeCom sender。

6. 更新测试：
   - `tests/test_notifications.py`
   - `tests/test_audit_logging.py`
   - `tests/test_mcp_tools.py`

7. 运行 `python -m pytest -q`

8. 提交：
   `git commit -am "feat(v10): add notification dispatch lifecycle and audit integration"`
```

### Step G-6：审计查询与受控重试入口

```text
你正在 `feature/v10-platform-governance` 分支上工作。

任务：
1. 在后端新增审计查询接口：
   - FastAPI: `GET /api/audit`
   - MCP tool: `get_audit_events`

2. 支持过滤条件：
   - `run_id`
   - `bundle_id`
   - `task_id`
   - `event_type`
   - `status`

3. 在 `retry.py` 中补充最小重试入口：
   - 仅针对非阻断的 notification dispatch / artifact generation
   - 不对 approval transition 做自动重试

4. 新增 MCP tool：
   - `retry_operation(run_id: str, operation: str, options: dict[str, Any] | None = None)`

5. 要求：
   - 每次 retry 都写审计日志
   - 返回重试前后状态与错误信息
   - 非法 operation 返回受控错误

6. 更新测试：
   - `tests/test_audit_logging.py`
   - `tests/test_retry_metadata.py`
   - `tests/test_mcp_tools.py`

7. 运行 `python -m pytest -q`

8. 提交：
   `git commit -am "feat(v10): add audit query and controlled retry entrypoints for platform governance"`
```

---

## 十二、Phase J：数据库持久化升级（SQLite 优先）

> 目标：把当前基于 JSON 文件的状态管理升级为“SQLite 主存储 + 文件产物保留”的模式，优先解决查询、并发和审计问题。

### Step J-1：定义数据库 schema 与 repository 抽象

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v13-sqlite-persistence`

任务：
1. 在 `requirement_review_v1/persistence/` 下创建：
   - `__init__.py`
   - `db.py`
   - `models.py`
   - `repository.py`

2. 先使用标准库 `sqlite3`，不要引入 SQLAlchemy。

3. 设计最小表结构：
   - `review_runs`
   - `delivery_bundles`
   - `approval_records`
   - `status_snapshots`
   - `execution_tasks`
   - `trace_links`
   - `audit_events`
   - `notifications`

4. 要求：
   - `db.py` 负责连接管理与 schema 初始化
   - `repository.py` 负责 CRUD 封装
   - 每张表保留 `created_at` / `updated_at`
   - 为 `run_id`、`bundle_id`、`task_id` 建索引

5. 数据库文件默认路径：
   - `data/runtime.db`

6. 新增测试：
   - `tests/test_sqlite_repository.py`
   - 覆盖建表、插入、查询、更新、唯一键约束

7. 运行：
   - `python -m pytest tests/test_sqlite_repository.py -v`
   - `python -m pytest -q`

8. 提交：
   `git commit -am "feat(v13): add sqlite persistence layer and repository abstractions"`
```

### Step J-2：将审批、执行、审计、通知改为数据库主写入

```text
你正在 `feature/v13-sqlite-persistence` 分支上工作。

任务：
1. 修改以下模块，使其变为“双写模式”：
   - 继续保留现有 JSON 文件产物
   - 新增 SQLite 主写入

2. 集成点：
   - `requirement_review_v1/service/review_service.py`
   - `requirement_review_v1/service/execution_service.py`
   - `requirement_review_v1/workspace/repository.py`
   - `requirement_review_v1/monitoring/audit.py`
   - `requirement_review_v1/notifications/dispatcher.py`

3. 要求：
   - run 完成时写 `review_runs`
   - bundle 生成/审批时写 `delivery_bundles`、`approval_records`、`status_snapshots`
   - handoff/update 时写 `execution_tasks`
   - traceability 写 `trace_links`
   - 审计与通知分别入库

4. 保持向后兼容：
   - 原有 JSON 文件仍生成
   - 查询接口优先走 SQLite，SQLite 不可用时可降级读文件

5. 更新测试：
   - `tests/test_mcp_tools.py`
   - `tests/test_review_service_handoff.py`
   - 新增 `tests/test_dual_write_persistence.py`

6. 运行 `python -m pytest -q`

7. 提交：
   `git commit -am "feat(v13): dual-write workflow state into sqlite while preserving file artifacts"`
```

### Step J-3：新增数据库查询 API / MCP

```text
你正在 `feature/v13-sqlite-persistence` 分支上工作。

任务：
1. 在 FastAPI 中新增查询接口：
   - `GET /api/runs`
   - `GET /api/bundles`
   - `GET /api/tasks`
   - `GET /api/traceability`
   - `GET /api/notifications`

2. 在 MCP 中新增工具：
   - `list_runs`
   - `list_bundles`
   - `list_tasks`
   - `list_notifications`

3. 查询能力要求：
   - 支持分页
   - 支持按状态过滤
   - 支持按 `run_id / bundle_id / task_id` 精确查询
   - 返回 SQLite 查询结果，而不是拼文件目录

4. 更新测试：
   - 新增 `tests/test_query_api.py`
   - 更新 `tests/test_mcp_tools.py`

5. 运行 `python -m pytest -q`

6. 提交：
   `git commit -am "feat(v13): expose sqlite-backed query APIs for runs, bundles, tasks, traceability, and notifications"`
```

---

## 十三、Phase K：前端 Review Workspace / Execution Dashboard

> 目标：在现有 `frontend/` 目录基础上落地一个轻量工作台，用于查看运行状态、审批 bundle、追踪执行任务，而不是只靠 JSON 文件和 MCP 查询。

### Step K-1：初始化前端工作台骨架

```text
你正在仓库中工作。
从 main 创建新分支：`git checkout -b feature/v14-frontend-workspace`

任务：
1. 检查 `frontend/` 目录当前状态；若只有日志或依赖缓存，则在该目录初始化一个最小 Vite + React 前端。

2. 要求：
   - 复用已有 `frontend/` 目录，不新建第二套前端
   - 创建最小结构：
     - `frontend/package.json`
     - `frontend/index.html`
     - `frontend/src/main.jsx`
     - `frontend/src/App.jsx`
     - `frontend/src/styles.css`

3. UI 方向：
   - 偏“运维 / 审批工作台”而不是营销页
   - 首页展示系统概览：runs、bundles、tasks、blocked items
   - 桌面端和移动端都能正常显示

4. 新增前端基础校验：
   - `npm run build`
   - 如已有 lint，则接入 lint

5. 提交：
   `git commit -am "feat(v14): bootstrap frontend workspace dashboard with Vite and React"`
```

### Step K-2：实现 Runs / Bundles / Tasks 三个核心视图

```text
你正在 `feature/v14-frontend-workspace` 分支上工作。

任务：
1. 在前端新增页面/组件：
   - `RunsPage`
   - `BundlesPage`
   - `TasksPage`
   - `StatusBadge`
   - `DetailPanel`

2. 数据来源：
   - 调用后端新增的 SQLite 查询 API

3. 界面要求：
   - Runs 列表：展示 run_id、status、coverage、high_risk_ratio、created_at
   - Bundles 列表：展示 bundle_id、bundle_status、workspace_status、approval history 摘要
   - Tasks 列表：展示 task_id、executor_type、execution_mode、status、updated_at
   - 支持点击行查看详情

4. 样式要求：
   - 不要默认白底表格堆砌
   - 使用明确的信息层级、状态色和卡片布局
   - 保持移动端可读

5. 加入加载态、空态、错误态

6. 验证：
   - `npm run build`
   - 如可行，补前端组件测试或最小交互测试

7. 提交：
   `git commit -am "feat(v14): add runs, bundles, and tasks dashboard views backed by workflow query APIs"`
```

### Step K-3：实现审批与执行操作面板

```text
你正在 `feature/v14-frontend-workspace` 分支上工作。

任务：
1. 在 Bundle 详情页中加入审批操作：
   - approve
   - need_more_info
   - block_by_risk
   - reset_to_draft

2. 在 Task 详情页中加入执行操作：
   - update status
   - append checkpoint
   - complete / fail / cancel

3. 调用后端现有 API / MCP 对应 HTTP 封装接口，不要在前端直接操作文件。

4. 要求：
   - 每次操作后自动刷新详情和列表
   - 展示最近的 approval records / audit events / notifications 摘要
   - 对危险操作增加确认弹层

5. 验证：
   - `npm run build`
   - 至少人工走通一轮：bundle 审批 -> handoff -> task 更新

6. 提交：
   `git commit -am "feat(v14): add approval and execution action panels to the workspace dashboard"`
```

### Step K-4：补充 Traceability / Notifications / Audit 视图

```text
你正在 `feature/v14-frontend-workspace` 分支上工作。

任务：
1. 新增：
   - `TraceabilityPage`
   - `NotificationsPage`
   - `AuditPage`

2. 页面目标：
   - Traceability: 按 requirement / bundle / task 查看映射链
   - Notifications: 查看通知事件、状态、失败原因
   - Audit: 查看关键操作日志与过滤条件

3. 交互要求：
   - 支持按 `run_id / bundle_id / task_id / event_type / status` 过滤
   - Traceability 支持侧边详情展开

4. 样式要求：
   - 保持与前面页面一致的设计语言
   - 避免做成纯 CRUD 后台模板风格

5. 验证：
   - `npm run build`
   - 如已有测试框架，补至少一个页面级测试

6. 提交：
   `git commit -am "feat(v14): add traceability, notifications, and audit views to the workspace dashboard"`
```

---

## 十四、扩展后的推荐顺序

如果你要优先补“治理能力”，推荐顺序调整为：

```text
Phase G   基础平台治理抽象
    ->
Phase G+  查询 / dispatch / retry
    ->
Phase J   SQLite 持久化
    ->
Phase K   Frontend Workspace Dashboard
```

理由：

- 没有治理抽象，数据库表结构会反复改
- 没有数据库，前端只能继续读文件，价值有限
- 先做 SQLite，再做 dashboard，整体收益最高
