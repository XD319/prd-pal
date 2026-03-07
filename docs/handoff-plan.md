# Handoff Plan

## 半自动 handoff 架构

当前阶段的 handoff 方案保持两层输出：

- 结构化层：继续保留 `implementation_pack.json`、`test_pack.json`、`execution_pack.json`
- 渲染层：基于 pack 内容生成面向编码代理的 Markdown prompt，例如 `codex_prompt.md` 和 `claude_code_prompt.md`

这样做的目的，是把“机器可读的稳定契约”和“人/Agent 直接可消费的执行提示”分开。JSON pack 负责承载稳定字段、嵌套结构和后续程序化处理；Markdown prompt 负责把相同信息重排为更适合 Codex / Claude Code 直接执行的上下文。

当前实现已经将 prompt renderer 接入主流程：在生成 `execution_pack.json` 后，会自动在同目录下输出 `codex_prompt.md` 和 `claude_code_prompt.md`，并在 trace 中记录 renderer 状态、输出路径、耗时，以及失败时的 `handoff_render_error`。如果 prompt 渲染失败，不会影响原有 requirement review 和 execution pack 主结果。

## 为什么同时保留 JSON pack 与 Markdown prompt

只保留 JSON pack 不够，因为外部 coding agent 在实际使用时通常更适合消费清晰的 Markdown 指令结构，而不是直接阅读完整 JSON。

只保留 Markdown prompt 也不够，因为：

- Markdown 不适合作为稳定接口契约
- 后续如果要做自动校验、二次渲染、agent 选择或 UI 展示，结构化字段仍然需要 JSON
- JSON pack 更适合回归测试和 schema 演进

因此当前建议是：

- JSON pack 作为 source of truth
- Markdown prompt 作为从 JSON 派生的 handoff 视图

## Codex / Claude Code 的使用方式

建议的使用方式如下：

1. 运行 requirement review 主流程，例如：`python -m requirement_review_v1.main --input docs/sample_prd.md`
2. 打开 `outputs/<run_id>/codex_prompt.md`
3. 复制内容到 Codex
4. 让 Codex 在目标仓库中执行
5. Claude Code 同理：打开 `outputs/<run_id>/claude_code_prompt.md`，复制到 Claude Code，并让它在目标仓库中执行

两个 prompt 共享同一份 execution pack，但关注点不同：

- Codex prompt 更偏向实现落地，强调目标、变更项、约束和输出结果
- Claude Code prompt 更偏向验证与交付完整性，强调测试、边界情况、验收条件和剩余风险

## 当前阶段边界

当前阶段不直接自动调用外部 agent，只负责生成 handoff 文件。

明确边界如下：

- 不在 workflow 内自动触发 Codex / Claude Code
- 不接管仓库修改、CI/CD 或外部任务执行
- 不覆盖原有 artifacts 生成逻辑
- 不替换现有 `execution_pack.json` 的角色

后续如果要进入真正的自动化 handoff，可在此基础上继续增加：

- 外部 agent 调用适配层
- prompt 版本管理与回归测试
- 针对不同代码仓库类型的模板扩展
