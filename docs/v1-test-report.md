# V1 需求评审管线 — 测试报告

> 测试日期：2026-02-22
> 分支：`feature/requirement-review-v1`
> 运行 ID：`20260222T134713Z`

---

## 一、测试范围

本次测试覆盖 `requirement_review_v1` 模块全部 3 个 agent 节点和完整 LangGraph 管线。

| 组件 | 文件 | 测试内容 |
|------|------|----------|
| Parser Agent | `agents/parser_agent.py` | 需求文档 → 结构化拆解 |
| Reviewer Agent | `agents/reviewer_agent.py` | 结构化需求 → 清晰度/可测试性/歧义性评审 |
| Reporter Agent | `agents/reporter_agent.py` | 评审结果 → Markdown 报告 + 风险等级 |
| Workflow | `workflow.py` | LangGraph 图编排：parser → reviewer → reporter → END |
| CLI 入口 | `main.py` | 端到端运行 + 输出持久化 |

---

## 二、测试环境

| 项目 | 值 |
|------|----|
| Python | 3.10.4 |
| LLM 模型 | `gpt-4.1` (OpenAI) |
| LLM Provider | `openai` via `gpt_researcher.utils.llm.create_chat_completion` |
| 关键依赖 | `langgraph>=0.2.76`, `langchain-core>=1.0.0`, `json-repair>=0.29.8` |
| 代理 | `http://127.0.0.1:7897`（本地 Clash 代理） |

---

## 三、测试输入

使用样例需求文档 `docs/sample_prd.md`，包含 5 条原始需求：

```markdown
# Sample PRD — User Management Module

## 1. User Registration
The system shall allow users to register with email and password.
- Passwords must be at least 8 characters with one uppercase letter and one digit.
- A confirmation email must be sent within 30 seconds of registration.

## 2. Login
The system should provide a fast and user-friendly login experience.

## 3. Account Deactivation
Admin users shall be able to deactivate any user account, and the change must take effect immediately.

## 4. Password Reset
Users should be able to reset their password easily through a self-service flow.

## 5. Audit Logging
All authentication events must be logged for compliance purposes, with appropriate detail.
```

---

## 四、测试过程与结果

### 4.1 单节点测试：Parser Agent

**命令：**

```bash
python -m requirement_review_v1.debug --agent parser
```

**结果：** ✅ 通过

Parser 将 5 条原始需求拆解为 **7 条结构化需求项**（REQ-001 ~ REQ-007），每条包含 `id`、`description`、`acceptance_criteria`。

<details>
<summary>Parser 输出（parsed_items）</summary>

```json
[
  {
    "id": "REQ-001",
    "description": "The system shall allow users to register with email and password.",
    "acceptance_criteria": [
      "Users can submit a registration form with email and password fields.",
      "Registration is successful only if both email and password are provided."
    ]
  },
  {
    "id": "REQ-002",
    "description": "Passwords must be at least 8 characters with one uppercase letter and one digit.",
    "acceptance_criteria": [
      "Password is rejected if it is less than 8 characters.",
      "Password is rejected if it does not contain at least one uppercase letter.",
      "Password is rejected if it does not contain at least one digit.",
      "Registration is successful only if password meets all criteria."
    ]
  },
  {
    "id": "REQ-003",
    "description": "A confirmation email must be sent within 30 seconds of registration.",
    "acceptance_criteria": [
      "A confirmation email is sent to the user's email address after successful registration.",
      "The confirmation email is sent within 30 seconds of registration completion."
    ]
  },
  {
    "id": "REQ-004",
    "description": "The system should provide a fast and user-friendly login experience.",
    "acceptance_criteria": [
      "Login page loads in under 2 seconds on standard broadband.",
      "Users can log in with valid credentials in under 5 seconds.",
      "Error messages are clear and actionable when login fails."
    ]
  },
  {
    "id": "REQ-005",
    "description": "Admin users shall be able to deactivate any user account, and the change must take effect immediately.",
    "acceptance_criteria": [
      "Admin users can select and deactivate any user account from the admin interface.",
      "Deactivated users are immediately unable to log in or access the system.",
      "Deactivation takes effect within 5 seconds of admin action."
    ]
  },
  {
    "id": "REQ-006",
    "description": "Users should be able to reset their password easily through a self-service flow.",
    "acceptance_criteria": [
      "Users can initiate password reset from the login page.",
      "Users receive a password reset email with a secure link.",
      "Users can set a new password using the link without admin intervention."
    ]
  },
  {
    "id": "REQ-007",
    "description": "All authentication events must be logged for compliance purposes, with appropriate detail.",
    "acceptance_criteria": [
      "Each login, logout, registration, password reset, and account deactivation event is logged.",
      "Logs include timestamp, user identifier, event type, and source IP address.",
      "Logs are stored securely and are accessible to authorized personnel for compliance review."
    ]
  }
]
```

