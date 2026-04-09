import { useRef } from 'react';
import '../styles/panels.css';
import '../styles/components.css';

function ReviewSubmissionForm({
  form,
  onFieldChange,
  onSubmit,
  onReset,
  onLoadSample,
  isSubmitting,
  errorMessage,
  kicker = 'New Review',
  title = 'Start a review run',
  helperText = 'Use Document Source when you already have a canonical document reference. Otherwise provide exactly one of PRD Content or File Path.',
  submitLabel = 'Submit review',
  resetLabel = 'Reset workspace',
  sourceLabel = 'Document Source',
  sourcePlaceholder = 'e.g. docs/sample_prd.md or a connector reference',
  textLabel = 'PRD Content',
  textPlaceholder = 'Paste or type your Product Requirements Document here...',
  filePathLabel = 'File Path',
  filePathPlaceholder = 'e.g. docs/requirements/feature-x.md',
  modeLabel = 'Review Mode',
  showMode = false,
  showFilePath = true,
  showLoadSample = true,
  sourceFirst = false,
  sourceEmphasis = '',
  sourceHelper = '',
  formAriaLabel = 'Review submission form',
}) {
  const formRef = useRef(null);
  const prdText = String(form.prd_text ?? '');
  const prdPath = String(form.prd_path ?? '');
  const hasPrdText = Boolean(prdText.trim());
  const hasPrdPath = Boolean(prdPath.trim());
  const hasConflictingInputs = showFilePath && hasPrdText && hasPrdPath;
  const conflictingInputMessage = 'Please provide either PRD content or a file path, not both.';
  const characterCountLabel = `${new Intl.NumberFormat('en-US').format(prdText.length)} characters`;

  function handleFormKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      formRef.current?.requestSubmit();
    }
  }

  const sourceField = (
    <label className={`field${sourceEmphasis ? ' field-emphasis' : ''}`}>
      <span>{sourceLabel}</span>
      <input
        type="text"
        value={form.source}
        placeholder={sourcePlaceholder}
        onChange={(event) => onFieldChange('source', event.target.value)}
        aria-label={sourceLabel}
      />
      {(sourceEmphasis || sourceHelper) && (
        <div className="field-meta field-meta-stacked">
          {sourceEmphasis ? <p className="field-feedback field-accent">{sourceEmphasis}</p> : null}
          {sourceHelper ? <p className="field-feedback">{sourceHelper}</p> : null}
        </div>
      )}
    </label>
  );

  return (
    <section className="panel review-submit-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">{kicker}</p>
          <h2>{title}</h2>
        </div>
        {showLoadSample ? (
          <button
            type="button"
            className="ghost-button"
            onClick={onLoadSample}
            aria-label="Load a sample product requirements document"
          >
            Load sample
          </button>
        ) : null}
      </div>

      <form
        ref={formRef}
        className="submission-form"
        onSubmit={onSubmit}
        onKeyDown={handleFormKeyDown}
        aria-label={formAriaLabel}
      >
        {sourceFirst ? sourceField : null}

        <label className="field">
          <span>{textLabel}</span>
          <textarea
            rows="12"
            value={form.prd_text}
            placeholder={textPlaceholder}
            onChange={(event) => onFieldChange('prd_text', event.target.value)}
            aria-label={textLabel}
          />
          <div className="field-meta">
            <span className="field-counter" aria-live="polite">{characterCountLabel}</span>
            {hasConflictingInputs ? <p className="field-feedback field-warning">{conflictingInputMessage}</p> : null}
          </div>
        </label>

        <div className="compact-fields compact-fields-stacked">
          {showFilePath ? (
            <label className="field">
              <span>{filePathLabel}</span>
              <input
                type="text"
                value={form.prd_path}
                placeholder={filePathPlaceholder}
                onChange={(event) => onFieldChange('prd_path', event.target.value)}
                aria-label={filePathLabel}
              />
              {hasConflictingInputs ? <p className="field-feedback field-warning">{conflictingInputMessage}</p> : null}
            </label>
          ) : null}

          {sourceFirst ? null : sourceField}

          {showMode ? (
            <label className="field">
              <span>{modeLabel}</span>
              <select
                value={form.mode}
                onChange={(event) => onFieldChange('mode', event.target.value)}
                aria-label={modeLabel}
              >
                <option value="quick">Quick</option>
                <option value="auto">Auto</option>
                <option value="full">Full</option>
              </select>
            </label>
          ) : null}
        </div>

        <p className="form-helper">
          {helperText}
          {' '}
          Press Ctrl+Enter or Cmd+Enter to submit.
        </p>

        {errorMessage ? <div className="feedback-banner feedback-error" aria-live="polite">{errorMessage}</div> : null}

        <div className="action-row">
          <button
            type="submit"
            className="primary-button"
            disabled={isSubmitting}
            aria-label={isSubmitting ? 'Submitting review' : submitLabel}
          >
            {isSubmitting ? 'Submitting...' : submitLabel}
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={onReset}
            aria-label={resetLabel}
          >
            {resetLabel}
          </button>
        </div>
      </form>
    </section>
  );
}

export default ReviewSubmissionForm;
