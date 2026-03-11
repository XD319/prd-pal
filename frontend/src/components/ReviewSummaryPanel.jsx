import '../styles/panels.css';
import '../styles/components.css';
import { deriveGatingInfo, deriveModeLabel, deriveReviewers, deriveSummary } from '../utils/derivers';

function ReviewSummaryPanel({ runId, status, result, statusPayload, resultPayload, resultState, failureMessage, resultError }) {
  const summary = deriveSummary(result, runId, statusPayload, resultPayload);
  const reviewers = deriveReviewers(result, resultPayload);
  const gating = deriveGatingInfo(result, resultPayload);

  return (
    <section className="panel review-summary-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review Results</p>
          <h2>Result overview</h2>
        </div>
        {result && <span className="inline-meta" aria-live="polite">{deriveModeLabel(result)}</span>}
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

          {(gating.skipped || result?.partial_review || result?.manual_review_required || result?.parallel_review?.manual_review_required) && (
            <div className="feedback-banner feedback-error" aria-live="polite">
              {result?.manual_review_message || result?.parallel_review?.manual_review_message || 'This run needs partial or manual review follow-up.'}
            </div>
          )}

          <div className="panel-grid panel-grid-two-up">
            <div className="metric-card">
              <span>Selected reviewers</span>
              <strong>{reviewers.used.length > 0 ? reviewers.used.join(', ') : 'None'}</strong>
            </div>
            <div className="metric-card">
              <span>Skipped reviewers</span>
              <strong>
                {reviewers.skipped.length > 0
                  ? reviewers.skipped.map((item) => item.reviewer ?? item).join(', ')
                  : 'None'}
              </strong>
            </div>
          </div>

          <div className="result-lead">
            <h3>Gating info</h3>
            <p>Mode decision: {deriveModeLabel({ mode: gating.selectedMode })}</p>
            <div className="chip-row">
              {gating.reasons.map((reason) => (
                <span key={reason} className="inline-meta inline-meta-soft">{reason}</span>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-state empty-state-soft">
          <div className="empty-grid" />
          <h3>Review summary will land here</h3>
          <p>
            The workspace will pull structured output from <code>GET /api/review/{'{run_id}'}/result</code> as soon as the run completes.
          </p>
          {resultError && <div className="feedback-banner feedback-error" aria-live="polite">{resultError}</div>}
        </div>
      )}
    </section>
  );
}

export default ReviewSummaryPanel;
