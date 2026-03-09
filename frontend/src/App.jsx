import { useEffect, useRef, useState } from 'react';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: 'workspace_file',
};

const sourceOptions = [
  { value: 'workspace_file', label: 'Workspace file' },
  { value: 'pasted_notes', label: 'Pasted notes' },
  { value: 'github_ticket', label: 'GitHub ticket' },
  { value: 'notion_export', label: 'Notion export' },
];

const timelineSteps = [
  'Submission captured',
  'Scope normalized',
  'Review agents running',
  'Result package assembled',
];

function buildMockResult(submission) {
  const prdText = submission.prd_text.trim();
  const paragraphs = prdText
    ? prdText.split(/\n\s*\n/).filter(Boolean)
    : [];
  const charCount = prdText.length;
  const hasMetrics = /metric|kpi|target|success/i.test(prdText);
  const mentionsEdgeCases = /edge case|fallback|error|failure/i.test(prdText);
  const mentionsOwner = /owner|team|handoff|approval/i.test(prdText);
  const findings = [
    {
      title: hasMetrics ? 'Success metrics are grounded' : 'Success metrics need sharper definitions',
      severity: hasMetrics ? 'Low' : 'High',
      note: hasMetrics
        ? 'The draft references measurable outcomes, which lowers delivery ambiguity.'
        : 'Add target thresholds or a pass/fail outcome so reviewers can validate implementation quality.',
    },
    {
      title: submission.prd_path.trim()
        ? 'Source path can anchor follow-up review'
        : 'No PRD path was provided',
      severity: submission.prd_path.trim() ? 'Low' : 'Medium',
      note: submission.prd_path.trim()
        ? 'Agents can use the path as a source of truth for linked follow-up analysis.'
        : 'A repository path would help the review workspace cross-check requirements against implementation artifacts.',
    },
    {
      title: mentionsEdgeCases ? 'Risk handling is visible' : 'Edge cases are underspecified',
      severity: mentionsEdgeCases ? 'Low' : 'Medium',
      note: mentionsEdgeCases
        ? 'Fallback and failure behavior appear in the draft, which improves release readiness.'
        : 'Add error handling, fallback behavior, and guardrails before passing this to delivery planning.',
    },
  ];

  const resolvedCount = findings.filter((item) => item.severity === 'Low').length;
  const needsAttention = findings.length - resolvedCount;
  const coverage = Math.min(
    97,
    58 + paragraphs.length * 8 + (submission.prd_path.trim() ? 10 : 0),
  );
  const confidence = Math.min(
    94,
    55 + Math.min(18, Math.floor(charCount / 120)) + (mentionsOwner ? 8 : 0),
  );

  return {
    headline: `${sourceOptions.find((item) => item.value === submission.source)?.label ?? 'Review'} ready for triage`,
    summary:
      charCount > 0
        ? `The workspace found ${needsAttention} area${needsAttention === 1 ? '' : 's'} to tighten before delivery handoff.`
        : 'The workspace completed a light pass and flagged missing context that should be added before review.',
    metrics: [
      { label: 'Coverage', value: `${coverage}%` },
      { label: 'Confidence', value: `${confidence}%` },
      { label: 'Focus areas', value: `${needsAttention}` },
      { label: 'Ready signals', value: `${resolvedCount}` },
    ],
    findings,
    checklist: [
      {
        label: 'Requirement structure parsed',
        detail: paragraphs.length > 0 ? `${paragraphs.length} content block(s) detected` : 'No structured PRD body detected yet',
        state: paragraphs.length > 0 ? 'done' : 'queued',
      },
      {
        label: 'Source traceability linked',
        detail: submission.prd_path.trim() || 'Add a repository path for traceable review comments',
        state: submission.prd_path.trim() ? 'done' : 'active',
      },
      {
        label: 'Delivery risks surfaced',
        detail: mentionsEdgeCases
          ? 'Fallback logic is already described in the draft'
          : 'Review notes suggest adding error and fallback coverage',
        state: needsAttention > 1 ? 'active' : 'done',
      },
    ],
  };
}

