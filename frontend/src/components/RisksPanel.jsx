import '../styles/panels.css';
import '../styles/components.css';
import { deriveRisks } from '../utils/derivers';
import { joinList, pluralize } from '../utils/formatters';

function RisksPanel({ result }) {
  const risks = result ? deriveRisks(result) : [];

  return (
    <section className="panel risks-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">RisksPanel</p>
          <h2>Risks</h2>
        </div>
        <span className="inline-meta">{pluralize(risks.length, 'item')}</span>
      </div>

      {risks.length === 0 ? (
        <div className="empty-inline">No structured risks were returned for this run.</div>
      ) : (
        <div className="list-stack">
          {risks.map((risk) => (
            <article key={risk.id} className="finding-card risk-card">
              <div className="finding-header">
                <h4>{risk.title}</h4>
                <span className={`severity severity-${risk.severity}`}>{risk.severity}</span>
              </div>
              <p>{risk.detail}</p>
              <div className="detail-row">
                {risk.category && <span>{risk.category}</span>}
                {risk.reviewers.length > 0 && <span>{joinList(risk.reviewers)}</span>}
              </div>
              {risk.mitigation && <div className="subtle-note">Mitigation: {risk.mitigation}</div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default RisksPanel;
