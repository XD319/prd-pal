import '../styles/panels.css';
import '../styles/components.css';
import { deriveToolCalls } from '../utils/derivers';
import { formatStatusLabel, pluralize } from '../utils/formatters';

function ToolTracePanel({ result }) {
  const toolCalls = result ? deriveToolCalls(result) : [];

  return (
    <section className="panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Tool Trace</p>
          <h2>Tool trace</h2>
        </div>
        <span className="inline-meta">{pluralize(toolCalls.length, 'call')}</span>
      </div>

      {toolCalls.length === 0 ? (
        <div className="empty-inline">No tool calls were recorded for this run.</div>
      ) : (
        <div className="list-stack">
          {toolCalls.map((call) => (
            <article key={call.id} className="finding-card trace-card">
              <div className="finding-header">
                <div>
                  <h4>{call.toolName}</h4>
                  <p className="trace-subtitle">{call.reviewer}</p>
                </div>
                <span className={`status-badge status-${call.status}`}>{formatStatusLabel(call.status)}</span>
              </div>
              <div className="detail-row">
                {call.evidenceCount > 0 && <span>Evidence hits: {call.evidenceCount}</span>}
                {call.query && <span>Query captured</span>}
              </div>
              {call.outputSummary && <p>{call.outputSummary}</p>}
              {call.degradedReason && <div className="subtle-note">Degraded: {call.degradedReason}</div>}
              {call.errorMessage && <div className="subtle-note">Error: {call.errorMessage}</div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default ToolTracePanel;
