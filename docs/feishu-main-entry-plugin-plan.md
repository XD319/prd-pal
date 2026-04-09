# 飞书主入口插件化改造方案

## 结论

这个项目适合改成“飞书主入口”的插件形态，但不适合改成“所有能力都用飞书原生卡片完成”的纯卡片产品。

更合适的目标架构是：

- 飞书插件 / 机器人 / 卡片作为主入口
- 当前 Python Review Engine 继续作为核心后端
- 复杂结果查看页继续保留为 H5 页面，优先考虑在飞书内打开
- 飞书卡片主要承接提交、状态通知、澄清追问、结果跳转

## 为什么适合

当前仓库已经具备比较完整的后端主链路，飞书入口更像是增加一个“前台”而不是重写系统：

- `requirement_review_v1/server/app.py`
  - 已有提交、查询状态、拉取结果、回填澄清等异步 API
- `requirement_review_v1/connectors/feishu.py`
  - 已支持飞书/Lark 文档作为输入源
- `frontend/src/pages/HomePage.jsx`
  - 当前 Web 首页主要是提审表单和历史列表
- `frontend/src/pages/RunDetailsPage.jsx`
  - 当前详情页主要承担复杂结果展示
- `frontend/src/hooks/useReviewRun.js`
  - 当前详情页已经按“提交后异步轮询 + 完成后取结果”的模型组织

换句话说，这个项目最适合做的不是“把引擎搬进飞书”，而是“让飞书承接用户入口，把现有引擎封装成飞书可消费的后端能力”。

## 不建议的方向

不建议一开始就做成下面这种形态：

- 只保留飞书卡片，不保留独立结果页
- 所有 findings / risks / conflicts / trace 都在卡片里展开
- 运行中每一步都依赖飞书事件回调维持状态

原因很直接：

- 当前结果信息密度高，卡片承载复杂度有限
- 调试成本会明显高于普通 Web API + H5 页面
- 你现在已有可用的 Web 结果页，重写收益不高

## 推荐目标架构

```text
飞书用户
  ->
飞书插件入口 / 机器人消息 / 文档侧边栏
  ->
Feishu App Backend Adapter
  ->
现有 Review API / Review Service / Connector Registry
  ->
outputs/<run_id> 产物
  ->
飞书消息卡片 + 飞书内 H5 结果页
```

### 职责划分

飞书侧负责：

- 登录态和用户身份
- 文档选择或链接选择
- 提审入口
- 运行中通知
- 澄清问题回填
- 打开结果页

后端负责：

- PRD 内容获取
- review mode gating
- normalizer
- reviewers
- aggregator
- report artifacts

H5 结果页负责：

- 大段结果阅读
- findings / risks / conflicts / trace 可视化
- 历史 run 浏览
- 报告下载

## MVP 范围

第一版飞书主入口建议只做下面四件事：

1. 飞书内发起评审
2. 飞书内收到运行状态通知
3. 飞书内回答澄清问题
4. 飞书内打开结果详情页

下面这些放到第二阶段更合适：

- 飞书原生历史列表
- 飞书原生复杂筛选
- 飞书原生长报告阅读器
- 多租户 / 多空间权限映射
- 飞书通讯录粒度的权限隔离

## 分阶段实施方案

## Phase 1：飞书入口适配层

目标：

- 让飞书插件能够调用现有评审能力发起 run
- 不改动核心 review 主链路

建议新增能力：

- `POST /api/feishu/submit`
- `POST /api/feishu/events`
- 飞书签名校验、challenge 响应、基础用户上下文解析

建议新增文件：

- `requirement_review_v1/integrations/feishu/__init__.py`
- `requirement_review_v1/integrations/feishu/models.py`
- `requirement_review_v1/integrations/feishu/security.py`
- `requirement_review_v1/integrations/feishu/router.py`

关键设计：

- 飞书适配层只做协议转换，不直接写 review 逻辑
- 提交后仍然调用现有 `POST /api/review` 对应的服务层能力
- 把 `open_id` / `user_id` / `tenant_key` 放进 audit metadata

验收标准：

