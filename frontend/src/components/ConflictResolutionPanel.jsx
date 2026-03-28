import '../styles/panels.css';
import '../styles/components.css';
import { deriveConflicts } from '../utils/derivers';
import { joinList, pluralize } from '../utils/formatters';

function ConflictGroup({ title, conflicts, emptyMessage }) {
  return (
    <div className="stack">
      <div className="panel-header panel-header-inline">
        <div>
          <h3>{title}</h3>
        </div>
        <span className="inline-meta">{pluralize(conflicts.length, 'item')}</span>
      </div>

      {conflicts.length === 0 ? (
        <div className="empty-inline">{emptyMessage}</div>
      ) : (
        <div className="list-stack">
          {conflicts.map((conflict) => (
            <article key={conflict.id} className="finding-card risk-card">
              <div className="finding-header">
                <h4>{conflict.title}</h4>
                <span className={`severity severity-${conflict.severity}`}>{conflict.severity}</span>
              </div>
              <p>{conflict.description}</p>
              <div className="detail-row">
                {conflict.reviewers.length > 0 && <span>{joinList(conflict.reviewers)}</span>}
                {conflict.decidedBy && <span>{conflict.decidedBy}</span>}
                <span>{conflict.requiresManualResolution ? 'Need manual handling' : 'Arbitrated'}</span>
              </div>
              {conflict.recommendation && <div className="subtle-note">Recommendation: {conflict.recommendation}</div>}
              {conflict.reasoning && <div className="subtle-note">Reasoning: {conflict.reasoning}</div>}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function ConflictResolutionPanel({ result }) {
  const conflicts = result ? deriveConflicts(result) : [];
  const resolved = conflicts.filter((item) => !item.requiresManualResolution);
  const unresolved = conflicts.filter((item) => item.requiresManualResolution);

  return (
    <section className="panel risks-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Conflict Arbitration</p>
          <h2>Conflict resolutions</h2>
        </div>
        <span className="inline-meta">{pluralize(conflicts.length, 'item')}</span>
      </div>

      {conflicts.length === 0 ? (
        <div className="empty-inline">No conflict arbitration output is available for this run.</div>
      ) : (
        <div className="stack">
          <ConflictGroup
            title="已裁决"
            conflicts={resolved}
            emptyMessage="No conflicts were auto-resolved by the delivery reviewer."
          />
          <ConflictGroup
            title="需人工处理"
            conflicts={unresolved}
            emptyMessage="No unresolved conflicts need manual follow-up."
          />
        </div>
      )}
    </section>
  );
}

export default ConflictResolutionPanel;

