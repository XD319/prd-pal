import { useState } from "react";

import { MAX_LOG_ENTRIES } from "../constants";
import { formatTime } from "../utils";

export function useLogs() {
  const [logs, setLogs] = useState([{ stamp: formatTime(new Date()), message: "系统已就绪，等待提交任务。" }]);

  function appendLog(message) {
    setLogs((current) => {
      const last = current[current.length - 1];
      if (last?.message === message) {
        return current;
      }

      return [...current, { stamp: formatTime(new Date()), message }].slice(-MAX_LOG_ENTRIES);
    });
  }

  function clearLogs() {
    setLogs([]);
    appendLog("日志已清空。");
  }

  return { logs, appendLog, clearLogs };
}
