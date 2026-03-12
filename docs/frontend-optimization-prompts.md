# 前端界面优化 — 分步提示词设计

> 基于当前 `frontend/` 代码审查生成。每一步均需新建分支后再开始工作。

---

## 当前版本问题总览

### A. 架构 / 代码质量

| # | 问题 | 影响 |
|---|------|------|
| A1 | **单体文件**: `App.jsx` 1160+ 行，全部组件、工具函数、业务逻辑堆在一个文件里 | 可维护性差，难以复用与测试 |
| A2 | **无 TypeScript**: 全部使用 `.jsx`，缺少类型安全 | 大型重构容易引入 runtime 错误 |
| A3 | **缺少 `@vitejs/plugin-react`**: `vite.config.js` 未引入 React 插件 | JSX 热更新和 Fast Refresh 可能失效 |
| A4 | **无路由系统**: 整个应用是单页长卷，没有 React Router | 无法通过 URL 定位到具体 run 或 panel |
| A5 | **状态管理全靠 prop drilling**: `App` 层 `useState` 传递 7-8 层 props | 新增功能时耦合度高 |
| A6 | **`useEffectEvent` 尚为实验 API**: React 19 中仍不稳定 | 未来版本可能 breaking change |

### B. UI / UX

| # | 问题 | 影响 |
|---|------|------|
| B1 | **面板标题暴露组件名**: "ReviewSubmitPanel"、"FindingsPanel" 等内部命名直接展示给用户 | 不专业，用户困惑 |
| B2 | **表单字段名使用 API 参数名**: `prd_text`、`prd_path`、`source` 作为 label | 用户不理解含义 |
| B3 | **无导航/侧边栏**: 所有内容堆在一条长页面上，无法快速跳转 | 信息过载，操作效率低 |
| B4 | **无确认对话框**: "Reset workspace" 直接清空所有状态 | 容易误操作 |
| B5 | **无 Toast / 通知系统**: 成功提交、下载完成等事件无即时反馈 | 用户不确定操作是否成功 |
| B6 | **历史列表固定最多 8 条，无分页/搜索**: 超过 8 条 run 就看不到 | 无法回溯旧记录 |
| B7 | **进度条过于简单**: 缺少步骤指示器（stepper），用户不知道流水线执行到了哪一步 | 等待焦虑 |
| B8 | **无响应式侧边栏/选项卡**: 移动端体验差 | 移动设备基本不可用 |

### C. 视觉 / 无障碍

| # | 问题 | 影响 |
|---|------|------|
| C1 | **字体仅使用系统字体** (`Trebuchet MS`, `Georgia`): 风格老旧 | 视觉品质不够现代 |
| C2 | **无 favicon / PWA manifest** | 浏览器标签页无图标，不可安装 |
| C3 | **颜色对比度不足**: `--text-soft: #516274` 在白色面板上 contrast ratio 约 4.3:1，部分小字低于 WCAG AA | 弱视用户可能看不清 |
| C4 | **无 ARIA 标签和焦点管理**: 按钮、表单、状态变化无 `aria-live`、`role` 等 | 屏幕阅读器无法正确解读 |
| C5 | **无暗色模式切换**: Hero 区域深色 + Panel 区域浅色，整体视觉割裂 | 夜间使用刺眼 |
| C6 | **CSS 单文件 670 行**: 无模块化，选择器平铺 | 样式冲突风险高 |

---

## 分步优化提示词

> **使用方法**: 将每一步的提示词输入 AI 编码助手（Cursor / Claude Code / Codex 等），由 AI 完成开发。前一步完成并合并后再执行下一步。

---

### Phase 1: 工程基础修复与组件拆分

**分支名**: `frontend/phase1-architecture-cleanup`

