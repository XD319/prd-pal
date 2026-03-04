# Release Notes (feature/requirement-review-v2 -> main)

## Highlights

- 引入 V2 服务层：新增 `review_service` / `report_service`，将评审执行与报告读取抽象为可复用入口，CLI/HTTP/MCP 共享核心逻辑。
- 新增最小 REST API（FastAPI）：支持异步提交评审、按 `run_id` 查询进度、下载 `md/json` 报告（见 `docs/v2-api.md`）。
- 新增 MCP Server（stdio）：提供 `ping`、`review_prd`、`get_report` 三个工具，支持外部 MCP 客户端集成（见 `docs/mcp.md`）。
- 增强风险评审链路：增加基于工具的风险证据检索与风险驱动回环路由，提高高风险场景下的审查深度。
- 增强结构化输出稳定性：完善 schema 校验与回退机制，并补充对应单元测试（schema validation / routing loop / MCP / risk tool）。
- 评估脚本可用性优化：`eval/run_eval.py` 增加项目根路径注入，降低直接执行时的导入失败概率。

## Breaking Changes

- 当前未识别到必须迁移的 breaking change（原有 CLI 入口 `python -m requirement_review_v1.main --input <file>` 仍可使用）。

## Migration Notes

- 依赖变化：`mcp` 依赖调整为 `mcp >= 1.9.1`（不再使用仅非 Windows 平台安装的 marker），Windows 环境可直接安装并运行 MCP 能力。
- 新增对外接口能力：
  - REST：`uvicorn requirement_review_v1.server.app:app --host 0.0.0.0 --port 8000 --reload`
  - MCP：`python -m requirement_review_v1.mcp_server.server`
- 环境变量：调用 LLM 仍需可用 API Key（如 `OPENAI_API_KEY`）；测试套件使用 mock，不依赖真实 API Key。

## Verification

以下为已执行的验证命令（在 `main` 基线进行）：

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
python eval/run_eval.py
pytest
```

## Suggested Tag

- 建议使用：`v2.1.0`
- 理由：
  - 相比 `main`，本次不只是修复或小改（不适合 `v2.0.1`）。
  - 本次新增了对外接口能力（REST API + MCP 工具接口），符合“新增对外接口能力 -> minor bump”的语义，优先匹配 `v2.1.0`。
  - 若按 `v2` 作为首次主版本发布，`v2.1.0` 同时体现“v2 基础上的新能力扩展”，便于后续按 patch/minor 继续迭代。
