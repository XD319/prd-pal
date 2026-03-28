import '../styles/panels.css';
import '../styles/components.css';
import { deriveFindings } from '../utils/derivers';
import { joinList, pluralize } from '../utils/formatters';

function FindingsPanel({ result, status, resultState }) {
  const findings = result ? deriveFindings(result) : [];

  return (
    <section className="panel findings-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review Findings</p>
          <h2>Findings</h2>
        </div>
        <span className="inline-meta">{pluralize(findings.length, 'item')}</span>
      </div>

      {status === 'completed' && resultState === 'loading' ? (
        <div className="loading-state loading-state-list">
          <div className="shimmer-block shimmer-line" />
          <div className="shimmer-block shimmer-line short" />
          <div className="shimmer-block shimmer-line" />
        </div>
      ) : findings.length === 0 ? (
        <div className="empty-inline">No findings are available for this run yet.</div>
      ) : (
        <div className="list-stack">
          {findings.map((finding) => (
            <article key={finding.id} className="finding-card">
              <div className="finding-header">
                <h4>{finding.title}</h4>
                <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
              </div>
              <p>{finding.detail}</p>
              <div className="detail-row">
                {finding.category && <span>{finding.category}</span>}
                {finding.reviewers.length > 0 && <span>{joinList(finding.reviewers)}</span>}
                {finding.assignee && <span>Owner: {finding.assignee}</span>}
                {finding.clarificationApplied && <span>Clarification updated</span>}
              </div>
              {finding.clarificationApplied && (
                <div className="subtle-note">
                  Clarification applied: {finding.originalSeverity} to {finding.severity}.
                </div>
              )}
              {finding.userClarification && <div className="subtle-note">User clarification: {finding.userClarification}</div>}
              {finding.action && <div className="subtle-note">Suggested action: {finding.action}</div>}
              {finding.evidence.length > 0 && (
                <details className="evidence-panel">
                  <summary>Evidence ({finding.evidence.length})</summary>
                  <div className="evidence-list">
                    {finding.evidence.map((item, index) => (
                      <div key={`${finding.id}-evidence-${index}`} className="evidence-item">
                        <strong>{item.title || 'Evidence'}</strong>
                        <p>{item.snippet || 'No evidence snippet was recorded.'}</p>
                        <div className="detail-row">
                          {item.source && <span>{item.source}</span>}
                          {item.ref && <span>{item.ref}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default FindingsPanel;
