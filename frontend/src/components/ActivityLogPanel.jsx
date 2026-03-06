export function ActivityLogPanel({ logs, onClear }) {
  return (
    <section className="panel progress-panel">
      <div className="subsection-header">
        <h3>运行日志</h3>
        <button className="link-btn" type="button" onClick={onClear}>清空</button>
      </div>
      <div className="activity-log">
        {logs.map((entry, index) => (
          <div className="log-entry" key={`${entry.stamp}-${index}`}>
            <span className="log-time">[{entry.stamp}]</span>
            {` ${entry.message}`}
          </div>
        ))}
      </div>
    </section>
  );
}