- 能从飞书插件提交 `source` 或 `prd_text`
- 返回 `run_id`
- challenge 校验通过
- 未签名 / 签名错误请求被拒绝

### Prompt 1

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
为当前 Review Engine 增加“飞书主入口适配层”，但不要修改核心 review 主链路。飞书层只负责协议转换、签名校验、事件接入和提交入口封装。

请先检查以下文件：
- requirement_review_v1/server/app.py
- requirement_review_v1/service/review_service.py
- requirement_review_v1/connectors/feishu.py
- tests/test_server_app_source_input.py
- tests/test_server_app_security.py

实现要求：
1. 新增一个飞书集成模块目录：
   - requirement_review_v1/integrations/feishu/__init__.py
   - requirement_review_v1/integrations/feishu/models.py
   - requirement_review_v1/integrations/feishu/security.py
   - requirement_review_v1/integrations/feishu/router.py

2. 在 FastAPI 中挂载飞书入口：
   - POST /api/feishu/events
   - POST /api/feishu/submit

3. 具体要求：
   - /api/feishu/events 支持 challenge 响应
   - 为飞书事件增加基础签名校验能力；使用环境变量驱动，不要把密钥写死
   - /api/feishu/submit 接收飞书侧传入的 source / prd_text / mode 等字段
   - /api/feishu/submit 最终复用现有 review 提交逻辑，返回 run_id
   - 飞书入口层本身不实现 review，不复制 review_service 逻辑
   - 在 audit_context 或 metadata 中保留 open_id、tenant_key、trigger_source=feishu 等信息

4. 测试要求：
   - 覆盖 challenge 成功
   - 覆盖签名失败
   - 覆盖成功提交 review run
   - 覆盖非法 payload

5. 文档要求：
   - 更新 docs/v2-api.md，增加飞书入口说明

6. 验证：
   - pytest -q tests/test_server_app_security.py tests/test_server_app_source_input.py

请优先保持后向兼容，避免改动现有 review API contract。
```

## Phase 2：飞书提交入口 UI

目标：

- 让用户在飞书内完成提审
- 复用现有 Web 表单的输入模型

实现策略：

- 插件首页只做轻量入口
- 支持三类输入：
  - 直接选择飞书文档
  - 粘贴飞书文档链接
  - 粘贴纯文本 PRD

建议交互：

- 选择来源
- 填写模式 `auto / quick / full`
- 提交成功后展示 `run_id` 和“查看进度”按钮

### Prompt 2

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
设计并实现一个“飞书主入口提交页”的最小版本。它不需要替代完整结果页，只需要让用户在飞书内完成发起评审。

请先检查以下文件：
- frontend/src/pages/HomePage.jsx
- frontend/src/components/ReviewSubmitPanel.jsx
- frontend/src/utils/submission.js
- frontend/src/api.js

实现要求：
1. 基于现有提交模型，抽离一个适合飞书入口使用的提交表单层。
2. 不要破坏现有 Web 首页；优先复用提交校验和 payload 构造逻辑。
3. 新增一个“飞书入口模式”的页面或组件，支持：
   - source
   - prd_text
   - mode
4. 这个页面的定位是轻量提交器，不展示复杂历史列表。
5. 交互要求：
   - 默认强调“飞书文档链接 / 飞书 source”
   - 提交成功后显示 run_id
   - 提供进入详情页的按钮或可复用跳转能力
6. 样式要求：
   - 保持现有视觉语言
   - 不做大而全工作台
   - 让移动端也可读

如果你认为应该把“飞书入口页”做成一个独立 route，请直接实现，并保证现有首页不回归。
```

## Phase 3：飞书状态通知与卡片刷新

目标：

- 用户不用一直盯着详情页
- run 状态变化时在飞书中收到更新

建议新增能力：

- review 提交成功后，记录发起人飞书身份
- 运行状态变化时生成飞书卡片 payload
- 完成 / 失败 / 待澄清时发送不同卡片

结合当前仓库，优先升级：

- `requirement_review_v1/notifications/feishu.py`

当前它只是 dry-run payload renderer，可以在这个基础上演进为真正的发送器或“发送器 + renderer”分层。

卡片建议最少包含：

