import { useEffect, useRef, useState } from 'react';
import '../styles/panels.css';
import '../styles/components.css';

function ReviewSubmitPanel({ form, onFieldChange, onSubmit, onReset, onLoadSample, isSubmitting, errorMessage }) {
  const formRef = useRef(null);
  const [selectedMode, setSelectedMode] = useState('prd_text');
  const inputModes = [
    { key: 'prd_text', label: 'PRD Content' },
    { key: 'prd_path', label: 'File Path' },
    { key: 'source', label: 'Document Source' },
  ];
  const helperText = 'Use Document Source when you already have a canonical document reference. Otherwise provide exactly one of PRD Content or File Path.';
  const hasPrdText = Boolean(form.prd_text.trim());
  const hasPrdPath = Boolean(form.prd_path.trim());
  const hasSource = Boolean(form.source.trim());
  const hasConflictingInputs = hasPrdText && hasPrdPath;
  const conflictingInputMessage = 'Please provide either PRD content or a file path, not both.';
  const characterCountLabel = `${new Intl.NumberFormat('en-US').format(form.prd_text.length)} characters`;
  const activeMode = selectedMode;
  const isSubmitDisabled = isSubmitting || (!hasPrdText && !hasPrdPath && !hasSource);

  useEffect(() => {
    if (hasSource) {
      setSelectedMode('source');
      return;
    }

    if (hasPrdPath) {
      setSelectedMode('prd_path');
      return;
    }

    if (hasPrdText) {
      setSelectedMode('prd_text');
    }
  }, [hasPrdPath, hasPrdText, hasSource]);

  function handleFormKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  function handleModeSelect(nextMode) {
    if (nextMode === activeMode) {
      return;
    }

    setSelectedMode(nextMode);

    if (nextMode === 'prd_text') {
      onFieldChange('prd_path', '');
      onFieldChange('source', '');
      return;
    }

    if (nextMode === 'prd_path') {
      onFieldChange('prd_text', '');
      onFieldChange('source', '');
      return;
    }

    onFieldChange('prd_text', '');
    onFieldChange('prd_path', '');
  }

  return (
    <section className="panel review-submit-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">New Review</p>
          <h2>Start a review run</h2>
        </div>
        <button
          type="button"
          className="ghost-button"
          onClick={onLoadSample}
          aria-label="Load a sample product requirements document"
        >
          Load sample
        </button>
      </div>

      <form
        ref={formRef}
        className="submission-form"
        onSubmit={onSubmit}
        onKeyDown={handleFormKeyDown}
        aria-label="Review submission form"
      >
        <div className="history-filter-group" role="tablist" aria-label="Choose review input mode">
          {inputModes.map((mode) => (
            <button
              key={mode.key}
              type="button"
              role="tab"
              className={`filter-chip${activeMode === mode.key ? ' filter-chip-active' : ''}`}
              aria-selected={activeMode === mode.key}
              aria-controls={`input-panel-${mode.key}`}
              onClick={() => handleModeSelect(mode.key)}
            >
              {mode.label}
            </button>
          ))}
        </div>

        <label className="field">
          <span>PRD Content</span>
          <textarea
            id="input-panel-prd_text"
            role="tabpanel"
            aria-hidden={activeMode !== 'prd_text'}
            rows="12"
            value={form.prd_text}
            placeholder="Paste or type your Product Requirements Document here..."
            onChange={(event) => onFieldChange('prd_text', event.target.value)}
            aria-label="PRD content"
          />
          <div className="field-meta">
            <span className="field-counter" aria-live="polite">{characterCountLabel}</span>
            {hasConflictingInputs && <p className="field-feedback field-warning">{conflictingInputMessage}</p>}
          </div>
        </label>

        <div className="compact-fields compact-fields-stacked">
          <label className="field">
            <span>File Path</span>
            <input
              id="input-panel-prd_path"
              role="tabpanel"
              aria-hidden={activeMode !== 'prd_path'}
              type="text"
              value={form.prd_path}
              placeholder="e.g. docs/requirements/feature-x.md"
              onChange={(event) => onFieldChange('prd_path', event.target.value)}
              aria-label="PRD file path"
            />
            {hasConflictingInputs && <p className="field-feedback field-warning">{conflictingInputMessage}</p>}
          </label>

          <label className="field">
            <span>Document Source</span>
            <input
              id="input-panel-source"
              role="tabpanel"
              aria-hidden={activeMode !== 'source'}
              type="text"
              value={form.source}
              placeholder="e.g. docs/sample_prd.md or a connector reference"
              onChange={(event) => onFieldChange('source', event.target.value)}
              aria-label="Document source"
            />
          </label>
        </div>

        <p className="form-helper">
          {helperText}
          {' '}
          Press Ctrl+Enter or Cmd+Enter to submit.
        </p>

        {errorMessage && <div className="feedback-banner feedback-error" aria-live="polite">{errorMessage}</div>}

        <div className="action-row">
          <button
            type="submit"
            className="primary-button"
            disabled={isSubmitDisabled}
            aria-label={isSubmitting ? 'Submitting review' : 'Submit review'}
          >
            {isSubmitting ? 'Submitting...' : 'Submit review'}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={onReset}
            aria-label="Reset review submission fields"
          >
            Reset workspace
          </button>
        </div>
      </form>
    </section>
  );
}

export default ReviewSubmitPanel;
