import '../styles/panels.css';
import '../styles/components.css';
import { pluralize } from '../utils/formatters';

function ArtifactDownloadPanel({ runId, status, resultPayload, statusPayload, downloadFormat, onDownload }) {
  const artifactPaths = resultPayload?.artifact_paths ?? statusPayload?.report_paths ?? {};
  const artifactKeys = Object.keys(artifactPaths);
  const canDownload = Boolean(runId) && status === 'completed';

  return (
    <section className="panel artifact-download-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Export & Artifacts</p>
          <h2>Artifacts</h2>
        </div>
        <span className="inline-meta">{pluralize(artifactKeys.length, 'path')}</span>
      </div>

      <p className="panel-copy">
        Download the canonical review report as Markdown or JSON after the run completes. Additional artifact paths are listed for inspection.
      </p>

      <div className="action-row">
        <button
          type="button"
          className="primary-button"
          disabled={!canDownload || downloadFormat === 'md'}
          onClick={() => onDownload('md')}
        >
          {downloadFormat === 'md' ? 'Downloading Markdown...' : 'Download Markdown'}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={!canDownload || downloadFormat === 'json'}
          onClick={() => onDownload('json')}
        >
          {downloadFormat === 'json' ? 'Downloading JSON...' : 'Download JSON'}
        </button>
      </div>

      {!canDownload && <div className="empty-inline">Artifacts unlock after a run completes successfully.</div>}

      {artifactKeys.length > 0 && (
        <div className="artifact-list">
          {artifactKeys.map((key) => (
            <div key={key} className="artifact-row">
              <span>{key}</span>
              <code>{artifactPaths[key]}</code>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default ArtifactDownloadPanel;