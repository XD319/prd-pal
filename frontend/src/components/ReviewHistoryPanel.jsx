import '../styles/panels.css';
import '../styles/components.css';
import { describeHistoryRun } from '../utils/derivers';
import { formatDateTime } from '../utils/formatters';

function ReviewHistoryPanel({ history, activeRunId, onRefresh, onOpenRun }) {
  const recentRuns = history.runs.slice(0, 8);

  return (
    <section className="panel review-history-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review History</p>
          <h2>Recent runs</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onRefresh} disabled={history.refreshing}>
          {history.refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {history.status === 'loading' && history.runs.length === 0 ? (
        <div className="loading-state loading-state-history">
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
        </div>
      ) : history.status === 'error' && history.runs.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>Run history is unavailable</h3>
          <p>{history.error}</p>
        </div>
      ) : recentRuns.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>No review runs yet</h3>
          <p>Completed and in-progress review runs from <code>GET /api/runs</code> will appear here for quick follow-up.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.status === 'error' && <div className="feedback-banner feedback-error">{history.error}</div>}

          {recentRuns.map((run) => {
            const summary = describeHistoryRun(run);
            const isActive = run.run_id === activeRunId;

            return (
              <article key={run.run_id} className={`history-card${isActive ? ' history-card-active' : ''}`}>
                <div className="history-header">
                  <div>
                    <span className="history-kicker">{run.run_id}</span>
                    <h3>{summary.hasResult ? 'Result ready for inspection' : 'Review run in motion'}</h3>
                  </div>
                  <span className={`status-badge status-${summary.status}`}>{summary.statusLabel}</span>
                </div>

                <p className="history-note">{summary.detail}</p>

                <div className="history-meta">
                  <div>
                    <span>Created</span>
                    <strong>{formatDateTime(run.created_at)}</strong>
                  </div>
                  <div>
                    <span>Updated</span>
                    <strong>{formatDateTime(run.updated_at)}</strong>
                  </div>
                </div>

                <div className="history-actions">
                  <button type="button" className="secondary-button" onClick={() => onOpenRun(run)}>
                    {summary.actionLabel}
                  </button>
                  <span className="inline-meta inline-meta-soft">
                    {run.artifact_presence?.report_json ? 'Report artifact ready' : 'Waiting on report artifact'}
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default ReviewHistoryPanel;
