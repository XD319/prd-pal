# Feishu Setup

这份文档覆盖“本地已跑通后，如何把用户在飞书里的提审、澄清和结果查看打通”。

## 最终要打通的链路

1. 用户在飞书里提交文档或 PRD 内容
2. 后端接收飞书请求并创建 `run_id`
3. 用户在飞书里打开 H5 结果页
4. 如需澄清，用户在飞书里提交答案
5. 后端刷新结果并保留审计记录

## 一、接入前提

先完成本地验证：

- [quick-start.md](/D:/Backup/Career/Projects/AgentProject/prd-pal/docs/quick-start.md)

再准备：

- 一套可公网访问的 HTTPS 域名
- 一个 Feishu 应用
- Feishu 文档访问能力
- 飞书事件订阅
- 飞书内可打开的 H5 页面

## 二、必须配置的环境变量

在 `.env` 中至少补齐：

```dotenv
MARRDP_FEISHU_APP_ID=your-app-id
MARRDP_FEISHU_APP_SECRET=your-app-secret
MARRDP_FEISHU_SIGNATURE_DISABLED=false
MARRDP_FEISHU_WEBHOOK_SECRET=your-webhook-secret
MARRDP_FEISHU_SIGNATURE_TOLERANCE_SEC=300
```

建议生产环境同时打开 API 鉴权：

```dotenv
MARRDP_API_AUTH_DISABLED=false
MARRDP_API_KEY=replace-with-a-secret
```

本地 mock 联调时，可先关闭飞书签名校验：

```dotenv
MARRDP_FEISHU_SIGNATURE_DISABLED=true
```

## 三、飞书应用里要配置什么

至少配置这些地址：

- 事件回调:
  - `POST https://<your-domain>/api/feishu/events`
- 提交评审:
  - `POST https://<your-domain>/api/feishu/submit`
- 回答澄清:
  - `POST https://<your-domain>/api/feishu/clarification`

推荐的 H5 页面：

- 轻量提交页:
  - `https://<your-domain>/feishu`
- 结果页:
  - `https://<your-domain>/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>`

## 四、本地联调顺序

### 1. 先启动服务

```bash
start-dev.cmd
```

或：

```bash
docker-compose up --build
```

### 2. 验证事件挑战

```bash
curl -X POST "http://127.0.0.1:8000/api/feishu/events" \
  -H "Content-Type: application/json" \
  -d "{\"type\":\"url_verification\",\"challenge\":\"challenge-token\"}"
```

预期响应：

```json
{
  "challenge": "challenge-token"
}
```

### 3. 验证飞书提交

```bash
curl -X POST "http://127.0.0.1:8000/api/feishu/submit" \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"feishu://docx/doc-token\",\"mode\":\"quick\",\"open_id\":\"ou_mock_user\",\"tenant_key\":\"tenant_mock\"}"
```

预期响应：

```json
{
  "run_id": "20260309T000000Z"
}
```

### 4. 打开结果页

在浏览器或飞书 WebView 中打开：

```text
http://127.0.0.1:5173/run/<run_id>?embed=feishu&open_id=ou_mock_user&tenant_key=tenant_mock
```

预期结果：

- 页面能正常打开
- 只显示适合飞书 H5 的紧凑布局
- 能看到当前 run 的进度和结果

### 5. 验证澄清回写

```bash
curl -X POST "http://127.0.0.1:8000/api/feishu/clarification" \
  -H "Content-Type: application/json" \
  -d "{\"run_id\":\"20260309T000000Z\",\"question_id\":\"clarify-1\",\"answer\":\"Use successful dashboard arrival within 30 seconds.\",\"open_id\":\"ou_mock_user\",\"tenant_key\":\"tenant_mock\"}"
```

预期响应会包含：

- `clarification_status`
- `has_pending_questions`
- `result_page`

## 五、生产环境上线清单

1. 域名已启用 HTTPS
2. `outputs/` 已挂载持久化存储
3. `MARRDP_FEISHU_SIGNATURE_DISABLED=false`
4. Feishu webhook secret 与服务端环境变量一致
5. Feishu 应用已配置正确的 callback URL
6. 至少完成一次 challenge 握手
7. 至少成功提交一次真实飞书文档评审
8. 至少成功在飞书里打开一次结果页
9. 至少成功完成一次澄清回写

## 六、上线后怎么排障

先看这些文件是否存在：

- `outputs/<run_id>/report.json`
- `outputs/<run_id>/entry_context.json`
- `outputs/<run_id>/audit_log.jsonl`

它们分别说明：

- `report.json`: 评审结果是否已成功产出
- `entry_context.json`: 飞书身份上下文是否已落盘
- `audit_log.jsonl`: 提交和澄清是否已记录

再看这些接口：

- `GET /health`
- `GET /ready`
- `GET /api/review/{run_id}`
- `GET /api/review/{run_id}/result?open_id=<open_id>&tenant_key=<tenant_key>`

## 七、推荐给业务用户的使用方式

如果是第一次上线，建议只开放这两种操作：

- 在飞书里发起评审
- 在飞书里打开结果页

把更复杂的工作台、历史对比、工作空间版本流转留在后续阶段。这样更容易保证首发体验稳定。
