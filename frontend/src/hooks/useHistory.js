import { useEffect, useState } from "react";

import { HISTORY_KEY, HISTORY_LIMIT } from "../constants";

function loadHistory() {
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
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
