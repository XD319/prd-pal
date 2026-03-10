import { useRef } from 'react';
import '../styles/panels.css';
import '../styles/components.css';

function ReviewSubmitPanel({ form, onFieldChange, onSubmit, onReset, onLoadSample, isSubmitting, errorMessage }) {
  const formRef = useRef(null);
  const helperText = 'Use Document Source when you already have a canonical document reference. Otherwise provide exactly one of PRD Content or File Path.';
  const hasPrdText = Boolean(form.prd_text.trim());
  const hasPrdPath = Boolean(form.prd_path.trim());
  const hasConflictingInputs = hasPrdText && hasPrdPath;
  const conflictingInputMessage = 'Please provide either PRD content or a file path, not both.';
  const characterCountLabel = `${new Intl.NumberFormat('en-US').format(form.prd_text.length)} characters`;

  function handleFormKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
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
        <label className="field">
          <span>PRD Content</span>
          <textarea
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
            disabled={isSubmitting}
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
