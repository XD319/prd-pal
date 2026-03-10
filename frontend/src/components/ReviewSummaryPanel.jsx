import '../styles/panels.css';
import '../styles/components.css';
import { deriveModeLabel, deriveSummary } from '../utils/derivers';

function ReviewSummaryPanel({ runId, status, result, statusPayload, resultPayload, resultState, failureMessage, resultError }) {
  const summary = deriveSummary(result, runId, statusPayload, resultPayload);

  return (
    <section className="panel review-summary-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review Results</p>
          <h2>Result overview</h2>
        </div>
        {result && <span className="inline-meta">{deriveModeLabel(result)}</span>}
      </div>

      {status === 'failed' ? (
        <div className="empty-state empty-state-soft">
          <div className="empty-grid" />
          <h3>Run failed before review output was ready</h3>
          <p>{failureMessage}</p>
        </div>
      ) : resultState === 'loading' ? (
        <div className="loading-state loading-state-summary">
          <div className="shimmer-block shimmer-title" />
          <div className="metric-grid">
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
          </div>
        </div>
      ) : result ? (
        <div className="result-content">
          <div className="result-lead">
            <h3>{summary.title}</h3>
            <p>{summary.narrative}</p>
          </div>

          <div className="metric-grid">
            {summary.metrics.map((metric) => (
              <div key={metric.label} className="metric-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>

          <div className="chip-row">
            {summary.chips.map((chip) => (
              <span key={chip} className="inline-meta inline-meta-soft">{chip}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-state empty-state-soft">
          <div className="empty-grid" />
          <h3>Review summary will land here</h3>
          <p>
            The workspace will pull structured output from <code>GET /api/review/{'{run_id}'}/result</code> as soon as the run completes.
          </p>
          {resultError && <div className="feedback-banner feedback-error">{resultError}</div>}
        </div>
      )}
    </section>
  );
}

export default ReviewSummaryPanel;