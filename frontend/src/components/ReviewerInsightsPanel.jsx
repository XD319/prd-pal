import '../styles/panels.css';
import '../styles/components.css';
import { deriveReviewerInsights } from '../utils/derivers';
import { formatStatusLabel, pluralize } from '../utils/formatters';

function ReviewerInsightsPanel({ result }) {
  const insights = result ? deriveReviewerInsights(result) : [];

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Reviewer Insights</p>
          <h2>Reviewer insights</h2>
        </div>
        <span className="inline-meta">{pluralize(insights.length, 'reviewer')}</span>
      </div>

      {insights.length === 0 ? (
        <div className="empty-inline">No reviewer insight records are available for this run.</div>
      ) : (
        <div className="list-stack">
          {insights.map((item) => (
            <article key={item.id} className="finding-card insight-card">
              <div className="finding-header">
                <h4>{item.reviewer}</h4>
                <span className={`status-badge status-${item.status}`}>{formatStatusLabel(item.status)}</span>
              </div>
              {item.summary && <p>{item.summary}</p>}
              {item.statusDetail && <div className="subtle-note">{item.statusDetail}</div>}
              <div className="detail-row">
                {item.ambiguityType && <span>Ambiguity: {item.ambiguityType}</span>}
                {item.clarificationQuestion && <span>Clarify: {item.clarificationQuestion}</span>}
              </div>
              {item.notes.length > 0 && (
                <div className="insight-notes">
                  {item.notes.map((note, index) => (
                    <div key={`${item.id}-note-${index}`} className="subtle-note">{note}</div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default ReviewerInsightsPanel;