```
请在本项目中新建一个分支 `frontend/phase1-architecture-cleanup`，然后在该分支上完成以下前端优化工作：

1. **安装缺失依赖**
   - 安装 `@vitejs/plugin-react`，并在 `vite.config.js` 中正确配置 React 插件（启用 Fast Refresh）。

2. **组件拆分**
   将 `App.jsx` 中的以下组件拆分为独立文件，放入 `src/components/` 目录：
   - `ReviewSubmitPanel` → `src/components/ReviewSubmitPanel.jsx`
   - `ReviewHistoryPanel` → `src/components/ReviewHistoryPanel.jsx`
   - `RunProgressCard` → `src/components/RunProgressCard.jsx`
   - `ReviewSummaryPanel` → `src/components/ReviewSummaryPanel.jsx`
   - `FindingsPanel` → `src/components/FindingsPanel.jsx`
   - `RisksPanel` → `src/components/RisksPanel.jsx`
   - `OpenQuestionsPanel` → `src/components/OpenQuestionsPanel.jsx`
   - `ArtifactDownloadPanel` → `src/components/ArtifactDownloadPanel.jsx`

3. **工具函数提取**
   将 `normalizeText`、`pluralize`、`formatDateTime`、`formatPercent`、`excerpt`、`severityRank`、
   `deriveFindings`、`deriveRisks`、`deriveOpenQuestions`、`deriveSummary` 等纯函数移到 `src/utils/` 目录
   下的合理文件中（如 `formatters.js`、`derivers.js`）。

4. **移除 `useEffectEvent`**
   该 API 在 React 19 中仍不稳定。将 `loadRunHistory`、`pollRunStatus`、`fetchCompletedResult`
   改为使用 `useCallback` + `useRef` 模式，保持行为一致但不依赖实验性 API。

5. **CSS 模块化**
   将 `styles.css` 按组件拆分为 CSS Modules 或按功能分块：
   - `src/styles/globals.css` — CSS 变量、reset、body
   - `src/styles/layout.css` — hero、workspace-grid、stack
   - `src/styles/panels.css` — panel 通用样式
   - `src/styles/components.css` — 按钮、badge、chip 等原子组件
   各组件文件 import 对应的样式。

6. 确保拆分后 `npm run build` 无报错，功能与拆分前完全一致。

不要添加新功能，只做结构优化和工程修复。完成后提交到该分支。
```

---

### Phase 2: 用户界面文案与表单体验优化

**分支名**: `frontend/phase2-ux-copy-and-form`

```
请在本项目中新建一个分支 `frontend/phase2-ux-copy-and-form`（基于 main 或 Phase 1 合并后的分支），
然后在该分支上完成以下 UI 文案与表单体验优化：

1. **修正面板标题**
   将所有 `section-kicker` 中暴露的组件名替换为用户友好的文案：
   - "ReviewSubmitPanel" → "New Review"
   - "RunProgressCard" → "Pipeline Status"
   - "ReviewSummaryPanel" → "Review Results"
   - "FindingsPanel" → "Review Findings"
   - "RisksPanel" → "Risk Assessment"
   - "OpenQuestionsPanel" → "Open Questions"
   - "ArtifactDownloadPanel" → "Export & Artifacts"

2. **优化表单字段 label**
   - `prd_text` → "PRD Content"（并添加 placeholder: "Paste or type your Product Requirements Document here..."）
   - `prd_path` → "File Path"（placeholder: "e.g. docs/requirements/feature-x.md"）
   - `source` → "Document Source"（placeholder: "e.g. docs/sample_prd.md or a connector reference"）

3. **添加表单验证反馈**
   - 当用户同时填写了 prd_text 和 prd_path 时，在对应字段下方实时显示警告：
     "Please provide either PRD content or a file path, not both."
   - 在 textarea 下方显示字符计数器（如 "1,234 characters"）。

4. **添加重置确认对话框**
   - 点击 "Reset workspace" 后弹出确认提示（可用原生 `window.confirm` 或简单的
     自定义 modal）："This will clear all current review data. Are you sure?"

5. **优化 Hero 区域文案**
   - 将当前偏技术性的 Hero 标题改为面向产品经理/工程 lead 的表述，例如：
     - 标题: "AI-Powered Requirement Review"
     - 副标题: "Submit your PRD, get structured findings, risks, and delivery insights — all in one workspace."
   - Hero 右侧面板改为简洁的 "Quick Start" 指引（1. Paste PRD → 2. Review → 3. Download report）。

6. （在D:\venvs\marrdp虚拟环境中）确保 `npm run build` 无报错。完成后提交到该分支。
7.评估是否可以进行合并和推送，如果可以就执行
```

---

### Phase 3: 导航、路由与布局升级

**分支名**: `frontend/phase3-navigation-and-layout`

