export const TRACKED_NODES = ["parser", "clarify", "planner", "risk", "reviewer", "route_decider", "reporter"];
export const HISTORY_KEY = "requirement-review-history";
export const HISTORY_LIMIT = 8;
export const MAX_LOG_ENTRIES = 200;
export const POLL_INTERVAL_MS = 2000;
export const WEBSOCKET_FALLBACK_TIMEOUT_MS = 2500;
export const TERMINAL_STATUSES = new Set(["completed", "failed"]);

export const DEFAULT_PROGRESS = {
  percent: 0,
  current_node: "等待提交",
  nodes: {},
  updated_at: "",
};

export const DEFAULT_REPORT_MESSAGE = "任务完成后，这里会显示报告预览和下载入口。";

export const SAMPLE_PRD = `# 校园招聘多 Agent 需求评审系统

## 背景
为校招项目提供一个可提交 PRD 并自动输出评审报告的系统。

## 目标
1. 用户可以在网页上提交 PRD 文本。
2. 系统展示 parser、planner、risk、reviewer、reporter 等节点进度。
3. 完成后可以下载 Markdown 和 JSON 报告。

## 验收标准
- 提交后返回 run_id。
- 页面每 2 秒轮询状态。
- 任务完成后提供报告预览和下载入口。
- 页面支持查看最近运行历史。`;
