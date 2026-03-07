# Codex 分阶段开发提示词

基于 `v4-mainline-feasibility-assessment.md` 评估结论，将后续开发拆分为三个主要阶段（Phase A / B / C），每个阶段内再细分为可独立执行的步骤。每个步骤对应一条 Codex 提示词，可直接复制到 Codex 中执行。

---

## Phase A：v4 并入 main + 主干文档同步

> 目标：完成主干合并，保持测试全绿，同步更新主干文档口径。

### Step A-1：合并前回归验证

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。
当前处于 feature/project-delivery-handoff 分支。

任务：
1. 在虚拟环境 D:\venvs\marrdp 中运行 `python -m pytest -q`，确认全量测试通过。
2. 运行 `python -m requirement_review_v1.main --input docs/sample_prd.md`，确认主流程可正常生成以下产物：
   - outputs/<run_id>/report.md
   - outputs/<run_id>/report.json
   - outputs/<run_id>/implementation_pack.json
   - outputs/<run_id>/test_pack.json
   - outputs/<run_id>/execution_pack.json
   - outputs/<run_id>/codex_prompt.md
   - outputs/<run_id>/claude_code_prompt.md
3. 检查 run_trace.json 中 handoff_renderer 和 pack_builder 的 status 字段是否均为 "ok"。
4. 如果有任何失败，修复后重新验证，直到全部通过。

不要修改任何功能代码，只做验证。如果发现问题，报告问题但不自行修复。
```

### Step A-2：执行 main 合并

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。

任务：
1. 切换到 main 分支：`git checkout main`
2. 确保 main 是最新的：`git pull origin main`
3. 合并 feature/project-delivery-handoff：`git merge feature/project-delivery-handoff --no-ff -m "merge: v4 delivery planning and coding-agent handoff into main"`
4. 如果出现合并冲突，逐文件解决，优先保留 feature 分支的内容（因为 feature 分支是更新的能力基线）。
5. 合并完成后运行 `python -m pytest -q` 确认测试全绿。
6. 运行 `python -m requirement_review_v1.main --input docs/sample_prd.md` 确认主流程正常。

不要 push，只做本地合并和验证。
```

### Step A-3：更新 pyproject.toml 版本号

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 main 分支上工作。

任务：
1. 打开 pyproject.toml
2. 将 version 从 "3.0.0" 更新为 "4.0.0"
3. 将 description 更新为：
   "LangGraph-based requirement review, delivery planning, and coding-agent handoff system"
4. 确认改动后 `python -m pytest -q` 仍然全绿。
5. 提交：`git commit -am "chore: bump version to 4.0.0 for delivery planning baseline"`
```

### Step A-4：同步主干文档

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 main 分支上工作。

任务：
1. 更新 README.md，使其反映 v4 的能力边界：
   - 系统定位：需求评审 + delivery planning + coding-agent handoff artifact 生成
   - 核心能力：LangGraph 评审主流程、implementation/test/execution pack 生成、codex/claude code prompt 渲染
   - 明确边界：不直接修改目标仓库、不直接执行命令、不承诺审批/追踪/调度闭环
   - 使用方式：CLI / FastAPI / MCP 三种入口
   - 保留已有的安装和配置说明

2. 创建 docs/release-notes-v4.md，内容包括：
   - v4 新增能力清单
   - 与 v3 的差异说明
   - 已知限制（对应 v4-mainline-feasibility-assessment.md 中 2.2 节的内容）
   - 后续版本预告（v5 交付物标准化、v6 流程编排）

3. 提交：`git commit -am "docs: update README and add v4 release notes for main baseline"`
4. 推送本地提交（可用非沙箱执行）
不要修改任何功能代码。
```

---

## Phase B：v5 交付物标准化与最小审批闭环

> 目标：从当前综合输出中拆出正式 artifact，建立 delivery_bundle 作为统一 source of truth，引入最小审批状态。

### Step B-1：定义 delivery_bundle schema

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 main 分支上工作。
从 main 创建新分支：`git checkout -b feature/v5-delivery-bundle`

任务：
在 requirement_review_v1/packs/ 目录下创建 delivery_bundle.py，定义 delivery_bundle 的正式 schema。

