import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { submitFeishuReview } from '../api';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import ReviewSubmissionForm from '../components/ReviewSubmissionForm';
import { useToast } from '../components/ToastProvider';
import { formatApiError } from '../utils/errors';
import { buildSubmissionPayload, validateSubmission } from '../utils/submission';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: '',
  mode: 'quick',
};

function FeishuEntryPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [form, setForm] = useState(initialForm);
  const [submitState, setSubmitState] = useState('idle');
  const [submitError, setSubmitError] = useState('');
  const [submittedRunId, setSubmittedRunId] = useState('');

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
    setSubmitError('');
  }

  function resetForm() {
    setForm(initialForm);
    setSubmitError('');
    setSubmittedRunId('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = buildSubmissionPayload(form, {
      includeMode: true,
      allowPrdPath: false,
    });
    const validationMessage = validateSubmission(payload, {
      allowPrdPath: false,
      requireSourceOrText: true,
    });
    if (validationMessage) {
      setSubmitError(validationMessage);
      return;
    }

    setSubmitState('submitting');
    setSubmitError('');

    try {
      const response = await submitFeishuReview(payload);
      setSubmittedRunId(response.run_id);
      setSubmitState('idle');
      showToast(`Review submitted from Feishu entry. Tracking run ${response.run_id}.`, 'success');
    } catch (error) {
      setSubmitState('idle');
      setSubmitError(formatApiError(error, 'Feishu review submission failed.'));
    }
  }

  return (
    <>
      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Feishu Main Entry</p>
          <h1>Launch a review without the full workspace</h1>
          <p className="hero-copy">
            Use this lightweight page when the user enters from Feishu and only needs to submit a source or PRD text,
            choose a mode, and jump straight into the run detail page.
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Best Input</span>
          <strong>Start from a Feishu document link</strong>
          <p>
            Paste a Feishu or Lark document source first. If the document link is not ready, fall back to direct PRD
            text and submit the run in one step.
          </p>
        </div>
      </header>

      <main className="workspace-grid workspace-grid-feishu">
        <section className="stack">
          <PanelErrorBoundary panelTitle="Feishu Entry" resetKey={`${submitState}:${submittedRunId}`}>
            <ReviewSubmissionForm
              form={form}
              onFieldChange={updateField}
              onSubmit={handleSubmit}
              onReset={resetForm}
              onLoadSample={() => {}}
              isSubmitting={submitState === 'submitting'}
              errorMessage={submitError}
              kicker="Feishu Entry"
              title="Submit from Feishu"
              helperText="Prefer a Feishu document link or connector source. If source is unavailable, provide PRD content directly."
              submitLabel="Start review"
              resetLabel="Clear form"
              sourceLabel="Feishu Source"
              sourcePlaceholder="e.g. https://your-domain.feishu.cn/docx/... or feishu://docx/..."
              showFilePath={false}
              showLoadSample={false}
              showMode
              sourceFirst
              sourceEmphasis="Recommended: paste the Feishu document link or connector source here."
              sourceHelper="This entry page is optimized for source-first submission and a fast jump into run details."
              formAriaLabel="Feishu review submission form"
            />
          </PanelErrorBoundary>
        </section>

        <section className="stack">
          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Next Step</p>
                <h2>Open the run detail page</h2>
              </div>
            </div>

            {submittedRunId ? (
              <div className="submission-success-card">
                <span className="inline-meta">Run created</span>
                <h3>{submittedRunId}</h3>
                <p className="panel-copy">
                  The review run has been queued successfully. Open the detail page to watch progress, findings,
                  questions, and downloadable artifacts.
                </p>
                <div className="action-row">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => navigate(`/run/${submittedRunId}`)}
                  >
                    Open run details
                  </button>
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={resetForm}
                  >
                    Submit another
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-state empty-state-compact">
                <div>
                  <h3>No run yet</h3>
                  <p>
                    Submit a Feishu source or PRD text, then this panel will show the generated <code>run_id</code> and
                    a direct path into the review detail page.
                  </p>
                </div>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Navigation</p>
                <h2>Need the full workspace?</h2>
              </div>
            </div>
            <p className="panel-copy">
              The Feishu entry page intentionally stays focused on submission. If you need history browsing or the
              broader workspace layout, head back to the main home page.
            </p>
            <div className="action-row">
              <Link to="/" className="secondary-button">Open home workspace</Link>
            </div>
          </section>
        </section>
      </main>
    </>
  );
}

export default FeishuEntryPage;
