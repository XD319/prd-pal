import { useMemo } from "react";

import { TRACKED_NODES } from "../constants";
import { formatDate } from "../utils";

export function RunStatusPanel({ progress, runId, transportLabel }) {
  const nodeCards = useMemo(() => {
    return TRACKED_NODES.map((nodeName) => ({
      name: nodeName,
      ...(progress.nodes?.[nodeName] ?? { status: "pending", runs: 0 }),
    }));
  }, [progress.nodes]);

  const updatedAtLabel = progress.updated_at ? formatDate(progress.updated_at) : "-";

  return (
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
    </section>
  );
}
