# 基于当前 v4 分支的主干并入与后续实施评估

## 1. 结论

当前 `feature/project-delivery-handoff` 分支已经具备作为后续版本开发基线的条件，建议先并入 `main`，再开展 v5、v6 迭代。

结论依据如下：

- 当前分支已完成从“需求评审”到“delivery planning / coding-agent handoff artifact 生成”的能力扩展，不再是实验性分支。
- 改动边界清晰，集中在 `delivery_planning`、`packs`、`handoff renderer`、`review_service` 及相关测试，不属于长期漂移形成的混合型分支。
- 在 `D:\venvs\marrdp` 虚拟环境内，已验证 `python -m pytest -q` 全量通过，共 `136` 个测试。
- 后续 v5、v6 规划中的审批流、traceability、execution orchestration 等能力都依赖当前 v4 产出的 planning 与 handoff 结构，继续在功能分支上滚动开发会抬高后续合并与回归成本。

## 2. 当前 v4 分支的真实能力边界

### 2.1 已具备能力

当前 v4 分支已具备以下能力：

- LangGraph 评审主流程稳定存在，并已插入 `delivery_planning` 节点。
- 可从 review 结果生成：
  - `implementation_plan`
  - `test_plan`
  - `codex_prompt_handoff`
  - `claude_code_prompt_handoff`
- 可进一步生成结构化 handoff 工件：
  - `implementation_pack.json`
  - `test_pack.json`
  - `execution_pack.json`
- 可从 `execution_pack` 派生面向执行方的 Markdown prompt：
  - `codex_prompt.md`
  - `claude_code_prompt.md`
- CLI、API、MCP 共用统一服务层，主链路没有发生分叉破坏。
- 已有较完整测试覆盖 pack schema、builder、renderer、service 集成与 trace 回写。

### 2.2 尚未具备能力

以下内容在当前分支中仍未真正落地，后续规划不能将其视为“已存在基础设施”：

- 真实的 `Connector` 抽象层
  - 当前输入仍主要是 `prd_text / prd_path`，尚未形成 `FeishuConnector / URLConnector / LocalFileConnector` 的统一接口模型。
- 正式的多角色独立交付物体系
  - 当前更接近“单份综合报告 + 三类 pack”，尚未稳定拆分为 `open_questions.md`、`scope_boundary.md`、`tech_design_draft.md`、`test_checklist.md` 等独立 artifact。
- 审批状态机与人工 Gate
  - 目前没有正式的 `approved / need_more_info / blocked_by_risk` 等审批实体与持久化流程。
- handoff 编排层
  - 当前仅负责生成 handoff 文件，不负责真正的 executor routing、自动/半自动/人工模式切换。
- traceability 持久化层
  - 尚未具备 `requirement -> review item -> dev task -> test item -> execution task` 的独立 repository 与查询能力。
- execution task 生命周期
  - 当前状态追踪主要面向 review job，而非 handoff 执行任务。
- v2 规划中的 MCP 工具集
  - 当前 MCP 仍以 `review_prd` 和 `get_report` 为主，尚未扩展为完整交付流程工具集。

## 3. 是否应先并入 main

建议先将当前 v4 分支并入 `main`。

原因如下：

- `main` 若作为持续主干，应承载已经被验证且会成为后续版本依赖的基线能力。
- 当前分支与 `main` 的差异可控，且改动主题单一，适合在此时并入。
- 若继续在功能分支上推进 v5、v6，再回合到 `main`，后续合并将同时混入：
  - v4 handoff 基础能力
  - v5/v6 新能力
  - 期间 `main` 可能产生的额外偏移
- 先并入 `main` 后再做后续版本，便于：
  - 稳定主线叙事
  - 降低回归范围
  - 简化版本切分
  - 提高评估与文档口径的一致性

因此，当前更合理的演进方式不是继续让 v4 长期悬空，而是将其确认为新的主干能力基线。

## 4. 后续版本实施建议

### 4.1 v4 在 main 中的定位

建议将 v4 定义为：

“需求评审 + delivery planning + coding-agent handoff artifact 生成”的主干版本。

其边界应明确为：

- 负责需求评审与交付准备
- 负责生成结构化 planning 与 handoff 工件
- 不直接修改目标仓库
- 不直接执行目标仓库内命令
- 不直接承诺审批、追踪、调度闭环已完整实现

### 4.2 v5 建议聚焦交付物标准化与最小审批闭环

v5 建议优先完成以下内容：

- 将综合报告拆分为正式 artifact：
  - `prd_review_report.md`
  - `open_questions.md`
  - `scope_boundary.md`
  - `tech_design_draft.md`
  - `test_checklist.md`
- 定义 `delivery_bundle` 正式 schema
- 引入最小审批状态：
  - `draft`
  - `need_more_info`
  - `approved`
  - `blocked_by_risk`
- 增加最小 bundle 生命周期与落盘结构
- 在 MCP 中补充最小交付能力：
  - `generate_delivery_bundle`
  - `approve_handoff`

v5 的目标应是“交付物标准化 + 人工确认可插入”，而不是“自动执行”。

### 4.3 v6 再推进编排与追踪

在 v5 定稳之后，再推进 v6：

- `handoff_to_executor`
- `get_execution_status`
- `agent_assisted / human_only / agent_auto` 模式
- execution task 状态机
- traceability map
- approval records / status snapshot

这一步才是从“生成 handoff 文件”走向“管理 handoff 流程”。

## 5. 工期与优先级重估

相较于原始开发计划，建议按以下顺序推进：

### Phase A：v4 并入 main

目标：

- 完成主干合并
- 保持测试全绿
- 同步更新主干文档口径

判断：

- 风险低
- 工期短
- 应优先完成

### Phase B：v5 交付物标准化

目标：

- 从当前综合输出中拆出正式 artifact
- 建立 `delivery_bundle` 作为统一 source of truth
- 引入最小审批状态

判断：

- 高可行
- 收益最高
- 实际复杂度高于“生成几份 Markdown”的表面印象

### Phase C：v6 流程编排与追踪

目标：

- executor routing
- execution task 状态管理
- traceability 查询
- 审批记录沉淀

判断：

- 可行
- 复杂度显著高于 v5
- 不建议与 v5 混做

## 6. 主要风险

需要在后续实施中显式控制以下风险：

- 当前 v4 已有 handoff 文件生成，但尚无真正的执行编排基础设施。
- 现有测试证明的是内部模块稳定，不等同于外部 Agent 集成、异步回流和审批流已经成熟。
- `main` 当前的仓库叙事仍偏向 requirement review core，v4 并入后需同步修正文档，否则主线表达会滞后于代码现实。
- 若同时推进 frontend、connector、approval、traceability、notification，主线会迅速失焦。

## 7. 最终建议

建议按以下顺序落地：

1. 先将当前 v4 分支并入 `main`
2. 以并入后的 `main` 为基线定义 v5：交付物标准化 + 最小审批闭环
3. 再以 `main` 为基线定义 v6：handoff 编排 + execution 状态 + traceability
4. 暂缓将通知系统、外部企业工具接入、完整 Web UI 作为主线任务

## 8. 默认假设

本评估基于以下默认假设：

- `main` 作为持续主干，而不是长期冻结的展示线
- 当前 v4 分支的定位是“交付准备能力”，不是“直接自动执行代码改动”
- 后续版本优先保证主线叙事清晰，而不是追求功能点数量
- 当前测试结果可作为并入主干的准入依据
