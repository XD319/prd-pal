# Feishu 管理员接入指南

本文面向管理员与部署者，目标是把 `prd-pal` 接入飞书并稳定上线。  
普通用户如何在飞书中使用，请看 [feishu-user-guide.md](./feishu-user-guide.md)。

## 适用范围

- 你负责飞书应用配置或服务部署
- 你需要让团队成员可在飞书里提交评审、查看结果、回答澄清
- 你需要一份可复用的最小上线清单

## 接入目标（管理员视角）

完成接入后，应满足以下结果：

1. 用户可在飞书中发起评审
2. 用户可在飞书中打开完整 H5 结果页
3. 用户可在飞书中回答澄清问题
4. 用户可继续进入下一步交付动作
5. 系统可保留必要审计信息（来源身份与交互记录）

## 管理员最小配置清单

这是可上线的最小必需配置，建议逐项打勾：

### A. 基础条件

- [ ] 服务已部署到可公网访问的 HTTPS 域名
- [ ] `outputs/` 已配置持久化存储
- [ ] 已完成 [quick-start.md](./quick-start.md) 的本地链路验证

### B. 服务端环境变量

- [ ] 已设置 `MARRDP_FEISHU_APP_ID`
- [ ] 已设置 `MARRDP_FEISHU_APP_SECRET`
- [ ] 已设置 `MARRDP_FEISHU_WEBHOOK_SECRET`
- [ ] 已设置 `MARRDP_FEISHU_SIGNATURE_DISABLED=false`
- [ ] 已设置 `MARRDP_FEISHU_SIGNATURE_TOLERANCE_SEC=300`（或更严格值）
- [ ] 生产环境已开启 API 鉴权（推荐）

参考：

```dotenv
MARRDP_FEISHU_APP_ID=your-app-id
MARRDP_FEISHU_APP_SECRET=your-app-secret
MARRDP_FEISHU_SIGNATURE_DISABLED=false
MARRDP_FEISHU_WEBHOOK_SECRET=your-webhook-secret
MARRDP_FEISHU_SIGNATURE_TOLERANCE_SEC=300

MARRDP_API_AUTH_DISABLED=false
MARRDP_API_KEY=replace-with-a-strong-secret
```

### C. 飞书应用回调与页面地址

- [ ] 事件回调地址：`POST https://<your-domain>/api/feishu/events`
- [ ] 评审提交地址：`POST https://<your-domain>/api/feishu/submit`
- [ ] 澄清提交地址：`POST https://<your-domain>/api/feishu/clarification`
- [ ] 飞书工作入口地址：`https://<your-domain>/feishu`
- [ ] 飞书结果页可正常打开：`https://<your-domain>/run/<run_id>?trigger_source=feishu&open_id=<open_id>&tenant_key=<tenant_key>&embed=feishu`

## 推荐接入流程（管理员）

1. 完成部署并确认 HTTPS 可用
2. 写入并生效飞书相关环境变量
3. 在飞书应用后台配置回调地址与入口页面
4. 完成一次事件订阅 challenge 校验
5. 用真实飞书文档完成一次提交与结果查看
6. 完成一次澄清回答并验证结果刷新

## 验收标准（上线前）

满足以下项即可视为“可用首发版本”：

- `GET /health` 与 `GET /ready` 正常
- challenge 校验成功
- 至少一次真实飞书评审提交成功
- 飞书内可打开结果页
- 至少一次澄清回答成功
- `outputs/<run_id>/report.json` 已生成
- `outputs/<run_id>/entry_context.json` 已生成
- `outputs/<run_id>/audit_log.jsonl` 已生成

## 常见问题

### 1) 事件订阅验证失败怎么办？

- 先确认 `MARRDP_FEISHU_WEBHOOK_SECRET` 与飞书应用后台一致
- 再确认回调地址是 HTTPS 且可被公网访问
- 最后确认服务端时间同步正常，避免签名时间窗口误差

### 2) 用户能提交但打不开结果页怎么办？

- 检查结果页地址是否为 `https://<your-domain>/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>` 结构
- 推荐显式保留 `trigger_source=feishu`，便于审计和链路排查
- 检查是否误删 `embed=feishu` 参数（会影响飞书内布局）
- 检查是否正确传递了 `open_id` 与 `tenant_key`

### 3) 用户回答澄清后结果不刷新怎么办？

- 确认澄清提交地址配置正确
- 检查服务日志中是否有对应 `run_id` 的澄清记录
- 检查 `outputs/<run_id>/audit_log.jsonl` 是否新增澄清事件

### 4) 是否可以先关闭签名校验？

仅允许在本地联调阶段临时设置：

```dotenv
MARRDP_FEISHU_SIGNATURE_DISABLED=true
```

生产环境必须改回 `false`。

## 相关文档

- 普通用户使用说明：[feishu-user-guide.md](./feishu-user-guide.md)
- 飞书主入口落地方案：[feishu-main-entry-mvp.md](./feishu-main-entry-mvp.md)
- 演示材料说明：[feishu-demo-assets.md](./feishu-demo-assets.md)
- 本地启动说明：[quick-start.md](./quick-start.md)
- 部署说明：[deployment-guide.md](./deployment-guide.md)