- run_id
- 当前状态
- 关键摘要
- 打开结果页按钮
- 若需要澄清，则带“去回答”按钮

### Prompt 3

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
把当前 FeishuNotifier 从“dry-run payload renderer”演进成可用于飞书主入口方案的通知模块，但要保持分层清晰。

请先检查以下文件：
- requirement_review_v1/notifications/feishu.py
- requirement_review_v1/notifications/base.py
- requirement_review_v1/notifications/models.py
- requirement_review_v1/service/review_service.py

实现要求：
1. 保留“payload 构造”和“实际发送”分层，不要把所有逻辑堆在一个类里。
2. 能根据 review run 状态生成不同卡片：
   - submitted / running
   - completed
   - failed
   - clarification_required
3. 卡片内容至少包含：
   - run_id
   - status
   - summary
   - 查看详情链接
4. 若当前环境不适合真实联网发送，请至少把发送接口、配置模型、payload renderer 和 dry-run 记录打通，便于后续切换到真实发送。
5. 如果 review_service 当前没有足够的通知触发点，请增加最小必要的钩子，但不要重构整个流程。

测试要求：
- 覆盖不同状态下的 payload 结构
- 覆盖 dry-run dispatch 记录
- 不破坏现有通知测试
```

## Phase 4：飞书卡片内澄清追问

目标：

- 当 review 需要澄清时，用户直接在飞书里回答
- 回答后调用现有澄清回填能力

现有可复用能力：

- `POST /api/review/{run_id}/clarification`
- `answer_review_clarification(...)`

建议做法：

- 飞书卡片只收集答案，不在卡片内重算结果
- 提交答案后仍调用现有服务层逻辑
- 回答成功后，推送“澄清已应用”卡片，并提供结果页入口

### Prompt 4

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
为飞书主入口方案补齐“卡片内回答澄清问题”的能力，直接复用当前 clarification service，不复制业务逻辑。

请先检查以下文件：
- requirement_review_v1/service/review_service.py
- requirement_review_v1/server/app.py
- frontend/src/components/ClarificationPanel.jsx
- frontend/src/hooks/useReviewRun.js

实现要求：
1. 为飞书集成层新增一个澄清提交入口，例如：
   - POST /api/feishu/clarification
   或
   - POST /api/feishu/card/actions/clarification
2. 请求体中应能携带：
   - run_id
   - question_id
   - answer
   - open_id / tenant_key 等飞书上下文
3. 最终必须复用 answer_review_clarification(...) 或现有 clarification API，不要复制澄清更新逻辑。
4. 响应中返回：
   - 更新后的澄清状态
   - 是否还有待回答问题
   - 结果页跳转信息
5. 若一个 run 当前没有启用 clarification gate，应返回受控错误。

测试要求：
 - 覆盖正常回答
 - 覆盖 run 不存在
 - 覆盖 clarification 未启用
 - 覆盖重复回答或非法 payload
```

## Phase 5：飞书内 H5 结果页

目标：

- 让用户“全程在飞书操作”，但不牺牲复杂结果可读性

推荐实现：

- 保留现有 React 详情页主结构
- 增加一个“飞书嵌入模式”
- 在飞书内打开 `/run/:runId?embed=feishu`

飞书嵌入模式建议做的收敛：

- 弱化顶栏导航
- 保留进度、摘要、发现、风险、澄清、下载
- 减少不必要的工作台装饰

### Prompt 5

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
把现有结果页改造成“既能独立 Web 使用，也能作为飞书内 H5 页面使用”的双模式页面。

请先检查以下文件：
- frontend/src/App.jsx
- frontend/src/pages/RunDetailsPage.jsx
- frontend/src/components/Navbar.jsx
- frontend/src/hooks/useReviewRun.js
- frontend/src/styles/layout.css
- frontend/src/styles/components.css

实现要求：
1. 为结果页增加 embed 模式，例如通过 query 参数 `?embed=feishu` 控制。
2. embed=feishu 时：
   - 弱化或隐藏全局导航
   - 压缩页头
   - 保留核心面板：运行进度、结果总览、发现、风险、澄清、产物下载
   - 页面在移动端可读