设计要求：
1. 使用 Pydantic v2 模型，继承项目已有的 AgentSchemaModel（位于 requirement_review_v1/schemas/base.py）
2. DeliveryBundle 应包含以下字段：
   - bundle_id: str（唯一标识）
   - bundle_version: str = "1.0"
   - created_at: str（ISO 8601 时间戳）
   - status: BundleStatus（枚举：draft / need_more_info / approved / blocked_by_risk）
   - source_run_id: str（关联的 review run_id）
   - artifacts: DeliveryArtifacts（包含所有交付物路径和内容摘要）
   - approval_history: list[ApprovalEvent]（审批事件列表）
   - metadata: dict[str, Any]

3. DeliveryArtifacts 应包含：
   - prd_review_report: ArtifactRef
   - open_questions: ArtifactRef
   - scope_boundary: ArtifactRef
   - tech_design_draft: ArtifactRef
   - test_checklist: ArtifactRef
   - implementation_pack: ArtifactRef
   - test_pack: ArtifactRef
   - execution_pack: ArtifactRef

4. ArtifactRef 应包含：
   - artifact_type: str
   - path: str
   - content_hash: str = ""
   - generated_at: str = ""

5. ApprovalEvent 应包含：
   - event_id: str
   - timestamp: str
   - from_status: BundleStatus
   - to_status: BundleStatus
   - reviewer: str = ""
   - comment: str = ""

6. BundleStatus 使用 StrEnum 定义

在 tests/ 目录下创建 test_delivery_bundle_schema.py，验证：
- DeliveryBundle 可以正常实例化和序列化
- BundleStatus 枚举值正确
- ApprovalEvent 状态转换合法性
- ArtifactRef 基本字段验证

运行 `python -m pytest tests/test_delivery_bundle_schema.py -v` 确认通过。
提交：`git commit -am "feat(v5): define DeliveryBundle schema with approval status model"`
```

### Step B-2：实现 artifact 拆分生成器

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

当前系统在 review_service.py 的 build_delivery_handoff_outputs() 中生成 implementation_pack.json / test_pack.json / execution_pack.json。现在需要在此基础上，增加独立 artifact 的拆分生成能力。

任务：
1. 在 requirement_review_v1/packs/ 目录下创建 artifact_splitter.py，实现 ArtifactSplitter 类：

   class ArtifactSplitter:
       """从 review 结果中拆分出独立的交付物文件。"""

       def split(self, review_result: dict, run_dir: Path) -> dict[str, ArtifactRef]:
           """
           从 review_result 中提取并生成以下独立文件：
           - prd_review_report.md：基于 final_report 字段
           - open_questions.md：从 review_results 中提取 is_ambiguous=True 或 issues 非空的条目
           - scope_boundary.md：从 parsed_items + plan 中提取边界定义
           - tech_design_draft.md：从 implementation_plan + tasks 中提取技术设计草案
           - test_checklist.md：从 test_plan + review_results 中提取测试清单
           返回 artifact_type -> ArtifactRef 的映射。
           """

2. 每个 Markdown artifact 应有清晰的标题、来源说明和结构化内容。

3. 在 tests/ 目录下创建 test_artifact_splitter.py，验证：
   - 给定完整的 review_result mock 数据，能正确生成 5 个 Markdown 文件
   - 文件内容包含预期的标题和关键信息
   - 空输入时优雅降级（生成带占位内容的文件）
   - 返回的 ArtifactRef 路径正确

4. 运行 `python -m pytest tests/test_artifact_splitter.py -v` 确认通过。
5. 运行 `python -m pytest -q` 确认全量测试不受影响。
6. 提交：`git commit -am "feat(v5): implement ArtifactSplitter for independent delivery artifacts"`
```

### Step B-3：实现 DeliveryBundle 构建器

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

任务：
1. 在 requirement_review_v1/packs/ 目录下创建 bundle_builder.py，实现 DeliveryBundleBuilder：

   class DeliveryBundleBuilder:
       """组装完整的 DeliveryBundle。"""

       def build(
           self,
           run_output: dict[str, Any],
           artifact_refs: dict[str, ArtifactRef],
           pack_paths: dict[str, str],
       ) -> DeliveryBundle:
           """
           将 review 产出、拆分后的 artifact 引用、pack 路径组装为 DeliveryBundle。
           - bundle_id 基于 run_id 生成
           - 初始 status 为 draft
           - artifacts 字段整合 artifact_refs 和 pack_paths
           - approval_history 初始为空
           """

       def save(self, bundle: DeliveryBundle, output_dir: Path) -> Path:
           """将 bundle 序列化为 delivery_bundle.json 并写入 output_dir。"""

