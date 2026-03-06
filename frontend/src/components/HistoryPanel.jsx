import { formatDate, truncate } from "../utils";

export function HistoryPanel({ history, onClear, onOpen }) {
  return (
    <aside className="panel history-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">History</p>
          <h2>最近运行</h2>
        </div>
        <button className="link-btn" type="button" onClick={onClear}>清空历史</button>
      </div>
      <div className="history-list">
        {history.length ? history.map((item) => (
          <button className="history-item" type="button" key={`${item.runId}-${item.createdAt}`} onClick={() => void onOpen(item)}>
            <span className="history-item-title">{truncate(item.summary, 48)}</span>
            <span className="history-item-meta">{`${item.mode.toUpperCase()} · ${item.runId} · ${formatDate(item.createdAt)}`}</span>
          </button>
        )) : <div className="empty-state">还没有历史运行记录。</div>}
      </div>
    </aside>
  );
}