</details>

### 4.2 单节点测试：Reviewer Agent

**命令：**

```bash
python -m requirement_review_v1.debug --agent reviewer
```

**结果：** ✅ 通过

Reviewer 对每条需求从 **清晰度（Clarity）**、**可测试性（Testability）**、**歧义性（Ambiguity）** 三个维度进行评审，并给出具体问题和改进建议。

<details>
<summary>Reviewer 输出（review_results）</summary>

```json
[
  {
    "id": "REQ-001",
    "is_clear": true,
    "is_testable": true,
    "is_ambiguous": false,
    "issues": [],
    "suggestions": ""
  },
  {
    "id": "REQ-002",
    "is_clear": true,
    "is_testable": true,
    "is_ambiguous": false,
    "issues": [],
    "suggestions": ""
  },
  {
    "id": "REQ-003",
    "is_clear": true,
    "is_testable": true,
    "is_ambiguous": false,
    "issues": [],
    "suggestions": ""
  },
  {
    "id": "REQ-004",
    "is_clear": false,
    "is_testable": false,
    "is_ambiguous": true,
    "issues": [
      "The terms 'fast' and 'user-friendly' are subjective and open to interpretation.",
      "Acceptance criteria for 'user-friendly' are not defined.",
      "Performance criteria depend on 'standard broadband', which is not precisely defined."
    ],
    "suggestions": "Replace vague terms with measurable criteria. Define 'user-friendly' with specific usability metrics or user satisfaction targets. Specify the bandwidth for 'standard broadband' (e.g., 25 Mbps download speed)."
  },
  {
    "id": "REQ-005",
    "is_clear": true,
    "is_testable": true,
    "is_ambiguous": false,
    "issues": [],
    "suggestions": ""
  },
  {
    "id": "REQ-006",
    "is_clear": false,
    "is_testable": true,
    "is_ambiguous": true,
    "issues": [
      "The term 'easily' is subjective and not defined."
    ],
    "suggestions": "Remove or define 'easily' with measurable usability criteria, such as the number of steps required or average completion time for the password reset process."
  },
  {
    "id": "REQ-007",
    "is_clear": false,
    "is_testable": true,
    "is_ambiguous": true,
    "issues": [
      "The phrase 'appropriate detail' is vague and open to interpretation."
    ],
    "suggestions": "Specify what constitutes 'appropriate detail' in the requirement description, or remove the phrase if the acceptance criteria already define the required log details."
  }
]
```

</details>

### 4.3 端到端测试：完整管线

**命令：**

```bash
python -m requirement_review_v1.main --input docs/sample_prd.md
```

**结果：** ✅ 通过

三个节点依次执行 parser → reviewer → reporter，成功生成 Markdown 报告，并将所有输出持久化到 `outputs/20260222T134713Z/` 目录。

**输出文件：**

| 文件 | 内容 | 大小 |
|------|------|------|
| `report.md` | 人类可读的 Markdown 评审报告 | 4,857 字符 |
| `report.json` | 完整 state 快照（含所有中间结果） | — |
| `run_trace.json` | 各节点耗时追踪 | — |

---

## 五、性能数据

| 节点 | 耗时 | 输出量 |
|------|------|--------|
| Parser Agent | 9.534s | 7 条结构化需求 |
| Reviewer Agent | 5.088s | 7 条评审结果 |
| Reporter Agent | ~0s | 4,857 字符 Markdown 报告 |
| **总计** | **~14.6s** | — |

---

## 六、生成报告内容

### 6.1 需求列表

