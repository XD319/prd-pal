import { useState } from "react";

import { ActivityLogPanel } from "./components/ActivityLogPanel";
import { HistoryPanel } from "./components/HistoryPanel";
import { InputPanel } from "./components/InputPanel";
import { ReportPanel } from "./components/ReportPanel";
import { RunStatusPanel } from "./components/RunStatusPanel";
import { SAMPLE_PRD } from "./constants";
import { useHistory } from "./hooks/useHistory";
import { useLogs } from "./hooks/useLogs";
import { useReviewRun } from "./hooks/useReviewRun";

function App() {
  const [mode, setMode] = useState("text");
  const [prdText, setPrdText] = useState("");
  const [prdPath, setPrdPath] = useState("");

  const { appendLog, clearLogs, logs } = useLogs();
  const { addHistoryItem, clearHistory, history } = useHistory();
  const {
    errorMessage,
    formError,
    isSubmitting,
    openHistory,
    progress,
    reportMarkdown,
    reportMessage,
    runId,
    status,
    statusLabel,
    stopListening,
    submitReview,
    transportLabel,
  } = useReviewRun({
    mode,
    prdPath,
    prdText,
    appendLog,
    addHistoryItem,
  });

  const statusClass = ["status-badge", status].join(" ");

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
        <InputPanel
          errorMessage={errorMessage}
          formError={formError}
          isSubmitting={isSubmitting}
          mode={mode}
          onModeChange={setMode}
          onPrdPathChange={setPrdPath}
          onPrdTextChange={setPrdText}
          onStopListening={() => stopListening(true)}
          onSubmit={submitReview}
          prdPath={prdPath}
          prdText={prdText}
          statusClass={statusClass}
          statusLabel={statusLabel}
        />

        <RunStatusPanel progress={progress} runId={runId} transportLabel={transportLabel} />
        <ActivityLogPanel logs={logs} onClear={clearLogs} />
        <ReportPanel reportMarkdown={reportMarkdown} reportMessage={reportMessage} runId={runId} />
        <HistoryPanel history={history} onClear={clearHistory} onOpen={openHistory} />
      </main>
    </div>
  );
}

export default App;
