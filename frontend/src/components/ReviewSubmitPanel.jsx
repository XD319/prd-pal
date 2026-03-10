import '../styles/panels.css';
import '../styles/components.css';

function ReviewSubmitPanel({ form, onFieldChange, onSubmit, onReset, onLoadSample, isSubmitting, errorMessage }) {
  const helperText = 'Use source when you already have a canonical document reference. Otherwise provide exactly one of prd_text or prd_path.';

  return (
    <section className="panel review-submit-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">ReviewSubmitPanel</p>
          <h2>Start a review run</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onLoadSample}>
          Load sample
        </button>
      </div>

      <form className="submission-form" onSubmit={onSubmit}>
        <label className="field">
          <span>prd_text</span>
          <textarea
            rows="12"
            value={form.prd_text}
            placeholder="Paste a PRD draft when you want to review text directly."
            onChange={(event) => onFieldChange('prd_text', event.target.value)}
          />
        </label>

        <div className="compact-fields compact-fields-stacked">
          <label className="field">
            <span>prd_path</span>
            <input
              type="text"
              value={form.prd_path}
              placeholder="docs/product/requirement.md"
              onChange={(event) => onFieldChange('prd_path', event.target.value)}
            />
          </label>

          <label className="field">
            <span>source</span>
            <input
              type="text"
              value={form.source}
              placeholder="docs/sample_prd.md or connector source"
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
