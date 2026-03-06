import { useEffect, useRef, useState } from "react";

import { buildWebSocketUrl, createReview, getReportMarkdown, getReviewStatus } from "../api";
import { DEFAULT_PROGRESS, DEFAULT_REPORT_MESSAGE, POLL_INTERVAL_MS, TERMINAL_STATUSES, WEBSOCKET_FALLBACK_TIMEOUT_MS } from "../constants";
import { firstLine } from "../utils";

export function useReviewRun({ mode, prdPath, prdText, appendLog, addHistoryItem }) {
  const [status, setStatus] = useState("idle");
  const [statusLabel, setStatusLabel] = useState("Idle");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runId, setRunId] = useState("");
  const [transportLabel, setTransportLabel] = useState("Idle");
  const [progress, setProgress] = useState(DEFAULT_PROGRESS);
  const [reportMarkdown, setReportMarkdown] = useState("");
  const [reportMessage, setReportMessage] = useState(DEFAULT_REPORT_MESSAGE);
  const [formError, setFormError] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const pollRef = useRef(null);
  const wsRef = useRef(null);
  const fallbackTimeoutRef = useRef(null);
  const transportRef = useRef("idle");
  const latestStatusRef = useRef("idle");
  const activeRunIdRef = useRef("");
  const loadedReportRunRef = useRef("");
  const listeningRef = useRef(false);

  function clearFallbackTimeout() {
    if (fallbackTimeoutRef.current) {
      window.clearTimeout(fallbackTimeoutRef.current);
      fallbackTimeoutRef.current = null;
    }
  }

  function stopPolling(shouldLog = true) {
    if (pollRef.current) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
      if (shouldLog) {
        appendLog("已停止轮询。");
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
          : nextTransport === "connecting"
            ? "Connecting"
            : "Idle"
    );
  }

  function stopListening(shouldLog = true) {
    clearFallbackTimeout();
    stopPolling(shouldLog);
    stopWebSocket(shouldLog);
    listeningRef.current = false;
    setIsSubmitting(false);
    setTransport("idle");
  }

  function resetRunView() {
    stopListening(false);
    setRunId("");
    transportRef.current = "idle";
    activeRunIdRef.current = "";
    loadedReportRunRef.current = "";
    setProgress(DEFAULT_PROGRESS);
    setReportMarkdown("");
    setReportMessage(DEFAULT_REPORT_MESSAGE);
    setErrorMessage("");
  }

  async function loadReport(targetRunId) {
    if (!targetRunId || loadedReportRunRef.current === targetRunId) {
      return;
    }

    try {
      const markdown = await getReportMarkdown(targetRunId);
      loadedReportRunRef.current = targetRunId;
      setReportMessage("报告已生成，可直接在线预览，也可以下载 Markdown 或 JSON 原始结果。");
      setReportMarkdown(markdown);
      setErrorMessage("");
    } catch (error) {
      setReportMessage(`报告生成完成，但预览拉取失败：${error.message}`);
      setReportMarkdown("");
      setErrorMessage(`报告预览加载失败：${error.message}`);
    }
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
      setErrorMessage(nextProgress.error);
      appendLog(`错误: ${nextProgress.error}`);
    } else {
      setErrorMessage("");
      appendLog(`状态更新(${source}): ${nextStatus} / ${nextProgress.percent ?? 0}% / ${nextProgress.current_node || "等待执行"}`);
    }

    if (TERMINAL_STATUSES.has(nextStatus)) {
      stopListening(false);
      void loadReport(data.run_id);
    }
  }

  async function pollStatus(targetRunId, source = "polling") {
    try {
      const data = await getReviewStatus(targetRunId);
      applyStatusPayload(data, source);
    } catch (error) {
      appendLog(`轮询失败: ${error.message}`);
      setStatus("failed");
      setStatusLabel("Polling error");
      setErrorMessage(`任务状态拉取失败：${error.message}`);
      stopListening(false);
    }
  }

  function startPolling(nextRunId, reason = "") {
    stopPolling(false);
    clearFallbackTimeout();
    setTransport("polling");
    if (reason) {
      appendLog(reason);
    }
    void pollStatus(nextRunId, "polling");
    pollRef.current = window.setInterval(() => {
      void pollStatus(nextRunId, "polling");
    }, POLL_INTERVAL_MS);
  }

  function schedulePollingFallback(nextRunId, message) {
    clearFallbackTimeout();
    fallbackTimeoutRef.current = window.setTimeout(() => {
      fallbackTimeoutRef.current = null;
      if (transportRef.current !== "websocket" && activeRunIdRef.current === nextRunId && listeningRef.current && !TERMINAL_STATUSES.has(latestStatusRef.current)) {
        startPolling(nextRunId, message);
      }
    }, WEBSOCKET_FALLBACK_TIMEOUT_MS);
  }

  function connectWebSocket(nextRunId) {
    stopWebSocket(false);
    const socket = new WebSocket(buildWebSocketUrl(nextRunId));
    wsRef.current = socket;
    setTransport("connecting");

    socket.onopen = () => {
      setTransport("websocket");
      appendLog("WebSocket 已连接，切换到实时推送。");
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        applyStatusPayload(payload, "websocket");
      } catch {
        appendLog("WebSocket 消息解析失败，已忽略该条更新。");
      }
    };

    socket.onerror = () => {
      appendLog("WebSocket 连接异常，准备回退到轮询。");
    };

    socket.onclose = () => {
      if (wsRef.current === socket) {
        wsRef.current = null;
      }
      if (!TERMINAL_STATUSES.has(latestStatusRef.current) && activeRunIdRef.current === nextRunId && listeningRef.current) {
        startPolling(nextRunId, "WebSocket 已断开，已回退到轮询。");
      }
    };
  }

  async function submitReview(event) {
    event.preventDefault();
    const payload = mode === "text" ? { prd_text: prdText.trim() } : { prd_path: prdPath.trim() };
    const value = mode === "text" ? payload.prd_text : payload.prd_path;

    if (!value) {
      const nextFormError = mode === "text" ? "请输入 PRD 文本后再提交。" : "请输入 PRD 文件路径后再提交。";
      setFormError(nextFormError);
      setErrorMessage(nextFormError);
      appendLog(nextFormError);
      return;
    }

    setFormError("");
    setErrorMessage("");
    setStatus("running");
    setStatusLabel("Queued");
    resetRunView();
    setIsSubmitting(true);
    listeningRef.current = true;
    appendLog("正在创建评审任务...");

    try {
      const data = await createReview(payload);
      setRunId(data.run_id);
      activeRunIdRef.current = data.run_id;
      setIsSubmitting(true);
      listeningRef.current = true;
      appendLog(`任务已创建: ${data.run_id}`);

      const summary = mode === "text" ? firstLine(prdText.trim()) || "PRD text" : prdPath.trim();
      addHistoryItem({ runId: data.run_id, mode, summary, createdAt: new Date().toISOString() });

      connectWebSocket(data.run_id);
      schedulePollingFallback(data.run_id, "实时连接尚未建立，已使用轮询兜底。");
    } catch (error) {
      setStatus("failed");
      setStatusLabel("Failed");
      stopListening(false);
      setErrorMessage(`创建任务失败：${error.message}`);
      appendLog(`创建任务失败: ${error.message}`);
    }
  }

  async function openHistory(item) {
    stopListening(false);
    setFormError("");
    setErrorMessage("");
    activeRunIdRef.current = item.runId;
    setRunId(item.runId);
    setStatus("running");
    setStatusLabel("History");
    loadedReportRunRef.current = "";
    appendLog(`已切换到历史任务 ${item.runId}。`);

    await pollStatus(item.runId, "history");
    if (!TERMINAL_STATUSES.has(latestStatusRef.current)) {
      setIsSubmitting(true);
      listeningRef.current = true;
      connectWebSocket(item.runId);
      schedulePollingFallback(item.runId, "历史任务实时连接失败，已回退到轮询。");
    } else {
      await loadReport(item.runId);
    }
  }

  useEffect(() => () => {
    stopListening(false);
  }, []);

  useEffect(() => {
    if (formError) {
      setFormError("");
    }
  }, [formError, mode, prdPath, prdText]);

  return {
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
  };
}
