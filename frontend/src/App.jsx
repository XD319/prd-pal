import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const TRACKED_NODES = ["parser", "clarify", "planner", "risk", "reviewer", "route_decider", "reporter"];
const HISTORY_KEY = "requirement-review-history";
const TERMINAL_STATUSES = new Set(["completed", "failed"]);
const SAMPLE_PRD = `# 校园招聘多 Agent 需求评审系统

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

function App() {
  const [mode, setMode] = useState("text");
  const [prdText, setPrdText] = useState("");
  const [prdPath, setPrdPath] = useState("");
  const [status, setStatus] = useState("idle");
  const [statusLabel, setStatusLabel] = useState("Idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runId, setRunId] = useState("");
  const [transportLabel, setTransportLabel] = useState("Idle");
  const [progress, setProgress] = useState({ percent: 0, current_node: "等待提交", nodes: {}, updated_at: "" });
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [reportMessage, setReportMessage] = useState("任务完成后，这里会显示报告预览和下载入口。");
  const [history, setHistory] = useState(() => loadHistory());
  const [logs, setLogs] = useState([{ stamp: formatTime(new Date()), message: "系统已就绪，等待提交任务。" }]);
  const pollRef = useRef(null);
  const wsRef = useRef(null);
  const transportRef = useRef("idle");
  const latestStatusRef = useRef("idle");
  const activeRunIdRef = useRef("");
  const loadedReportRunRef = useRef("");
  const listeningRef = useRef(false);

  const nodeCards = useMemo(() => {
    return TRACKED_NODES.map((nodeName) => ({
      name: nodeName,
      ...(progress.nodes?.[nodeName] ?? { status: "pending", runs: 0 }),
    }));
  }, [progress.nodes]);

  useEffect(() => {
    return () => {
      stopPolling(false);
      stopWebSocket(false);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, 8)));
  }, [history]);

  function appendLog(message) {
    setLogs((current) => {
      const last = current[current.length - 1];
      if (last?.message === message) {
        return current;
      }
      return [...current, { stamp: formatTime(new Date()), message }];
    });
  }

  function resetRunView() {
    stopPolling(false);
    stopWebSocket(false);
    setRunId("");
    setTransportLabel("Idle");
    transportRef.current = "idle";
    activeRunIdRef.current = "";
    loadedReportRunRef.current = "";
    setProgress({ percent: 0, current_node: "等待提交", nodes: {}, updated_at: "" });
    setReportMarkdown("");
    setReportMessage("任务完成后，这里会显示报告预览和下载入口。");
  }

  function stopPolling(shouldLog = true) {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
      if (shouldLog) {
        appendLog("已停止轮询。" );
      }
    }
  }

  function stopWebSocket(shouldLog = true) {
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      ws.close();
      if (shouldLog) {
        appendLog("WebSocket 已关闭。");
      }
    }
  }

  function setTransport(nextTransport) {
    transportRef.current = nextTransport;
    setTransportLabel(
      nextTransport === "websocket"
        ? "WebSocket"
        : nextTransport === "polling"
          ? "Polling"
          : "Idle"
    );
  }

  function applyStatusPayload(data, source) {
    const nextProgress = data.progress ?? {};
    const nextStatus = data.status || "idle";
    latestStatusRef.current = nextStatus;
    setProgress({
      percent: Number(nextProgress.percent ?? 0),
      current_node: nextProgress.current_node || "等待执行",
      nodes: nextProgress.nodes || {},
      updated_at: nextProgress.updated_at || "",
    });
    setStatus(nextStatus);
    setStatusLabel(nextStatus === "missing" ? "Missing" : nextStatus);

    if (nextProgress.error) {
      appendLog(`错误: ${nextProgress.error}`);
    } else {
      appendLog(`状态更新(${source}): ${nextStatus} / ${nextProgress.percent ?? 0}% / ${nextProgress.current_node || "等待执行"}`);
    }

    if (TERMINAL_STATUSES.has(nextStatus)) {
      setIsSubmitting(false);
      listeningRef.current = false;
      setTransport("idle");
      stopPolling(false);
      stopWebSocket(false);
      void loadReport(data.run_id);
    }
  }

  function startPolling(nextRunId, reason = "") {
    stopPolling(false);
    setTransport("polling");
    if (reason) {
      appendLog(reason);
    }
    void pollStatus(nextRunId, "polling");
    pollRef.current = window.setInterval(() => {
      void pollStatus(nextRunId, "polling");
    }, 2000);
  }

  function connectWebSocket(nextRunId) {
    stopWebSocket(false);
    const socket = new WebSocket(buildWebSocketUrl(nextRunId));
    wsRef.current = socket;
    setTransportLabel("Connecting");

    socket.onopen = () => {
      setTransport("websocket");
      appendLog("WebSocket 已连接，切换到实时推送。" );
    };

    socket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      applyStatusPayload(payload, "websocket");
    };

    socket.onerror = () => {
      appendLog("WebSocket 连接异常，准备回退到轮询。" );
    };

    socket.onclose = () => {
      if (wsRef.current === socket) {
        wsRef.current = null;
      }
      if (!TERMINAL_STATUSES.has(latestStatusRef.current) && activeRunIdRef.current === nextRunId && listeningRef.current) {
        startPolling(nextRunId, "WebSocket 已断开，已回退到轮询。" );
      }
    };
  }

  async function pollStatus(targetRunId, source = "polling") {
    try {
      const response = await fetch(`/api/review/${encodeURIComponent(targetRunId)}`);
      if (!response.ok) {
        throw new Error(await readError(response));
      }
      const data = await response.json();
      applyStatusPayload(data, source);
    } catch (error) {
      appendLog(`轮询失败: ${error.message}`);
      setStatus("failed");
      setStatusLabel("Polling error");
      setTransport("idle");
      stopPolling(false);
      setIsSubmitting(false);
      listeningRef.current = false;
    }
  }

  async function loadReport(targetRunId) {
    if (!targetRunId || loadedReportRunRef.current === targetRunId) {
      return;
    }
    try {
      const response = await fetch(`/api/report/${encodeURIComponent(targetRunId)}?format=md`);
      if (!response.ok) {
        throw new Error(await readError(response));
      }
      const markdown = await response.text();
      loadedReportRunRef.current = targetRunId;
      setReportMessage("报告已生成，可直接在线预览，也可以下载 Markdown 或 JSON 原始结果。");
      setReportMarkdown(markdown);
    } catch (error) {
      setReportMessage(`报告生成完成，但预览拉取失败：${error.message}`);
      setReportMarkdown("");
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const payload = mode === "text" ? { prd_text: prdText.trim() } : { prd_path: prdPath.trim() };
    const value = mode === "text" ? payload.prd_text : payload.prd_path;
    if (!value) {
      appendLog(mode === "text" ? "请输入 PRD 文本后再提交。" : "请输入 PRD 文件路径后再提交。");
      return;
    }

    setStatus("running");
    setStatusLabel("Queued");
    setIsSubmitting(true);
    resetRunView();
    appendLog("正在创建评审任务...");

    try {
      const response = await fetch("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(await readError(response));
      }
      const data = await response.json();
      setRunId(data.run_id);
      activeRunIdRef.current = data.run_id;
      setIsSubmitting(true);
      appendLog(`任务已创建: ${data.run_id}`);
      setHistory((current) => {
        const summary = mode === "text" ? firstLine(prdText.trim()) || "PRD text" : prdPath.trim();
        return [{ runId: data.run_id, mode, summary, createdAt: new Date().toISOString() }, ...current].slice(0, 8);
      });
      connectWebSocket(data.run_id);
      window.setTimeout(() => {
        if (transportRef.current !== "websocket" && activeRunIdRef.current === data.run_id && listeningRef.current) {
          startPolling(data.run_id, "实时连接尚未建立，已使用轮询兜底。" );
        }
      }, 2500);
    } catch (error) {
      setStatus("failed");
      setStatusLabel("Failed");
      setIsSubmitting(false);
      listeningRef.current = false;
      appendLog(`创建任务失败: ${error.message}`);
    }
  }

  async function openHistory(item) {
    activeRunIdRef.current = item.runId;
    setRunId(item.runId);
    setStatus("running");
    setStatusLabel("History");
    loadedReportRunRef.current = "";
    appendLog(`已切换到历史任务 ${item.runId}。`);
    await pollStatus(item.runId, "history");
    if (!TERMINAL_STATUSES.has(latestStatusRef.current)) {
      setIsSubmitting(true);
      connectWebSocket(item.runId);
      window.setTimeout(() => {
        if (transportRef.current !== "websocket" && activeRunIdRef.current === item.runId && !TERMINAL_STATUSES.has(latestStatusRef.current)) {
          startPolling(item.runId, "历史任务实时连接失败，已回退到轮询。" );
        }
      }, 2500);
    } else {
      await loadReport(item.runId);
    }
  }

  const statusClass = ["status-badge", status].join(" ");
  const updatedAtLabel = progress.updated_at ? formatDate(progress.updated_at) : "-";
  const downloadBase = runId ? `/api/report/${encodeURIComponent(runId)}` : "#";

  return (
    <div className="page-shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Requirement Review V2</p>
          <h1>从 PRD 输入到评审报告，一页完成。</h1>
          <p className="hero-text">
            现在前端已经切到 React 组件化结构，保留旧版 GPT Researcher 的大面板体验，
            但状态管理、历史记录和运行区块都更容易继续演进。
          </p>
          <div className="hero-actions">
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => {
                setMode("text");
                setPrdText(SAMPLE_PRD);
                appendLog("已填充示例 PRD。");
              }}
            >
              填充示例 PRD
            </button>
            <a className="btn btn-ghost" href="#workspace">开始使用</a>
          </div>
        </div>
        <div className="hero-panel">
          <div className="hero-card">
            <span className="hero-card-label">优化后结构</span>
            <ul>
              <li>React 组件化布局与状态管理</li>
              <li>按运行态切换提交、轮询、历史回看</li>
              <li>WebSocket 实时进度 + 轮询兜底</li>
              <li>报告预览与下载分区清晰</li>
            </ul>
          </div>
        </div>
      </header>

      <main id="workspace" className="workspace">
        <section className="panel input-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Submit Review</p>
              <h2>发起需求评审</h2>
            </div>
            <div className={statusClass}>{statusLabel}</div>
          </div>

          <div className="input-mode-switch" role="tablist" aria-label="Input mode">
            <button className={`mode-btn ${mode === "text" ? "active" : ""}`} type="button" onClick={() => setMode("text")}>PRD 文本</button>
            <button className={`mode-btn ${mode === "path" ? "active" : ""}`} type="button" onClick={() => setMode("path")}>文件路径</button>
          </div>

          <form className="review-form" onSubmit={handleSubmit}>
            {mode === "text" ? (
              <div>
                <label className="field-label" htmlFor="prdText">PRD 内容</label>
                <textarea id="prdText" className="field-input field-textarea" value={prdText} onChange={(event) => setPrdText(event.target.value)} placeholder="# PRD\n\n背景：...\n目标：...\n验收标准：..." />
              </div>
            ) : (
              <div>
                <label className="field-label" htmlFor="prdPath">PRD 文件路径</label>
                <input id="prdPath" className="field-input" type="text" value={prdPath} onChange={(event) => setPrdPath(event.target.value)} placeholder="例如：docs/sample_prd.md" />
              </div>
            )}

            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={isSubmitting}>{isSubmitting ? "任务已提交" : "开始评审"}</button>
              {isSubmitting ? (
                <button className="btn btn-secondary" type="button" onClick={() => { stopPolling(true); stopWebSocket(true); setIsSubmitting(false); setTransport("idle"); }}>
                  停止监听
                </button>
              ) : null}
            </div>
          </form>
        </section>

        <section className="panel progress-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Run Status</p>
              <h2>执行进度</h2>
            </div>
            <div className="run-meta">
              <span>{`run_id: ${runId || "-"}`}</span>
              <span>{`更新时间: ${updatedAtLabel}`}</span>
              <span>{`连接方式: ${transportLabel}`}</span>
            </div>
          </div>

          <div className="progress-meter">
            <div className="progress-meter-bar">
              <div className="progress-meter-fill" style={{ width: `${progress.percent}%` }} />
            </div>
            <div className="progress-meter-info">
              <strong>{progress.percent}%</strong>
              <span>{`当前节点: ${progress.current_node || "等待提交"}`}</span>
            </div>
          </div>

          <div className="node-grid">
            {nodeCards.map((node) => (
              <div className={`node-card ${node.status || "pending"}`} key={node.name}>
                <h3>{node.name}</h3>
                <p>{`状态: ${node.status || "pending"}`}</p>
                <p>{`运行次数: ${node.runs || 0}`}</p>
              </div>
            ))}
          </div>

          <div className="activity-log-wrap">
            <div className="subsection-header">
              <h3>运行日志</h3>
              <button className="link-btn" type="button" onClick={() => { setLogs([]); appendLog("日志已清空。"); }}>清空</button>
            </div>
            <div className="activity-log">
              {logs.map((entry, index) => (
                <div className="log-entry" key={`${entry.stamp}-${index}`}>
                  <span className="log-time">[{entry.stamp}]</span>
                  {` ${entry.message}`}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel report-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Review Report</p>
              <h2>报告输出</h2>
            </div>
            <div className="report-actions">
              <a className={`btn btn-ghost ${runId ? "" : "disabled"}`} href={`${downloadBase}?format=md`} target="_blank" rel="noreferrer">Markdown</a>
              <a className={`btn btn-ghost ${runId ? "" : "disabled"}`} href={`${downloadBase}?format=json`} target="_blank" rel="noreferrer">JSON</a>
            </div>
          </div>

          <div className="report-summary">
            <p>{reportMessage}</p>
          </div>
          <article className={`report-preview markdown-body ${reportMarkdown ? "" : "empty"}`}>
            {reportMarkdown ? (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
                }}
              >
                {reportMarkdown}
              </ReactMarkdown>
            ) : (
              <p>暂无预览。</p>
            )}
          </article>
        </section>

        <aside className="panel history-panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">History</p>
              <h2>最近运行</h2>
            </div>
            <button className="link-btn" type="button" onClick={() => { setHistory([]); appendLog("历史记录已清空。"); }}>清空历史</button>
          </div>
          <div className="history-list">
            {history.length ? history.map((item) => (
              <button className="history-item" type="button" key={`${item.runId}-${item.createdAt}`} onClick={() => void openHistory(item)}>
                <span className="history-item-title">{truncate(item.summary, 48)}</span>
                <span className="history-item-meta">{`${item.mode.toUpperCase()} · ${item.runId} · ${formatDate(item.createdAt)}`}</span>
              </button>
            )) : <div className="empty-state">还没有历史运行记录。</div>}
          </div>
        </aside>
      </main>
    </div>
  );
}

function loadHistory() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function buildWebSocketUrl(runId) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/review/${encodeURIComponent(runId)}`;
}

function firstLine(value) {
  return value.split("\n").find((line) => line.trim()) ?? "";
}

async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || response.statusText;
  } catch {
    return response.statusText;
  }
}

function truncate(value, maxLength) {
  if (!value || value.length <= maxLength) {
    return value;
  }
  return `${value.slice(0, maxLength - 1)}...`;
}

function formatDate(value) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false });
}

function formatTime(date) {
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

export default App;



