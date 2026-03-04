# Requirement Review v1 MCP 接入指南

本文档目标：让一个全新客户端从 0 到 1 调通本仓库 MCP Server（stdio），并成功调用 `review_prd` 与 `get_report`。

## 1. 前置条件

- Python 3.11+
- 已在环境中配置模型 API Key（至少 `OPENAI_API_KEY`）
- 在仓库根目录执行以下命令

仓库根目录示例：

```powershell
cd "d:\Backup\Career\Campus Recruitment Projects\Personal AI Agent Project\Multi-Agent-Requirement-Review-and-Delivery-Planning-System"
```

## 2. 安装依赖

推荐使用虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果你更偏好 editable 安装，也可以：

```powershell
pip install -e .
```

## 3. 启动 MCP Server（stdio）

本项目 MCP Server 入口：`requirement_review_v1.mcp_server.server`

```powershell
python -m requirement_review_v1.mcp_server.server
```

说明：
- 这是 stdio transport，通常由 MCP client 进程拉起。
- 手工直接运行时会等待 MCP 消息输入，这属于正常现象。

## 4. Claude Desktop 配置示例（本地 `python -m` 启动）

把以下配置加入 Claude Desktop 的 `claude_desktop_config.json`（Windows 常见路径：`%APPDATA%\Claude\claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "requirement-review-v1": {
      "command": "D:/.../Multi-Agent-Requirement-Review-and-Delivery-Planning-System/.venv/Scripts/python.exe",
      "args": [
        "-m",
        "requirement_review_v1.mcp_server.server"
      ],
      "cwd": "D:/.../Multi-Agent-Requirement-Review-and-Delivery-Planning-System",
      "env": {
        "OPENAI_API_KEY": "<YOUR_API_KEY>"
      }
    }
  }
}
```

注意：
- `command` 建议写虚拟环境里的 `python.exe` 绝对路径。
- `cwd` 建议写仓库根目录绝对路径。
- 配置后重启 Claude Desktop。

## 5. Cursor 或通用 MCP Client 调用方式

### 5.1 Cursor（若当前版本支持 MCP）

如果你的 Cursor 版本提供 MCP 配置入口，使用与 Claude 相同的 stdio 参数即可：

- `command`: 本地 Python 可执行文件
- `args`: `-m requirement_review_v1.mcp_server.server`
- `cwd`: 仓库根目录
- `env`: 至少包含 `OPENAI_API_KEY`

### 5.2 通用 MCP Client（Python SDK 方式）

仓库提供了可执行示例脚本：`scripts/mcp_demo.py`

```powershell
python scripts/mcp_demo.py --prd-file examples/example_prd_app_feature.md
```

脚本会自动：
1. 通过 stdio 拉起 `python -m requirement_review_v1.mcp_server.server`
2. 调用 `review_prd`
3. 读取 `run_id` 后调用 `get_report`

## 6. 端到端演示

### 6.1 一条命令跑通

```powershell
python scripts/mcp_demo.py --prd-file examples/example_prd_app_feature.md --report-format md --report-limit 1500
```

成功时你会看到：
- `review_prd` 返回的 `run_id`、`metrics`、`artifacts`
- `get_report` 返回的报告内容片段

### 6.2 常用参数

```powershell
python scripts/mcp_demo.py --help
```

关键参数：
- `--prd-file`: PRD 文件路径（与 `--prd-text` 二选一）
- `--prd-text`: 直接传 PRD 文本
- `--outputs-root`: 输出目录（默认 `outputs`）
- `--report-format`: `md` 或 `json`
- `--report-limit`: 读取 markdown 报告的最大字符数
- `--timeout-seconds`: 单次工具调用超时（默认 600 秒）

## 7. 已暴露工具

- `ping`: 连通性检查
- `review_prd`: 发起 PRD 审查，返回 `run_id`/指标/产物路径
- `get_report`: 通过 `run_id` 获取 `md/json` 报告内容

## 8. 常见问题

1. `ModuleNotFoundError: mcp`
   - 说明当前 Python 环境未安装依赖，请重新执行“安装依赖”。

2. `error.code = invalid_run_id`（调用 `get_report`）
   - `run_id` 必须是 `YYYYMMDDTHHMMSSZ` 格式，建议直接使用 `review_prd` 返回值。

3. 模型调用失败
   - 检查 `OPENAI_API_KEY` 是否在当前进程环境中可见（Claude/Cursor 配置里的 `env` 也要设置）。