3. 默认 Web 模式行为不变。
4. 避免复制一套 RunDetailsPage；优先通过布局开关复用现有组件。
5. 如果现有样式过于依赖桌面宽屏，请顺手做最小必要的响应式修正。

验证要求：
 - npm run build
 - 确认默认模式和 embed 模式都能正常渲染
```

## Phase 6：飞书身份、权限与审计

目标：

- 让飞书入口具备可上线的最小安全边界

最少需要做：

- 飞书请求签名校验
- tenant 级别隔离信息
- run 与发起人映射
- 结果页访问控制
- audit log 中保留飞书上下文

建议新增内容：

- `run_metadata.json` 或等价持久化字段
- 存储：
  - submitter_open_id
  - tenant_key
  - source_origin=feishu
  - entry_mode=plugin

### Prompt 6

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
为飞书主入口方案补齐最小可上线的身份、权限和审计边界。

请先检查以下文件：
- requirement_review_v1/server/app.py
- requirement_review_v1/monitoring/audit.py
- requirement_review_v1/service/review_service.py
- outputs/ 目录下现有运行产物结构

实现要求：
1. 为飞书提交的 run 持久化入口上下文，至少包含：
   - source_origin=feishu
   - entry_mode=plugin
   - submitter_open_id
   - tenant_key
2. 设计并实现一种轻量方式，使结果页或飞书相关 API 能校验访问者是否属于允许的飞书上下文。
3. 不引入重型数据库；优先基于当前 outputs/run_dir 结构做最小可行方案。
4. 审计要求：
   - 记录提交者
   - 记录飞书入口触发来源
   - 记录澄清回答者
5. 对非法访问返回受控错误，不要泄露 run 详情。

测试要求：
 - 覆盖 metadata 持久化
 - 覆盖权限校验成功与失败
 - 覆盖 audit 记录
```

## Phase 7：部署与运维文档

目标：

- 让这个方案能真正部署，而不是只停留在代码层

至少补齐：

- 飞书应用配置项
- 回调地址
- 签名密钥环境变量
- H5 页面地址
- 本地联调方式
- 生产环境推荐拓扑

### Prompt 7

```text
你正在 D:\Backup\Career\Projects\AgentProject\PRDReview 仓库中工作。

任务目标：
补齐“飞书主入口插件化改造”的部署和运维文档，让工程团队可以按文档完成配置和联调。

请先检查以下文件：
- README.md
- docs/v2-api.md
- docs/mcp.md
- docker-compose.yml
- .env.example

文档要求：
1. 新增或更新文档，说明：
   - 飞书应用需要哪些配置
   - 回调 URL 配哪些路径
   - 哪些环境变量必填
   - H5 页面如何接入飞书内打开
   - 本地如何 mock 飞书请求
   - 生产如何部署
2. 如果当前 .env.example 缺少飞书主入口所需的变量，请补齐示例项。
3. 不要写成纯概念文档，要给出工程落地步骤。
```

## 推荐实施顺序

如果你希望尽快上线一个能用的版本，建议顺序是：

1. Phase 1：飞书入口适配层
2. Phase 3：状态通知
3. Phase 4：卡片澄清
4. Phase 5：飞书内 H5 结果页
5. Phase 6：身份与权限
6. Phase 2：飞书入口 UI 微调
7. Phase 7：部署文档

这样排的原因：

- 先把“能提审”打通
- 再把“能通知、能追问”补齐
- 再处理“复杂结果如何看”
- 最后再做更精细的入口体验和文档收口

## 低风险落地原则

实施过程中建议坚持下面这些原则：

- 不改 review engine 的主定义
- 飞书层只做 adapter，不做第二套 review 逻辑
- 卡片负责短操作，H5 负责复杂阅读
- 优先在现有 `outputs/<run_id>/` 模型上做增量扩展
- 所有飞书上下文都进入审计链路
- 默认保持现有 Web 模式可用，不做破坏式替换

## 最终建议

如果只做一个最小可用版本，建议把范围收敛成：

- 飞书提交评审
- 飞书接收状态卡片
- 飞书回答澄清
- 飞书内打开现有结果页的 embed 模式

这是当前仓库最顺手、风险最低、上线最快的改造路径。
