import '../styles/panels.css';
import '../styles/components.css';

function ReviewSubmitPanel({ form, onFieldChange, onSubmit, onReset, onLoadSample, isSubmitting, errorMessage }) {
  const helperText = 'Use Document Source when you already have a canonical document reference. Otherwise provide exactly one of PRD Content or File Path.';
  const hasPrdText = Boolean(form.prd_text.trim());
  const hasPrdPath = Boolean(form.prd_path.trim());
  const hasConflictingInputs = hasPrdText && hasPrdPath;
  const conflictingInputMessage = 'Please provide either PRD content or a file path, not both.';
  const characterCountLabel = `${new Intl.NumberFormat('en-US').format(form.prd_text.length)} characters`;

  return (
    <section className="panel review-submit-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">New Review</p>
          <h2>Start a review run</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onLoadSample}>
          Load sample
        </button>
      </div>

      <form className="submission-form" onSubmit={onSubmit}>
        <label className="field">
          <span>PRD Content</span>
          <textarea
            rows="12"
            value={form.prd_text}
            placeholder="Paste or type your Product Requirements Document here..."
            onChange={(event) => onFieldChange('prd_text', event.target.value)}
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
            />
          </label>
        </div>

        <p className="form-helper">{helperText}</p>

        {errorMessage && <div className="feedback-banner feedback-error">{errorMessage}</div>}

        <div className="action-row">
          <button type="submit" className="primary-button" disabled={isSubmitting}>
            {isSubmitting ? 'Submitting...' : 'Submit review'}
          </button>
          <button type="button" className="secondary-button" onClick={onReset}>
            Reset workspace
          </button>
        </div>
      </form>
    </section>
  );
}

export default ReviewSubmitPanel;