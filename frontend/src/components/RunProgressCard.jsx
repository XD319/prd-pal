import '../styles/panels.css';
import '../styles/components.css';
import { deriveNodes } from '../utils/derivers';
import { formatDateTime, formatPercentFromWhole, formatStatusLabel, pluralize } from '../utils/formatters';

function RunProgressCard({ runId, status, statusPayload, failureMessage }) {
  const progress = statusPayload?.progress ?? {};
  const nodes = deriveNodes(progress);
  const statusLabel = formatStatusLabel(status);

  return (
    <section className="panel run-progress-card">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Pipeline Status</p>
          <h2>Run progress</h2>
        </div>
        <span className={`status-badge status-${status}`}>{statusLabel}</span>
      </div>

      {!runId ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-orb" />
          <h3>No run in focus</h3>
          <p>Submit a PRD or pick a recent run to inspect progress and result details here.</p>
        </div>
      ) : (
        <div className="status-stack">
          <div className="status-meta status-meta-two-up">
            <div>
              <span>Run ID</span>
              <strong>{runId}</strong>
            </div>
            <div>
              <span>Percent complete</span>
              <strong>{formatPercentFromWhole(progress.percent ?? 0)}</strong>
            </div>
            <div>
              <span>Current node</span>
              <strong>{progress.current_node || 'Waiting for next stage'}</strong>
            </div>
            <div>
              <span>Updated</span>
              <strong>{formatDateTime(progress.updated_at)}</strong>
            </div>
          </div>

          {failureMessage && <div className="feedback-banner feedback-error">{failureMessage}</div>}

          <div className="progress-bar-shell" aria-hidden="true">
            <div className="progress-bar-fill" style={{ width: `${Math.max(8, Number(progress.percent ?? 0))}%` }} />
          </div>

          <div className="node-list">
            {nodes.length === 0 ? (
              <div className="empty-inline">Node-level progress has not been reported yet.</div>
            ) : (
              nodes.map((node) => (
                <article key={node.name} className={`node-card node-${node.status}`}>
                  <div className="node-header">
                    <strong>{node.name}</strong>
                    <span className={`node-pill node-pill-${node.status}`}>{node.status}</span>
                  </div>
                  <p>
                    {node.runs > 0 ? `${pluralize(node.runs, 'attempt')}` : 'Not started'}
                    {node.lastEnd ? ` - finished ${formatDateTime(node.lastEnd)}` : ''}
                    {!node.lastEnd && node.lastStart ? ` - started ${formatDateTime(node.lastStart)}` : ''}
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      )}
    </section>
  );
}

export default RunProgressCard;