function formatTimestamp(value) {
  return value
    ? value.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '--:--';
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [runState, setRunState] = useState({
    status: 'idle',
    runId: null,
    startedAt: null,
    completedAt: null,
    submission: null,
    result: null,
  });
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current);
      }
    };
  }, []);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function loadSample() {
    setForm({
      prd_text:
        'Goal: give reviewers a single workspace to evaluate PRD quality, source coverage, and handoff readiness.\n\nReviewers should be able to submit pasted text or a repository path, see run progress, and quickly scan the highest-risk findings before sending feedback.\n\nEdge case handling should explain what happens when the PRD is incomplete, duplicated, or lacks a clear owner.',
      prd_path: 'docs/product/review-workspace-prd.md',
      source: 'workspace_file',
    });
  }

  function resetRun() {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }

    setRunState({
      status: 'idle',
      runId: null,
      startedAt: null,
      completedAt: null,
      submission: null,
      result: null,
    });
  }

  function handleSubmit(event) {
    event.preventDefault();

    if (timerRef.current) {
      window.clearTimeout(timerRef.current);
    }

    const submission = {
      prd_text: form.prd_text.trimEnd(),
      prd_path: form.prd_path.trim(),
      source: form.source,
    };
    const startedAt = new Date();
    const runId = `RUN-${startedAt.getHours().toString().padStart(2, '0')}${startedAt
      .getMinutes()
      .toString()
      .padStart(2, '0')}-${startedAt.getSeconds().toString().padStart(2, '0')}`;

    setRunState({
      status: 'loading',
      runId,
      startedAt,
      completedAt: null,
      submission,
      result: null,
    });

    timerRef.current = window.setTimeout(() => {
      setRunState((current) => ({
        ...current,
        status: 'complete',
        completedAt: new Date(),
        result: buildMockResult(submission),
      }));
    }, 1800);
  }

  const activeTimelineIndex =
    runState.status === 'idle' ? -1 : runState.status === 'loading' ? 2 : timelineSteps.length - 1;

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="hero">
        <div>
          <p className="eyebrow">Requirement Review Workspace</p>
          <h1>Move from raw PRD intake to review-ready feedback without platform clutter.</h1>
          <p className="hero-copy">
            This workspace keeps the flow anchored around one job: submit a product requirement, watch the
            review run, and triage the result package before delivery planning starts.
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Current workspace mode</span>
          <strong>{runState.status === 'loading' ? 'Active review run' : 'Review prep and triage'}</strong>
          <p>
            Best on desktop for side-by-side review, with a compact mobile layout that keeps the submission
            form and result summary readable.
          </p>
        </div>
      </header>

      <main className="workspace-grid">
        <section className="panel submission-panel">
          <div className="panel-header">
            <div>
              <p className="section-kicker">Submission</p>
              <h2>Queue a review run</h2>
            </div>
            <button type="button" className="ghost-button" onClick={loadSample}>
              Load sample
            </button>
          </div>

          <form className="submission-form" onSubmit={handleSubmit}>
            <label className="field">
              <span>prd_text</span>
              <textarea
                rows="10"
                placeholder="Paste the PRD body, review notes, or an extracted draft here."
                value={form.prd_text}
                onChange={(event) => updateField('prd_text', event.target.value)}
              />
            </label>

            <div className="compact-fields">
              <label className="field">
                <span>prd_path</span>
                <input
                  type="text"
                  placeholder="docs/product/review-workspace-prd.md"
                  value={form.prd_path}
                  onChange={(event) => updateField('prd_path', event.target.value)}
                />
              </label>

              <label className="field">
                <span>source</span>
                <select value={form.source} onChange={(event) => updateField('source', event.target.value)}>
                  {sourceOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="action-row">
              <button type="submit" className="primary-button" disabled={runState.status === 'loading'}>
                {runState.status === 'loading' ? 'Review running...' : 'Start review'}
              </button>
              <button type="button" className="secondary-button" onClick={resetRun}>
                Reset workspace
              </button>
            </div>
          </form>

          <div className="intention-strip">
            <div className="intent-card">
              <span className="intent-label">Flow</span>
              <strong>Submit</strong>
              <p>Collect text, path, and source context in a single pass.</p>
            </div>
            <div className="intent-card">
              <span className="intent-label">Monitor</span>
              <strong>Review</strong>
              <p>Show the run state without burying it behind side navigation.</p>
            </div>
            <div className="intent-card">
              <span className="intent-label">Decide</span>
              <strong>Triage</strong>
              <p>Highlight the result overview first so reviewers can act quickly.</p>
            </div>
          </div>
        </section>

        <section className="stack">
          <article className="panel status-panel" aria-live="polite">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Run status</p>
                <h2>Execution timeline</h2>
              </div>
              <span className={`status-badge status-${runState.status}`}>
                {runState.status === 'idle' && 'Idle'}
                {runState.status === 'loading' && 'Running'}
                {runState.status === 'complete' && 'Complete'}
              </span>
            </div>

            {runState.status === 'idle' ? (
              <div className="empty-state">
                <div className="empty-orb" />
                <h3>No review run yet</h3>
                <p>
                  Start with a draft PRD or load the sample to preview how the workspace reports progress and
                  outcomes.
                </p>
              </div>
            ) : (
              <>
                <div className="status-meta">
                  <div>
                    <span>Run ID</span>
                    <strong>{runState.runId}</strong>
                  </div>
                  <div>
                    <span>Started</span>
                    <strong>{formatTimestamp(runState.startedAt)}</strong>
                  </div>
                  <div>
                    <span>Finished</span>
                    <strong>{formatTimestamp(runState.completedAt)}</strong>
                  </div>
                </div>

                <ol className="timeline">
                  {timelineSteps.map((step, index) => {
                    const isDone = index < activeTimelineIndex || runState.status === 'complete';
                    const isActive = index === activeTimelineIndex && runState.status === 'loading';

                    return (
                      <li
                        key={step}
                        className={`timeline-item${isDone ? ' is-done' : ''}${isActive ? ' is-active' : ''}`}
                      >
                        <span className="timeline-marker" />
                        <div>
                          <strong>{step}</strong>
                          <p>
                            {isDone && 'Step completed and logged for this review run.'}
                            {isActive && 'Currently in progress. The workspace is preparing the next handoff.'}
                            {!isDone && !isActive && 'Waiting for the previous stage to finish first.'}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              </>
            )}
          </article>

          <article className="panel result-panel">
            <div className="panel-header">
              <div>
                <p className="section-kicker">Result overview</p>
                <h2>What needs attention</h2>
              </div>
              {runState.submission && (
                <span className="inline-meta">
                  {sourceOptions.find((item) => item.value === runState.submission.source)?.label}
                </span>
              )}
            </div>

            {runState.status === 'idle' && (
              <div className="empty-state empty-state-soft">
                <div className="empty-grid" />
                <h3>Review results will land here</h3>
                <p>
                  This area is tuned for triage, not generic reporting: headline first, metrics second, then
                  the findings reviewers can act on immediately.
                </p>
              </div>
            )}

            {runState.status === 'loading' && (
              <div className="loading-state">
                <div className="shimmer-block shimmer-title" />
                <div className="metric-grid">
                  <div className="metric-card loading-card" />
                  <div className="metric-card loading-card" />
                  <div className="metric-card loading-card" />
                  <div className="metric-card loading-card" />
                </div>
                <div className="shimmer-list">
                  <div className="shimmer-block shimmer-line" />
                  <div className="shimmer-block shimmer-line short" />
                  <div className="shimmer-block shimmer-line" />
                </div>
              </div>
            )}

            {runState.status === 'complete' && runState.result && (
              <div className="result-content">
                <div className="result-lead">
                  <h3>{runState.result.headline}</h3>
                  <p>{runState.result.summary}</p>
                </div>

                <div className="metric-grid">
                  {runState.result.metrics.map((metric) => (
                    <div key={metric.label} className="metric-card">
                      <span>{metric.label}</span>
                      <strong>{metric.value}</strong>
                    </div>
                  ))}
                </div>

                <div className="result-columns">
                  <div className="findings-list">
                    {runState.result.findings.map((finding) => (
                      <article key={finding.title} className="finding-card">
                        <div className="finding-header">
                          <h4>{finding.title}</h4>
                          <span className={`severity severity-${finding.severity.toLowerCase()}`}>
                            {finding.severity}
                          </span>
                        </div>
                        <p>{finding.note}</p>
                      </article>
                    ))}
                  </div>

                  <div className="checklist-card">
                    <h4>Review checklist</h4>
                    <ul>
                      {runState.result.checklist.map((item) => (
                        <li key={item.label} className={`checklist-item checklist-${item.state}`}>
                          <strong>{item.label}</strong>
                          <span>{item.detail}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}

export default App;