2. 在 tests/ 目录下创建 test_bundle_builder.py，验证：
   - 从 mock 数据构建 bundle 成功
   - bundle_id 格式正确
   - 初始 status 为 draft
   - save 后文件可被重新加载并验证 schema
   - artifacts 字段包含所有预期的 artifact 引用

3. 运行 `python -m pytest tests/test_bundle_builder.py -v` 确认通过。
4. 运行 `python -m pytest -q` 确认全量测试不受影响。
5. 提交：`git commit -am "feat(v5): implement DeliveryBundleBuilder for unified bundle assembly"`
```

### Step B-4：实现最小审批状态机

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

任务：
1. 在 requirement_review_v1/packs/ 目录下创建 approval.py，实现审批状态管理：

   合法的状态转换规则：
   - draft -> need_more_info（需要补充信息）
   - draft -> approved（直接批准）
   - draft -> blocked_by_risk（风险阻断）
   - need_more_info -> draft（补充完成，回到草稿）
   - need_more_info -> blocked_by_risk（发现风险）
   - blocked_by_risk -> draft（风险解除）
   - approved 是终态，不可回退

   实现：
   - VALID_TRANSITIONS: dict[BundleStatus, set[BundleStatus]]，定义合法转换
   - approve_bundle(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle
   - request_more_info(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle
   - block_by_risk(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle
   - reset_to_draft(bundle: DeliveryBundle, reviewer: str, comment: str) -> DeliveryBundle
   - 每个操作都应：校验状态转换合法性、追加 ApprovalEvent、返回更新后的 bundle
   - 非法转换抛出 InvalidTransitionError

2. 在 tests/ 目录下创建 test_approval.py，验证：
   - 所有合法转换路径
   - 非法转换抛出 InvalidTransitionError
   - ApprovalEvent 正确记录 from_status / to_status / reviewer / comment / timestamp
   - approved 终态不可回退
   - 连续多次状态转换后 approval_history 长度正确

3. 运行 `python -m pytest tests/test_approval.py -v` 确认通过。
4. 运行 `python -m pytest -q` 确认全量测试不受影响。
5. 提交：`git commit -am "feat(v5): implement minimal approval state machine for DeliveryBundle"`
```

### Step B-5：集成到 review_service 主流程

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

任务：
1. 修改 requirement_review_v1/service/review_service.py 中的 build_delivery_handoff_outputs() 函数：
   - 在现有 pack 构建逻辑之后，调用 ArtifactSplitter 生成独立 artifact
   - 调用 DeliveryBundleBuilder 组装 DeliveryBundle
   - 将 delivery_bundle.json 写入 run_dir
   - 在 ReviewResultSummary 中新增 delivery_bundle_path 字段
   - 在 trace 中记录 bundle_builder 的执行状态

2. 确保向后兼容：
   - 现有的 implementation_pack / test_pack / execution_pack / codex_prompt / claude_code_prompt 生成逻辑不变
   - delivery_bundle 是新增产物，不影响已有产物
   - 如果 bundle 构建失败，不应阻断主流程（non_blocking）

3. 修改 requirement_review_v1/service/review_service.py 中的 _build_summary() 函数，
   将 delivery_bundle_path 纳入 ReviewResultSummary。

4. 更新 tests/test_review_service_handoff.py，增加对 delivery_bundle 产物的断言：
   - delivery_bundle.json 文件存在
   - 内容可被 DeliveryBundle.model_validate() 验证
   - bundle status 为 draft
   - artifacts 字段包含所有预期引用