| ID | Description | Acceptance Criteria |
|----|-------------|---------------------|
| REQ-001 | The system shall allow users to register with email and password. | Users can submit a registration form with email and password fields.; Registration is successful only if both email and password are provided. |
| REQ-002 | Passwords must be at least 8 characters with one uppercase letter and one digit. | Password is rejected if it is less than 8 characters.; Password is rejected if it does not contain at least one uppercase letter.; Password is rejected if it does not contain at least one digit.; Registration is successful only if password meets all criteria. |
| REQ-003 | A confirmation email must be sent within 30 seconds of registration. | A confirmation email is sent to the user's email address after successful registration.; The confirmation email is sent within 30 seconds of registration completion. |
| REQ-004 | The system should provide a fast and user-friendly login experience. | Login page loads in under 2 seconds on standard broadband.; Users can log in with valid credentials in under 5 seconds.; Error messages are clear and actionable when login fails. |
| REQ-005 | Admin users shall be able to deactivate any user account, and the change must take effect immediately. | Admin users can select and deactivate any user account from the admin interface.; Deactivated users are immediately unable to log in or access the system.; Deactivation takes effect within 5 seconds of admin action. |
| REQ-006 | Users should be able to reset their password easily through a self-service flow. | Users can initiate password reset from the login page.; Users receive a password reset email with a secure link.; Users can set a new password using the link without admin intervention. |
| REQ-007 | All authentication events must be logged for compliance purposes, with appropriate detail. | Each login, logout, registration, password reset, and account deactivation event is logged.; Logs include timestamp, user identifier, event type, and source IP address.; Logs are stored securely and are accessible to authorized personnel for compliance review. |

### 6.2 评审详情

#### REQ-001 — User Registration

- **Clear:** ✅ Yes | **Testable:** ✅ Yes | **Ambiguous:** ✅ No
- **Risk Level:** 🟢 Low
- **Issues:** None

#### REQ-002 — Password Validation

- **Clear:** ✅ Yes | **Testable:** ✅ Yes | **Ambiguous:** ✅ No
- **Risk Level:** 🟢 Low
- **Issues:** None

#### REQ-003 — Confirmation Email

- **Clear:** ✅ Yes | **Testable:** ✅ Yes | **Ambiguous:** ✅ No
- **Risk Level:** 🟢 Low
- **Issues:** None

#### REQ-004 — Login Experience

- **Clear:** ❌ No | **Testable:** ❌ No | **Ambiguous:** ❌ Yes
- **Risk Level:** 🔴 High
- **Issues:**
  - "fast" and "user-friendly" are subjective
  - Acceptance criteria for "user-friendly" are not defined
  - "standard broadband" is not precisely defined
- **Suggestions:** Replace vague terms with measurable criteria; define usability metrics; specify bandwidth

#### REQ-005 — Account Deactivation

- **Clear:** ✅ Yes | **Testable:** ✅ Yes | **Ambiguous:** ✅ No
- **Risk Level:** 🟢 Low
- **Issues:** None

#### REQ-006 — Password Reset

- **Clear:** ❌ No | **Testable:** ✅ Yes | **Ambiguous:** ❌ Yes
- **Risk Level:** 🔴 High
- **Issues:**
  - "easily" is subjective and not defined
- **Suggestions:** Define "easily" with measurable usability criteria (e.g., steps count, completion time)

#### REQ-007 — Audit Logging

- **Clear:** ❌ No | **Testable:** ✅ Yes | **Ambiguous:** ❌ Yes
- **Risk Level:** 🔴 High
- **Issues:**
  - "appropriate detail" is vague and open to interpretation
- **Suggestions:** Specify what constitutes "appropriate detail" explicitly

### 6.3 风险汇总

| Risk Level | Count | Percentage |
|------------|-------|------------|
| 🔴 High | 3 | 43% |
| 🟡 Medium | 0 | 0% |
| 🟢 Low | 4 | 57% |

---

## 七、问题与修复记录

| # | 问题 | 原因 | 修复方式 |
|---|------|------|----------|
| 1 | `pip install` 失败，SSL/Proxy 报错 | Windows 系统代理配置 HTTPS 协议为 `https://`，导致 TLS 握手失败 | 显式设置 `HTTPS_PROXY=http://127.0.0.1:7897` |
| 2 | LLM 调用返回 `Connection error` | 同上，`httpx` 自动读取了 Windows 系统代理设置 | 在 `.env` 中添加 `HTTP_PROXY` 和 `HTTPS_PROXY` |
| 3 | PowerShell 终端 emoji 乱码 | Windows 终端 GBK 编码不支持 UTF-8 emoji | 文件内容正常，仅终端显示问题，不影响功能 |

---

## 八、结论

| 测试项 | 状态 |
|--------|------|
| Parser Agent 单独运行 | ✅ 通过 |
| Reviewer Agent 单独运行 | ✅ 通过 |
| Reporter Agent（随完整管线测试） | ✅ 通过 |
| LangGraph Workflow 编排 | ✅ 通过 |
| CLI 入口 + 输出持久化 | ✅ 通过 |
| 报告内容质量 | ✅ 评审维度准确，高风险需求识别正确 |

**V1 需求评审管线全部功能测试通过，可进入下一阶段开发。**