```
请在本项目中新建一个分支 `frontend/phase3-navigation-and-layout`（基于前序分支合并后），
然后在该分支上完成以下导航与布局优化：

1. **安装 React Router**
   - 安装 `react-router-dom`。
   - 配置以下路由结构：
     - `/` — 首页（提交表单 + 历史列表）
     - `/run/:runId` — 某次 run 的详情页（进度 + 摘要 + Findings + Risks + Questions + Artifacts）

2. **添加顶部导航栏**
   创建 `src/components/Navbar.jsx`：
   - 左侧: 项目 Logo + 名称 "Review Workspace"
   - 右侧: 导航链接（Home, History）+ 未来预留的用户头像位置
   - 导航栏固定在顶部（sticky），有半透明模糊背景

3. **首页布局调整**
   - 左栏: 提交表单（ReviewSubmitPanel）
   - 右栏: 最近运行历史列表（ReviewHistoryPanel）
   - 移除当前首页中的 RunProgressCard、FindingsPanel 等详情组件，
     这些只在 `/run/:runId` 页面显示

4. **Run 详情页布局**
   - 顶部: 面包屑导航（Home > Run > {runId}）
   - 左栏: RunProgressCard + ArtifactDownloadPanel
   - 右栏: ReviewSummaryPanel + FindingsPanel + RisksPanel + OpenQuestionsPanel
   - 提交 review 成功后自动跳转到 `/run/{runId}`

5. **历史列表中点击 "Open" 跳转到 `/run/:runId`**，不再在同一页内切换。

6. 确保直接访问 `/run/:runId` URL 也能正确加载数据（从 URL 参数读取 runId 并请求 API）。

7.（在D:\venvs\marrdp虚拟环境中）确保 `npm run build` 无报错。完成后提交到该分支。
8. 评估是否可以进行合并和推送，如果可以就执行
```

---

### Phase 4: 视觉升级与暗色模式

**分支名**: `frontend/phase4-visual-upgrade`

```
请在本项目中新建一个分支 `frontend/phase4-visual-upgrade`（基于前序分支合并后），
然后在该分支上完成以下视觉升级：

1. **引入现代字体**
   - 在 `index.html` 中通过 Google Fonts 引入 `Inter`（正文）和 `DM Serif Display`（标题）。
   - 更新 CSS 变量中的 font-family：
     - 正文: `'Inter', system-ui, sans-serif`
     - 标题/h1-h4: `'DM Serif Display', Georgia, serif`

2. **添加 favicon**
   - 在 `public/` 或 `frontend/` 根目录添加一个简单的 SVG favicon（可用文字 "RW" 或
     一个审查图标）。
   - 在 `index.html` 中引用。

3. **实现暗色/亮色模式切换**
   - 新增 CSS 变量集 `[data-theme="dark"]`，覆盖 `--panel`、`--text-main`、`--bg-deep` 等。
   - 在 Navbar 中添加主题切换按钮（太阳/月亮图标）。
   - 使用 `localStorage` 持久化用户选择，默认跟随系统 `prefers-color-scheme`。
   - 暗色模式下 Panel 使用深色背景而非当前的米白色，避免与深色 Hero 区域割裂。

4. **优化颜色对比度**
   - 将 `--text-soft` 在亮色模式下调整为 `#3d5267`（确保 contrast ratio ≥ 4.5:1）。
   - 检查所有 severity badge、status badge 的前景/背景对比度，确保符合 WCAG AA。

5. **添加过渡动画**
   - Panel 进入时添加 `fadeInUp` 动画（opacity 0→1, translateY 12px→0, duration 300ms）。
   - 按钮 hover 添加微妙的 scale(1.02) + shadow 变化。
   - 状态切换（idle→running→completed）时 badge 颜色平滑过渡。

6. **进度条升级**
   - 将简单的水平进度条改为带步骤节点的 Stepper 组件：
     每个 pipeline node 显示为一个圆点，已完成的高亮，当前正在执行的有脉冲动画。
   - 保留百分比文字显示。

7.（在D:\venvs\marrdp虚拟环境中）确保 `npm run build` 无报错。完成后提交到该分支。
8.评估是否可以进行合并和推送，如果可以就执行
```

---

### Phase 5: 交互增强与通知系统

**分支名**: `frontend/phase5-interaction-and-notifications`

```
请在本项目中新建一个分支 `frontend/phase5-interaction-and-notifications`（基于前序分支合并后），
然后在该分支上完成以下交互增强：

