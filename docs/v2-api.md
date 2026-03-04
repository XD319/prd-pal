# Requirement Review V2 API

该文档说明 `requirement_review_v1` 的最小 REST API，用于异步触发需求评审并按 `run_id` 查询进度与下载报告。

## 启动服务

```bash
uvicorn requirement_review_v1.server.app:app --host 0.0.0.0 --port 8000 --reload
```

> 服务会复用现有输出目录：`outputs/<run_id>/`，并生成 `report.md`、`report.json`、`run_trace.json`。

## 1) 创建评审任务

`POST /api/review`

请求体二选一：
- `prd_text`: 直接传 PRD 文本
- `prd_path`: 传本地 PRD 文件路径（相对路径基于项目根目录）

### curl 示例（传文本）

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -d "{\"prd_text\":\"# Sample PRD\n\nThe system shall support password reset within 5 minutes.\"}"
```

### curl 示例（传文件路径）

```bash
curl -X POST "http://127.0.0.1:8000/api/review" \
  -H "Content-Type: application/json" \
  -d "{\"prd_path\":\"docs/sample_prd.md\"}"
```

返回示例：

```json
{
  "run_id": "20260304T103210Z"
}
```

## 2) 查询任务状态与进度

`GET /api/review/{run_id}`

返回字段：
- `status`: `queued` / `running` / `completed` / `failed`
- `progress`: 包含 `percent`、`current_node`、`nodes`（节点级状态）等
- `report_paths`: 产物路径（任务完成后可用）

### curl 示例

```bash
curl "http://127.0.0.1:8000/api/review/20260304T103210Z"
```

返回示例（节选）：

```json
{
  "run_id": "20260304T103210Z",
  "status": "running",
  "progress": {
    "percent": 60,
    "current_node": "reviewer",
    "nodes": {
      "parser": {"status": "completed", "runs": 1},
      "planner": {"status": "completed", "runs": 1},
      "risk": {"status": "completed", "runs": 1},
      "reviewer": {"status": "running", "runs": 1}
    }
  }
}
```

## 3) 下载报告

`GET /api/report/{run_id}?format=md|json`

- `format=md`：返回 `report.md`
- `format=json`：返回 `report.json`

### curl 示例

```bash
curl "http://127.0.0.1:8000/api/report/20260304T103210Z?format=md"
curl "http://127.0.0.1:8000/api/report/20260304T103210Z?format=json"
```