5. 运行 `python -m pytest -q` 确认全量测试通过。
6. 提交：`git commit -am "feat(v5): integrate DeliveryBundle generation into review_service main flow"`
```

### Step B-6：扩展 MCP 工具集

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

任务：
1. 在 requirement_review_v1/mcp_server/server.py 中新增两个 MCP tool：

   @mcp.tool()
   async def generate_delivery_bundle(
       run_id: str,
       options: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """
       为已完成的 review run 生成或重新生成 DeliveryBundle。
       - 加载 run_id 对应的 report.json
       - 调用 ArtifactSplitter + DeliveryBundleBuilder
       - 返回 bundle_id、status、artifact 路径列表
       """

   @mcp.tool()
   def approve_handoff(
       bundle_id: str,
       action: Literal["approve", "need_more_info", "block_by_risk", "reset_to_draft"],
       reviewer: str = "",
       comment: str = "",
       options: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """
       对 DeliveryBundle 执行审批操作。
       - 加载 bundle_id 对应的 delivery_bundle.json
       - 执行状态转换
       - 持久化更新后的 bundle
       - 返回更新后的 status 和 approval_history
       """

2. 实现辅助函数来定位和加载 bundle 文件（基于 run_id 或 bundle_id 在 outputs/ 目录下查找）。

3. 更新 tests/test_mcp_tools.py，增加对新 tool 的测试：
   - generate_delivery_bundle 正常流程
   - generate_delivery_bundle 对不存在的 run_id 返回错误
   - approve_handoff 正常审批流程
   - approve_handoff 非法状态转换返回错误

4. 运行 `python -m pytest -q` 确认全量测试通过。
5. 提交：`git commit -am "feat(v5): add generate_delivery_bundle and approve_handoff MCP tools"`
```

### Step B-7：v5 文档与合并

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v5-delivery-bundle 分支上工作。

任务：
1. 创建 docs/release-notes-v5.md，内容包括：
   - v5 新增能力：DeliveryBundle schema、独立 artifact 拆分、最小审批状态机、MCP 新工具
   - 交付物清单：列出所有新增的 artifact 文件及其用途
   - 审批流程说明：状态转换图、各状态含义、使用示例
   - 与 v4 的差异：从"综合输出"到"标准化交付物"的演进
   - 已知限制：bundle 仅落盘到本地文件系统、无持久化数据库、无通知机制

2. 更新 docs/handoff-plan.md，补充 DeliveryBundle 相关内容。

3. 更新 pyproject.toml 版本号为 "5.0.0"。

4. 运行 `python -m pytest -q` 确认全量测试通过。

5. 提交：`git commit -am "docs: v5 release notes and version bump to 5.0.0"`
6. 推送本地提交（可用非沙箱执行）
注意：不要执行 git merge，合并操作将单独进行。
```

---

## Phase C：v6 流程编排与追踪

> 目标：从"生成 handoff 文件"走向"管理 handoff 流程"，实现 executor routing、execution task 状态机、traceability map。

### Step C-1：定义 execution task 模型

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库中工作。
从 main 创建新分支：`git checkout -b feature/v6-execution-orchestration`

任务：
1. 在 requirement_review_v1/ 目录下创建 execution/ 包（含 __init__.py），创建 models.py：

   定义以下模型（使用 Pydantic v2，继承 AgentSchemaModel）：

   ExecutionMode（StrEnum）：
   - agent_auto：全自动，Agent 独立执行
   - agent_assisted：半自动，Agent 执行但需人工确认关键节点
   - human_only：纯人工执行

   ExecutionTaskStatus（StrEnum）：
   - pending：待执行
   - assigned：已分配执行方
   - in_progress：执行中
   - waiting_review：等待人工审查
   - completed：已完成
   - failed：执行失败
   - cancelled：已取消

   ExecutionTask：
   - task_id: str
   - bundle_id: str（关联的 DeliveryBundle）
   - source_pack_type: str（implementation_pack / test_pack）
   - executor_type: str（codex / claude_code / human）
   - execution_mode: ExecutionMode
   - status: ExecutionTaskStatus
   - created_at: str
   - updated_at: str
   - assigned_to: str = ""
   - execution_log: list[ExecutionEvent]
   - result_summary: str = ""

   ExecutionEvent：
   - event_id: str
   - timestamp: str
   - event_type: str（assigned / started / checkpoint / completed / failed / cancelled）
   - detail: str = ""
   - actor: str = ""

2. 在 tests/ 目录下创建 test_execution_models.py，验证模型实例化、序列化、枚举值。

3. 运行 `python -m pytest tests/test_execution_models.py -v` 确认通过。
4. 提交：`git commit -am "feat(v6): define ExecutionTask and ExecutionMode models"`
```

