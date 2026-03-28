import { useCallback, useEffect, useState } from 'react';
import { fetchArtifactPreview } from '../api';
import '../styles/panels.css';
import '../styles/components.css';
import { pluralize } from '../utils/formatters';

const DOWNLOAD_FORMAT_OPTIONS = [
  { value: 'md', label: 'Markdown (.md)' },
  { value: 'json', label: 'JSON (.json)' },
  { value: 'html', label: 'HTML (.html)' },
  { value: 'csv', label: 'CSV (.csv)' },
];

function getPreviewFormat(path) {
  const normalized = String(path ?? '').toLowerCase();
  if (normalized.endsWith('.md') || normalized.endsWith('.markdown')) {
    return 'markdown';
  }
  if (normalized.endsWith('.json')) {
    return 'json';
  }
  return 'text';
}

function ArtifactDownloadPanel({ runId, status, resultPayload, statusPayload, downloadFormat, onDownload }) {
  const artifactPaths = resultPayload?.artifact_paths ?? statusPayload?.report_paths ?? {};
  const artifactKeys = Object.keys(artifactPaths);
  const canDownload = Boolean(runId) && status === 'completed';
  const [selectedFormat, setSelectedFormat] = useState('md');
  const [previewState, setPreviewState] = useState({
    artifactKey: '',
    status: 'idle',
    content: '',
    format: '',
    error: '',
  });

  const closePreview = useCallback(() => {
    setPreviewState({
      artifactKey: '',
      status: 'idle',
      content: '',
      format: '',
      error: '',
    });
  }, []);

  useEffect(() => {
    if (!previewState.artifactKey) {
      return undefined;
    }

    function handleWindowKeyDown(event) {
      if (event.key === 'Escape') {
        closePreview();
      }
    }

    window.addEventListener('keydown', handleWindowKeyDown);
    return () => {
      window.removeEventListener('keydown', handleWindowKeyDown);
    };
  }, [closePreview, previewState.artifactKey]);

  async function handleTogglePreview(artifactKey) {
    if (!runId) {
      return;
    }

    if (previewState.artifactKey === artifactKey) {
      closePreview();
      return;
    }

    const path = artifactPaths[artifactKey];
    setPreviewState({
      artifactKey,
      status: 'loading',
      content: '',
      format: getPreviewFormat(path),
      error: '',
    });

    try {
      const payload = await fetchArtifactPreview(runId, artifactKey);
      setPreviewState({
        artifactKey,
        status: 'ready',
        content: String(payload.content ?? ''),
        format: payload.format ?? getPreviewFormat(payload.path),
        error: '',
      });
    } catch (error) {
      setPreviewState({
        artifactKey,
        status: 'error',
        content: '',
        format: getPreviewFormat(path),
        error: error.message || 'Artifact preview could not be loaded.',
      });
    }
  }

  function renderPreviewContent() {
    if (previewState.status === 'loading') {
      return <div className="empty-inline">Loading preview...</div>;
    }

    if (previewState.status === 'error') {
      return <div className="feedback-banner feedback-error" aria-live="polite">{previewState.error}</div>;
    }

    if (previewState.format === 'json') {
      try {
        const parsed = JSON.parse(previewState.content);
        return <pre className="artifact-preview-code">{JSON.stringify(parsed, null, 2)}</pre>;
      } catch {
        return <pre className="artifact-preview-code">{previewState.content}</pre>;
      }
    }

    return <pre className="artifact-preview-markdown">{previewState.content}</pre>;
  }

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
        Download the canonical review report as Markdown, JSON, HTML, or CSV after the run completes. Additional artifact paths are listed for inspection.
      </p>

      <div className="action-row">
        <label className="field-label" htmlFor="artifact-download-format">
          Export format
        </label>
        <select
          id="artifact-download-format"
          className="input"
          value={selectedFormat}
          onChange={(event) => setSelectedFormat(event.target.value)}
          disabled={!canDownload || Boolean(downloadFormat)}
          aria-label="Select report export format"
        >
          {DOWNLOAD_FORMAT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>{option.label}</option>
          ))}
        </select>
        <button
          type="button"
          className="primary-button"
          disabled={!canDownload || downloadFormat === selectedFormat}
          onClick={() => onDownload(selectedFormat)}
          aria-label={downloadFormat === selectedFormat ? `Downloading ${selectedFormat.toUpperCase()} report` : `Download ${selectedFormat.toUpperCase()} report`}
        >
          {downloadFormat === selectedFormat ? `Downloading ${selectedFormat.toUpperCase()}...` : `Download ${selectedFormat.toUpperCase()}`}
        </button>
      </div>

      {!canDownload && <div className="empty-inline">Artifacts unlock after a run completes successfully.</div>}

      {artifactKeys.length > 0 && (
        <div className="artifact-list">
          {artifactKeys.map((key) => {
            const isExpanded = previewState.artifactKey === key;
            const previewPanelId = `artifact-preview-${key.replace(/[^a-zA-Z0-9_-]/g, '-')}`;

            return (
              <div key={key} className="artifact-entry">
                <div className="artifact-row">
                  <button
                    type="button"
                    className="artifact-key-button"
                    onClick={() => handleTogglePreview(key)}
                    aria-expanded={isExpanded}
                    aria-controls={previewPanelId}
                    aria-label={`${isExpanded ? 'Hide' : 'Show'} preview for ${key}`}
                  >
                    {key}
                  </button>
                  <code>{artifactPaths[key]}</code>
                </div>

                {isExpanded && (
                  <div id={previewPanelId} className="artifact-preview" aria-live="polite">
                    <div className="artifact-preview-header">
                      <strong>{key}</strong>
                      <button
                        type="button"
                        className="ghost-button"
                        onClick={closePreview}
                        aria-label={`Close preview for ${key}`}
                      >
                        Close preview
                      </button>
                    </div>
                    {renderPreviewContent()}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default ArtifactDownloadPanel;