1. **Toast 通知系统**
   创建 `src/components/ToastProvider.jsx`：
   - 使用 React Context 提供 `showToast(message, type)` 方法。
   - 支持类型: `success`、`error`、`info`、`warning`。
   - Toast 从右上角滑入，3 秒后自动消失，可手动关闭。
   - 在以下场景触发 Toast：
     - Review 提交成功: "Review submitted successfully. Tracking run {runId}."
     - 下载完成: "Report downloaded."
     - 轮询失败: "Status check failed. Retrying..."
     - Run 完成: "Run {runId} completed. Results are ready."
     - Run 失败: "Run {runId} failed."

2. **历史列表分页与搜索**
   - 将固定 8 条上限改为分页显示（每页 10 条，底部显示页码导航）。
   - 在历史列表顶部添加搜索框，支持按 run_id 过滤。
   - 添加状态筛选 Chip（All / Running / Completed / Failed），点击后过滤列表。

3. **Artifact 预览**
   - 在 ArtifactDownloadPanel 中，点击 artifact key 时展开一个内联预览区域：
     - Markdown 文件: 渲染为格式化内容（可使用 `react-markdown` 或简单的 `<pre>` 显示）。
     - JSON 文件: 格式化为缩进的 JSON 代码块。
   - 保留原有的"Download Markdown"和"Download JSON"按钮。

4. **键盘快捷键**
   - `Ctrl+Enter` / `Cmd+Enter`: 在表单焦点时提交 review。
   - `Escape`: 关闭预览 / 关闭 modal。

5. **添加基础无障碍支持**
   - 为所有按钮和交互元素添加合适的 `aria-label`。
   - 在状态变化时使用 `aria-live="polite"` 通知屏幕阅读器。
   - 确保 Tab 键可以遍历所有可操作元素。

6.（在D:\venvs\marrdp虚拟环境中）确保 `npm run build` 无报错。完成后提交到该分支。
7.评估是否可以进行合并和推送，如果可以就执行
```

---

### Phase 6: 性能优化与生产就绪

**分支名**: `frontend/phase6-performance-and-production`

```
请在本项目中新建一个分支 `frontend/phase6-performance-and-production`（基于前序分支合并后），
然后在该分支上完成以下性能与生产就绪优化：

1. **代码分割 (Code Splitting)**
   - 使用 `React.lazy` + `Suspense` 对 Run 详情页进行懒加载。
   - 首页仅加载提交表单和历史列表所需代码。

2. **状态管理升级**（可选，视复杂度决定）
   - 如果 prop drilling 已超过 3 层，引入 React Context 进行 workspace 状态管理：
     - 创建 `src/context/WorkspaceContext.jsx`，封装当前 `App` 中的
       `workspace` state 和相关操作方法（handleSubmit, handleDownload, pollRunStatus 等）。
     - 各子组件通过 `useWorkspace()` hook 消费，不再逐层传递 props。

3. **错误边界完善**
   - 在每个主要 Panel 外层包裹独立的 ErrorBoundary，使单个 Panel 崩溃不影响整体。
   - ErrorBoundary 显示友好的"该模块加载失败"提示和"重试"按钮。

4. **SEO 与 Meta 信息**
   - 在 `index.html` 中添加 `<meta name="description">`, `<meta name="theme-color">`。
   - 添加 Open Graph 标签（`og:title`, `og:description`）以便分享时显示预览。

5. **构建优化**
   - 在 `vite.config.js` 中配置 `build.rollupOptions.output.manualChunks`，
     将 `react` 和 `react-dom` 分离到 vendor chunk。
   - 确认 production build 体积合理（目标: 初始加载 < 200KB gzipped）。

6. **添加基础 E2E 冒烟测试**（可选）
   - 使用 Playwright 或 Cypress 编写 1-2 个冒烟测试：
     - 首页可以正常渲染。
     - 填写表单并提交不会抛出前端错误（mock API 响应）。

7.（在D:\venvs\marrdp虚拟环境中）确保 `npm run build` 无报错。完成后提交到该分支。
8.评估是否可以进行合并和推送，如果可以就执行
```

---

## 执行顺序建议

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4 ──→ Phase 5 ──→ Phase 6
 架构修复    文案与表单    导航与路由    视觉升级    交互增强    性能与生产
```

- **Phase 1-2** 是基础优化，建议优先完成并合并。
- **Phase 3** 是结构性变更，完成后用户体验会有质的提升。
- **Phase 4-5** 是体验打磨，可并行开发（不同开发者）。
- **Phase 6** 是上线前的最终准备。

每个 Phase 完成后，通过 PR review 合并到主分支，再开始下一个 Phase。