### Step C-2：实现 executor router

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v6-execution-orchestration 分支上工作。

任务：
1. 在 requirement_review_v1/execution/ 目录下创建 router.py，实现 ExecutorRouter：

   class ExecutorRouter:
       """根据 DeliveryBundle 和配置决定执行方分配策略。"""

       def __init__(self, default_mode: ExecutionMode = ExecutionMode.agent_assisted):
           self.default_mode = default_mode

       def route(self, bundle: DeliveryBundle) -> list[ExecutionTask]:
           """
           从 approved 状态的 DeliveryBundle 生成 ExecutionTask 列表。
           路由规则：
           - implementation_pack -> 生成实现任务，默认分配给 codex
           - test_pack -> 生成测试任务，默认分配给 claude_code
           - 如果 bundle 中有 high-level risk，自动降级为 agent_assisted 模式
           - 如果 bundle status 不是 approved，抛出 BundleNotApprovedError
           """

       def reassign(self, task: ExecutionTask, new_executor: str, new_mode: ExecutionMode) -> ExecutionTask:
           """重新分配执行方和模式。"""

2. 在 tests/ 目录下创建 test_executor_router.py，验证：
   - approved bundle 正确生成 ExecutionTask 列表
   - 非 approved bundle 抛出错误
   - 高风险 bundle 自动降级模式
   - reassign 正确更新执行方

3. 运行 `python -m pytest tests/test_executor_router.py -v` 确认通过。
4. 运行 `python -m pytest -q` 确认全量测试不受影响。
5. 提交：`git commit -am "feat(v6): implement ExecutorRouter for task assignment"`
```

### Step C-3：实现 execution task 状态机

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v6-execution-orchestration 分支上工作。

任务：
1. 在 requirement_review_v1/execution/ 目录下创建 task_lifecycle.py：

   合法的状态转换：
   - pending -> assigned
   - assigned -> in_progress
   - in_progress -> waiting_review（仅 agent_assisted 模式）
   - in_progress -> completed
   - in_progress -> failed
   - waiting_review -> in_progress（审查通过，继续执行）
   - waiting_review -> failed（审查不通过）
   - pending / assigned / in_progress / waiting_review -> cancelled

   实现：
   - VALID_TASK_TRANSITIONS: dict[ExecutionTaskStatus, set[ExecutionTaskStatus]]
   - assign_task(task, executor, actor) -> ExecutionTask
   - start_task(task, actor) -> ExecutionTask
   - request_review(task, actor, detail) -> ExecutionTask
   - complete_task(task, actor, result_summary) -> ExecutionTask
   - fail_task(task, actor, reason) -> ExecutionTask
   - cancel_task(task, actor, reason) -> ExecutionTask
   - 每个操作追加 ExecutionEvent，更新 updated_at

2. 在 tests/ 目录下创建 test_task_lifecycle.py，验证所有合法/非法转换路径。

3. 运行 `python -m pytest tests/test_task_lifecycle.py -v` 确认通过。
4. 提交：`git commit -am "feat(v6): implement execution task state machine"`
```

### Step C-4：实现 traceability map

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v6-execution-orchestration 分支上工作。

任务：
1. 在 requirement_review_v1/execution/ 目录下创建 traceability.py：

   class TraceabilityMap:
       """维护 requirement -> review item -> dev task -> test item -> execution task 的追踪关系。"""

       def __init__(self):
           self._links: list[TraceLink] = []

       def build_from_bundle(self, bundle: DeliveryBundle, tasks: list[ExecutionTask]) -> "TraceabilityMap":
           """
           从 DeliveryBundle 和 ExecutionTask 列表构建追踪关系。
           遍历 bundle 中的 parsed_items，关联到对应的 plan tasks、test items、execution tasks。
           """

       def query_by_requirement(self, requirement_id: str) -> list[TraceLink]:
           """查询某个需求条目的完整追踪链。"""

       def query_by_execution_task(self, task_id: str) -> list[TraceLink]:
           """查询某个执行任务的上游追踪链。"""

       def to_dict(self) -> dict[str, Any]:
           """序列化为可持久化的字典。"""

       def save(self, output_path: Path) -> None:
           """保存为 traceability_map.json。"""

   TraceLink 模型：
   - requirement_id: str
   - review_item_id: str = ""
   - plan_task_id: str = ""
   - test_item_id: str = ""
   - execution_task_id: str = ""
   - link_type: str（full / partial / orphan）

