# 飞书主入口落地方案（最小闭环版）

本文用于对齐“以飞书为主入口”的最小可用交互，目标是让普通用户不需要理解技术细节，也能完成从提审到交付的闭环。

## 新增章节：文档属性与受众

- 用户文档内容：用户旅程、卡片文案、按钮命名、页面提示语
- 管理员/架构文档内容：配置项、接口映射、风险降级、回调与参数透传

## 一、推荐主入口形态

- 飞书应用内 H5 工作入口页：`/feishu`
- 飞书消息卡片：状态提醒 + 快捷按钮
- 飞书内结果页：`/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>`

设计原则：

- 聊天消息只做“提醒和跳转”
- 复杂阅读和填写全部放在 H5 页
- 每条卡片只给 2-3 个最关键动作

## 二、三层入口职责

### 1) 机器人消息 / 群聊入口

用户可见文案（示例）：

- `PRD评审助手已就绪，点“开始评审”即可提交文档。`
- `你的评审正在处理中，稍后可点“查看最新结果”。`
- `还差一点信息，请点“继续澄清”补充后自动更新结果。`
- `评审已完成，可选择修订 PRD，或直接进入下一步交付。`

按钮文案与去向：

- `开始评审` -> `/feishu`
- `查看最新结果` -> `/run/<run_id>?embed=feishu...`
- `继续澄清` -> `/run/<run_id>?embed=feishu...#clarification`
- `生成修订草稿` -> `/run/<run_id>?embed=feishu...#revision`
- `确认后生成handoff/roadmap` -> `/run/<run_id>?embed=feishu...#next-delivery`
- `重新提交` -> `/feishu`
- `跳过修订，直接交付` -> `/run/<run_id>?embed=feishu...#next-delivery`

最适合承载：

- 状态通知
- 下一步引导
- 一键跳转

不建议承载：

- 大段填写（如多条澄清答案）
- 复杂结果阅读（风险、发现、冲突）

### 2) 飞书消息卡片快捷操作

卡片标题建议：

- `PRD评审进度`

卡片正文建议：

- 运行中：`正在分析你的文档，请稍后查看结果。`
- 待澄清：`需要补充关键信息，补充后会自动更新。`
- 已完成：`评审已完成，可选择修订后再交付，也可直接交付。`

卡片按钮建议（按状态裁剪）：

- 始终优先：`查看最新结果`
- 待澄清：`继续澄清`
- 已完成：`生成修订草稿`
- 修订确认后：`生成handoff/roadmap`
- 已完成（兼容路径）：`跳过修订，直接交付`
- 始终保留：`重新提交`

### 3) 飞书 H5 页面（工作入口页 + 结果页）

工作入口页：`/feishu`

- 页面定位：`飞书工作入口`
- 核心动作：`开始评审`、`查看最新结果`、`继续澄清`、`生成修订草稿`、`确认后生成handoff/roadmap`、`跳过修订，直接交付`、`重新提交`

结果页：`/run/<run_id>?embed=feishu...`

- 页面文案：`评审结果`
- 核心动作：刷新状态、查看结果、回答澄清、选择是否修订、确认修订版、进入下一步交付区
- 页面锚点：
  - `#clarification`：澄清回答区
  - `#revision`：修订草稿生成与确认区（含会议纪要/额外要求上传）
  - `#next-delivery`：下一步交付区（产物下载/交付准备）

## 三、用户旅程（最小闭环）

1. 用户在飞书中点击 `开始评审` 进入 `/feishu`
2. 用户提交文档后拿到 run，并可点击 `查看最新结果`
3. 在 `/run/<run_id>?embed=feishu...` 查看进度与结果
4. 若提示待澄清，点击 `继续澄清` 直达澄清区提交答案
5. 用户选择是否修订 PRD：
   - 修订路径：上传会议纪要和额外要求（可选）-> 生成并确认修订版
   - 兼容路径：跳过修订，直接进入下一步交付
6. 点击 `生成handoff/roadmap` 进入交付区继续推进

## 新增章节：修订版约定（用户可见规则）

- 修订版是草稿/派生版本，不自动覆盖原文
- handoff / roadmap 默认基于“已确认修订版”
- 若未修订，仍可基于当前版本继续交付（兼容旧流程）

## 四、飞书端最小配置项

- App ID / App Secret
- 事件回调：`POST /api/feishu/events`
- 提审回调：`POST /api/feishu/submit`
- 澄清回调：`POST /api/feishu/clarification`
- 主入口 H5：`/feishu`
- 结果页 URL 模板：`/run/<run_id>?embed=feishu&open_id=<open_id>&tenant_key=<tenant_key>`

## 五、后端接口映射

- 飞书入口层：
  - `POST /api/feishu/events`
  - `POST /api/feishu/submit`
  - `POST /api/feishu/clarification`
- 复用核心评审接口：
  - `POST /api/review`
  - `GET /api/review/{run_id}`
  - `GET /api/review/{run_id}/result`
  - `POST /api/review/{run_id}/clarification`

## 六、风险与降级

- 卡片能力受限：卡片仅保留“状态 + 跳转”
- 回调偶发失败：用户仍可通过 `/feishu` 与 `/run/...` 自助继续
- 上下文缺失导致 403：统一保留 `open_id`、`tenant_key` 透传
- 签名联调复杂：本地可临时关闭签名，生产必须开启

## 七、演示材料

演示素材和拍摄脚本请参考：

- [feishu-demo-assets.md](./feishu-demo-assets.md)
