import { useEffect, useState } from "react";

import { HISTORY_KEY, HISTORY_LIMIT } from "../constants";

function normalizeHistoryItem(item) {
  if (!item || typeof item !== "object") {
    return null;
  }

  const runId = typeof item.runId === "string" ? item.runId.trim() : "";
  const mode = item.mode === "path" ? "path" : item.mode === "text" ? "text" : "";
  const summary = typeof item.summary === "string" ? item.summary.trim() : "";
  const createdAt = typeof item.createdAt === "string" ? item.createdAt : "";

  if (!runId || !mode || !summary || !createdAt) {
    return null;
  }

  return { runId, mode, summary, createdAt };
}

function loadHistory() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.map(normalizeHistoryItem).filter(Boolean).slice(0, HISTORY_LIMIT);
  } catch {
    return [];
  }
}

export function useHistory() {
  const [history, setHistory] = useState(() => loadHistory());

  useEffect(() => {
    window.localStorage.setItem(HISTORY_KEY, JSON.stringify(history.slice(0, HISTORY_LIMIT)));
  }, [history]);

  function addHistoryItem(item) {
    setHistory((current) => [item, ...current].slice(0, HISTORY_LIMIT));
  }

  function clearHistory() {
    setHistory([]);
  }

  return { history, addHistoryItem, clearHistory };
}
