import '../styles/panels.css';
import '../styles/components.css';
import { deriveNodes } from '../utils/derivers';
import { formatDateTime, formatPercentFromWhole, formatStatusLabel, pluralize } from '../utils/formatters';

function RunProgressCard({ runId, status, statusPayload, failureMessage }) {
  const progress = statusPayload?.progress ?? {};
  const nodes = deriveNodes(progress);
  const statusLabel = formatStatusLabel(status);
  const currentNodeName = String(progress.current_node ?? '');

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
          <p className="sr-only" aria-live="polite">{`Run ${runId} status ${statusLabel}.`}</p>

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

          {failureMessage && <div className="feedback-banner feedback-error" aria-live="polite">{failureMessage}</div>}

          {nodes.length === 0 ? (
            <div className="empty-inline">Node-level progress has not been reported yet.</div>
          ) : (
            <>
              <div className="stepper-shell" aria-label="Pipeline progress">
                <div className="stepper-header">
                  <strong>Execution flow</strong>
                  <span className="stepper-progress">{formatPercentFromWhole(progress.percent ?? 0)} complete</span>
                </div>

                <div className="stepper-track">
                  {nodes.map((node, index) => {
                    const normalizedStatus = String(node.status ?? 'pending');
                    const isCurrent =
                      normalizedStatus === 'running' ||
                      (normalizedStatus !== 'completed' && currentNodeName && node.name === currentNodeName);
                    const stepClassName = [
                      'stepper-step',
                      `stepper-step-${normalizedStatus}`,
                      normalizedStatus === 'completed' ? 'is-completed' : '',
                      isCurrent ? 'is-current' : '',
                    ]
                      .filter(Boolean)
                      .join(' ');

                    return (
                      <div
                        key={node.name}
                        className={stepClassName}
                        aria-current={isCurrent ? 'step' : undefined}
                      >
                        <div className="stepper-rail" aria-hidden="true">
                          <span className="stepper-dot" />
                          {index < nodes.length - 1 && <span className="stepper-line" />}
                        </div>
                        <div className="stepper-copy">
                          <strong>{node.name}</strong>
                          <span>{node.status}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="node-list">
                {nodes.map((node) => (
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
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}

export default RunProgressCard;