2. 在 tests/ 目录下创建 test_traceability.py，验证：
   - 从 mock bundle + tasks 构建 map
   - 按 requirement_id 查询返回完整链
   - 按 execution_task_id 查询返回上游链
   - 序列化和反序列化一致

3. 运行 `python -m pytest tests/test_traceability.py -v` 确认通过。
4. 提交：`git commit -am "feat(v6): implement TraceabilityMap for end-to-end requirement tracking"`
```

### Step C-5：扩展 MCP 工具集（v6）

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v6-execution-orchestration 分支上工作。

任务：
1. 在 requirement_review_v1/mcp_server/server.py 中新增以下 MCP tool：

   @mcp.tool()
   async def handoff_to_executor(
       bundle_id: str,
       execution_mode: str = "agent_assisted",
       options: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """
       将 approved 的 DeliveryBundle 交付给执行方。
       - 调用 ExecutorRouter 生成 ExecutionTask 列表
       - 持久化 task 到 run_dir
       - 返回 task 列表和分配详情
       """

   @mcp.tool()
   def get_execution_status(
       bundle_id: str | None = None,
       task_id: str | None = None,
       options: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """
       查询执行状态。
       - 支持按 bundle_id 查询所有关联 task
       - 支持按 task_id 查询单个 task
       - 返回 task 状态、执行日志、traceability 信息
       """

   @mcp.tool()
   def get_traceability(
       requirement_id: str | None = None,
       task_id: str | None = None,
       bundle_id: str | None = None,
       options: dict[str, Any] | None = None,
   ) -> dict[str, Any]:
       """
       查询追踪关系。
       - 支持从 requirement / task / bundle 任一维度查询
       - 返回完整的追踪链
       """

2. 更新 tests/test_mcp_tools.py，增加对新 tool 的测试。

3. 运行 `python -m pytest -q` 确认全量测试通过。
4. 提交：`git commit -am "feat(v6): add execution orchestration MCP tools"`
```

### Step C-6：v6 文档与合并准备

```text
你正在 Multi-Agent-Requirement-Review-and-Delivery-Planning-System 仓库的 feature/v6-execution-orchestration 分支上工作。

任务：
1. 创建 docs/release-notes-v6.md，内容包括：
   - v6 新增能力：ExecutionTask 模型、ExecutorRouter、任务状态机、TraceabilityMap、MCP 新工具
   - 执行模式说明：agent_auto / agent_assisted / human_only 的区别和适用场景
   - 状态机转换图
   - 追踪关系说明
   - 与 v5 的差异：从"管理交付物"到"管理执行流程"
   - 已知限制：无真实 Agent 调用适配层、无异步回流、无通知机制

2. 更新 docs/handoff-plan.md，补充 v6 编排层内容。

3. 更新 README.md，反映 v6 的完整能力。

4. 更新 pyproject.toml 版本号为 "6.0.0"。

5. 运行 `python -m pytest -q` 确认全量测试通过。

6. 提交：`git commit -am "docs: v6 release notes and version bump to 6.0.0"`

注意：不要执行 git merge，合并操作将单独进行。
```

---

## 执行建议

### 执行顺序

```
Phase A (A-1 → A-2 → A-3 → A-4)  ← 必须先完成
    ↓
Phase B (B-1 → B-2 → B-3 → B-4 → B-5 → B-6 → B-7)
    ↓
Phase C (C-1 → C-2 → C-3 → C-4 → C-5 → C-6)
```

### 每步执行前检查

1. 确认当前在正确的分支上
2. 确认前一步的提交已完成
3. 确认 `python -m pytest -q` 全绿

### 每步执行后检查

1. 确认新增/修改的文件符合预期
2. 确认 `python -m pytest -q` 全绿
3. 确认 git log 显示正确的提交信息

### 风险控制

- Phase A 风险最低，应优先完成
- Phase B 的 B-5（集成到主流程）是最关键的步骤，需要特别注意向后兼容
- Phase C 的复杂度显著高于 Phase B，建议在 Phase B 完全稳定后再开始
- 每个 Phase 完成后，先合并到 main 再开始下一个 Phase
