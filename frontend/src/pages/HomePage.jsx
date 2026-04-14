import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { submitReview } from '../api';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import ReviewHistoryPanel from '../components/ReviewHistoryPanel';
import ReviewSubmitPanel from '../components/ReviewSubmitPanel';
import { useToast } from '../components/ToastProvider';
import useReviewHistory from '../hooks/useReviewHistory';
import { formatApiError } from '../utils/errors';
import { buildSubmissionPayload, validateSubmission } from '../utils/submission';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: '',
  mode: 'quick',
};

function HomePage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const { history, loadRunHistory } = useReviewHistory();
  const [form, setForm] = useState(initialForm);
  const [submitState, setSubmitState] = useState('idle');
  const [submitError, setSubmitError] = useState('');

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
    setSubmitError('');
  }

  function loadSample() {
    setForm({
      prd_text:
        'Goal: reviewers should submit one PRD, monitor progress, inspect structured findings, and download a report without leaving the workspace.\n\nAcceptance criteria should clarify success metrics, rollout risk, and who owns ambiguous requirements before delivery planning begins.\n\nEdge cases must explain how missing inputs, failed review runs, and unavailable result artifacts are surfaced to the reviewer.',
      prd_path: '',
      source: '',
      mode: 'quick',
    });
    setSubmitError('');
  }

  function resetWorkspace() {
    const shouldReset = window.confirm('This will clear the current review submission fields. Are you sure?');
    if (!shouldReset) {
      return;
    }

    setForm(initialForm);
    setSubmitError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = buildSubmissionPayload(form);
    const validationMessage = validateSubmission(payload);
    if (validationMessage) {
      setSubmitError(validationMessage);
      return;
    }

    setSubmitState('submitting');
    setSubmitError('');

    try {
      const response = await submitReview(payload);
      setForm(initialForm);
      setSubmitState('idle');
      showToast(`Review submitted successfully. Tracking run ${response.run_id}.`, 'success');
      navigate(`/run/${response.run_id}`);
    } catch (error) {
      const message = formatApiError(error, 'Review submission failed.');
      setSubmitState('idle');
      setSubmitError(message);
      showToast(message, 'error');
    }
  }

  function handleOpenRun(run) {
    const nextRunId = String(run?.run_id ?? '');
    if (!nextRunId) {
      return;
    }

    navigate(`/run/${nextRunId}`);
  }

  return (
    <>
      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Requirement Review Workspace</p>
          <h1>Web workspace for trial and development</h1>
          <p className="hero-copy">
            Feishu is now the primary product entry for end users. This page remains available as a local trial and
            engineering workspace for rapid debugging, smoke checks, and advanced run inspection.
          </p>
          <div className="action-row">
            <Link to="/feishu" className="secondary-button">Open Feishu work entry</Link>
          </div>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Quick Start</span>
          <ol className="quick-start-list" aria-label="Quick start steps">
            <li className="quick-start-step">
              <strong>1. Submit the PRD</strong>
              <p>Use this page to simulate submissions before handing the flow to Feishu users.</p>
            </li>
            <li className="quick-start-step">
              <strong>2. Open the run page</strong>
              <p>Each review has its own URL, useful for troubleshooting result rendering and panel behavior.</p>
            </li>
            <li className="quick-start-step">
              <strong>3. Validate feature changes safely</strong>
              <p>Inspect findings, risks, clarifications, and artifacts before promoting changes to Feishu flow.</p>
            </li>
          </ol>
        </div>
      </header>

      <main className="workspace-grid workspace-grid-home">
        <section className="stack">
          <PanelErrorBoundary panelTitle="提审表单" resetKey={submitState}>
            <ReviewSubmitPanel
              form={form}
              onFieldChange={updateField}
              onSubmit={handleSubmit}
              onReset={resetWorkspace}
              onLoadSample={loadSample}
              isSubmitting={submitState === 'submitting'}
              errorMessage={submitError}
            />
          </PanelErrorBoundary>
        </section>

        <section id="history" className="stack section-anchor-target">
          <PanelErrorBoundary panelTitle="历史列表" resetKey={history.status}>
            <ReviewHistoryPanel
              history={history}
              activeRunId=""
              onRefresh={() => loadRunHistory({ preserveRuns: true })}
              onOpenRun={handleOpenRun}
            />
          </PanelErrorBoundary>
        </section>
      </main>
    </>
  );
}

export default HomePage;
