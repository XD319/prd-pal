import React, { startTransition, useEffect, useEffectEvent, useState } from 'react';
import { fetchReviewResult, fetchReviewStatus, fetchRuns, submitReview } from './api';

const initialForm = {
  prd_text: '',
  prd_path: '',
  source: '',
};

const initialWorkspace = {
  submitState: 'idle',
  resultState: 'idle',
  status: 'idle',
  runId: '',
  statusPayload: null,
  resultPayload: null,
  submitError: '',
  failureMessage: '',
  resultError: '',
};

const initialHistory = {
  status: 'loading',
  runs: [],
  error: '',
  refreshing: false,
};

const pollIntervalMs = 2500;

function normalizeText(value) {
  return String(value ?? '').trim();
}

function normalizeMultiline(value) {
  return String(value ?? '').trimEnd();
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function formatApiError(error, fallbackMessage) {
  if (error?.payload?.detail?.message) {
    return error.payload.detail.message;
  }
  if (typeof error?.payload?.detail === 'string') {
    return error.payload.detail;
  }
  if (typeof error?.payload?.message === 'string') {
    return error.payload.message;
  }
  if (typeof error?.message === 'string' && error.message.trim()) {
    return error.message;
  }
  return fallbackMessage;
}

function formatDateTime(value) {
  if (!value) {
    return '--';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return parsed.toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPercentFromWhole(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric)}%`;
}

function formatRatio(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '--';
  }
  return `${Math.round(numeric * 100)}%`;
}

function formatStatusLabel(status) {
  const normalized = String(status ?? 'idle');
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function excerpt(value, maxLength = 220) {
  const normalized = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 1).trim()}...`;
}

function buildSubmissionPayload(form) {
  const payload = {};
  const source = normalizeText(form.source);
  const prdText = normalizeMultiline(form.prd_text);
  const prdPath = normalizeText(form.prd_path);

  if (source) {
    payload.source = source;
  }
  if (prdText) {
    payload.prd_text = prdText;
  }
  if (prdPath) {
    payload.prd_path = prdPath;
  }

  return payload;
}

function validateSubmission(payload) {
  const hasSource = Boolean(payload.source);
  const hasText = Boolean(payload.prd_text);
  const hasPath = Boolean(payload.prd_path);

  if (hasSource) {
    return '';
  }

  if (hasText === hasPath) {
    return 'Provide `source`, or exactly one of `prd_text` or `prd_path`.';
  }

  return '';
}

function deriveFailureMessage(statusPayload, fallbackMessage = '') {
  return (
    normalizeText(statusPayload?.progress?.error) ||
    normalizeText(statusPayload?.error) ||
    fallbackMessage ||
    'The run stopped before a structured result was available.'
  );
}

function deriveProgressNodes(progress) {
  const nodes = progress?.nodes;
  if (!nodes || typeof nodes !== 'object') {
    return [];
  }

  return Object.entries(nodes).map(([name, node]) => ({
    name,
    status: node?.status ?? 'pending',
    runs: node?.runs ?? 0,
    lastStart: node?.last_start ?? '',
    lastEnd: node?.last_end ?? '',
  }));
}

function deriveFindings(result) {
  const structuredFindings = asArray(result?.parallel_review?.findings);
  if (structuredFindings.length > 0) {
    return structuredFindings.map((item, index) => ({
      id: item.finding_id ?? item.id ?? `finding-${index}`,
      title: item.title ?? `Finding ${index + 1}`,
      detail: item.detail ?? item.description ?? item.summary ?? 'No detail provided.',
      severity: String(item.severity ?? 'medium').toLowerCase(),
    }));
  }

  return asArray(result?.review_results).map((item, index) => ({
    id: item.id ?? `finding-${index}`,
    title: item.id ? `${item.id} review note` : `Finding ${index + 1}`,
    detail: asArray(item.issues).join(' ') || item.suggestions || 'No detail provided.',
    severity: item.is_ambiguous || item.is_clear === false ? 'high' : 'medium',
  }));
}

function deriveRisks(result) {
  const structuredRisks = asArray(result?.review_risk_items);
  if (structuredRisks.length > 0) {
    return structuredRisks.map((item, index) => ({
      id: item.id ?? `risk-${index}`,
      title: item.title ?? `Risk ${index + 1}`,
      detail: item.detail ?? item.description ?? 'No detail provided.',
      severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
    }));
  }

  return asArray(result?.risks).map((item, index) => ({
    id: item.id ?? `risk-${index}`,
    title: item.title ?? `Risk ${index + 1}`,
    detail: item.description ?? 'No detail provided.',
    severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
  }));
}

function deriveOpenQuestions(result) {
  return asArray(result?.review_open_questions).map((item, index) => ({
    id: item.id ?? `question-${index}`,
    question: item.question ?? `Open question ${index + 1}`,
  }));
}

function deriveResultData(resultPayload) {
  if (resultPayload?.result && typeof resultPayload.result === 'object') {
    return resultPayload.result;
  }

  return resultPayload && typeof resultPayload === 'object' ? resultPayload : null;
}

function deriveReviewMode(result) {
  const meta = result?.['parallel-review_meta'] ?? result?.parallel_review_meta ?? {};
  return String(result?.review_mode ?? meta.selected_mode ?? meta.review_mode ?? 'single_review').replace(/_/g, ' ');
}

function deriveResultOverview(result, resultPayload, runId) {
  if (!result) {
    return null;
  }

  const findings = deriveFindings(result);
  const risks = deriveRisks(result);
  const openQuestions = deriveOpenQuestions(result);
  const metrics = result.metrics ?? {};
  const artifactCount = Object.keys(resultPayload?.artifact_paths ?? {}).length;
  const narrative =
    excerpt(result?.['parallel-review_meta']?.manual_review_message) ||
    excerpt(result?.parallel_review_meta?.manual_review_message) ||
    excerpt(result.final_report) ||
    'The review finished and the structured output is ready to inspect.';

  return {
    title: `Run ${runId} is ready for review`,
    narrative,
    chips: [
      `Mode: ${deriveReviewMode(result)}`,
      `${asArray(result.parsed_items).length} parsed requirements`,
      `${artifactCount} artifacts`,
    ],
    metrics: [
      { label: 'Coverage', value: formatRatio(metrics.coverage_ratio) },
      { label: 'High-risk ratio', value: formatRatio(result.high_risk_ratio) },
      { label: 'Findings', value: String(findings.length) },
      { label: 'Open questions', value: String(openQuestions.length) },
    ],
    insights: [
      findings[0]
        ? { kind: findings[0].severity, title: findings[0].title, detail: findings[0].detail }
        : null,
      risks[0]
        ? { kind: risks[0].severity, title: risks[0].title, detail: risks[0].detail }
        : null,
      openQuestions[0]
        ? { kind: 'info', title: openQuestions[0].question, detail: 'Clarify this before moving into delivery planning.' }
        : null,
    ].filter(Boolean),
  };
}

function loadSampleForm() {
  return {
    prd_text:
      'Goal: reviewers should submit one PRD, monitor progress, and inspect findings without leaving the workspace.\n\nAcceptance criteria should state success metrics, delivery risks, and ownership for ambiguous requirements before planning begins.\n\nEdge cases should explain how failed runs and missing artifacts are surfaced to the reviewer.',
    prd_path: '',
    source: '',
  };
}

function SubmissionPanel({ form, isSubmitting, errorMessage, onFieldChange, onLoadSample, onReset, onSubmit }) {
  return (
    <section className="panel intake-panel">
      <div className="panel-topline">
        <p className="panel-kicker">Step 1</p>
        <span className="panel-tag">Review intake</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Submit the PRD you want reviewed</h2>
          <p>Use a canonical `source` when you already have one. Otherwise provide exactly one of `prd_text` or `prd_path`.</p>
        </div>
        <button type="button" className="button ghost" onClick={onLoadSample}>
          Load sample
        </button>
      </div>

      <form className="submission-form" onSubmit={onSubmit}>
        <label className="field">
          <span>prd_text</span>
          <textarea
            rows="12"
            value={form.prd_text}
            placeholder="Paste a PRD draft here when you want the review to run directly against text."
            onChange={(event) => onFieldChange('prd_text', event.target.value)}
          />
        </label>

        <div className="field-grid">
          <label className="field">
            <span>prd_path</span>
            <input
              type="text"
              value={form.prd_path}
              placeholder="docs/product/prd.md"
              onChange={(event) => onFieldChange('prd_path', event.target.value)}
            />
          </label>

          <label className="field">
            <span>source</span>
            <input
              type="text"
              value={form.source}
              placeholder="feishu://prd/123 or docs/sample_prd.md"
              onChange={(event) => onFieldChange('source', event.target.value)}
            />
          </label>
        </div>

        {errorMessage && <div className="feedback error">{errorMessage}</div>}

        <div className="button-row">
          <button type="submit" className="button primary" disabled={isSubmitting}>
            {isSubmitting ? 'Submitting review...' : 'Submit review'}
          </button>
          <button type="button" className="button secondary" onClick={onReset}>
            Reset
          </button>
        </div>
      </form>
    </section>
  );
}

function StatusPanel({ runId, status, statusPayload, failureMessage, history, onRefreshHistory, onOpenRun }) {
  const progress = statusPayload?.progress ?? {};
  const percent = Number(progress.percent ?? 0);
  const nodes = deriveProgressNodes(progress);
  const recentRuns = history.runs.slice(0, 4);

  return (
    <section className="panel status-panel">
      <div className="panel-topline">
        <p className="panel-kicker">Step 2</p>
        <span className={`status-pill status-${status}`}>{formatStatusLabel(status)}</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Track the run while reviewers do their work</h2>
          <p>The status surface keeps the current run visible and makes it easy to reopen recent reviews.</p>
        </div>
        <button type="button" className="button ghost" onClick={onRefreshHistory} disabled={history.refreshing}>
          {history.refreshing ? 'Refreshing...' : 'Refresh runs'}
        </button>
      </div>

      {!runId ? (
        <div className="empty-state">
          <div className="empty-rings" />
          <h3>No active review yet</h3>
          <p>Submit a PRD to start a run. This panel will switch into live progress once a run ID is available.</p>
        </div>
      ) : (
        <div className="status-layout">
          <div className="status-hero">
            <div>
              <span className="eyebrow">Current run</span>
              <h3>{runId}</h3>
            </div>
            <div className="signal-cluster" aria-hidden="true">
              <span className={`signal signal-${status}`} />
              <span className={`signal signal-${status}`} />
              <span className={`signal signal-${status}`} />
            </div>
          </div>

          <div className="status-grid">
            <article className="status-card">
              <span>Progress</span>
              <strong>{formatPercentFromWhole(percent)}</strong>
            </article>
            <article className="status-card">
              <span>Current node</span>
              <strong>{progress.current_node || 'Waiting for orchestration update'}</strong>
            </article>
            <article className="status-card">
              <span>Updated</span>
              <strong>{formatDateTime(progress.updated_at)}</strong>
            </article>
          </div>

          <div className="progress-track" aria-hidden="true">
            <div className="progress-fill" style={{ width: `${Math.max(percent, 6)}%` }} />
          </div>

          {failureMessage && <div className="feedback error">{failureMessage}</div>}

          <div className="timeline">
            {nodes.length === 0 ? (
              <div className="empty-inline">Node-level updates will appear here when the backend reports them.</div>
            ) : (
              nodes.map((node) => (
                <article key={node.name} className="timeline-item">
                  <div className="timeline-marker" />
                  <div>
                    <div className="timeline-head">
                      <strong>{node.name}</strong>
                      <span className={`status-pill status-${node.status}`}>{formatStatusLabel(node.status)}</span>
                    </div>
                    <p>
                      {node.runs > 0 ? `${node.runs} attempt${node.runs === 1 ? '' : 's'}` : 'Not started'}
                      {node.lastEnd ? `, finished ${formatDateTime(node.lastEnd)}` : ''}
                      {!node.lastEnd && node.lastStart ? `, started ${formatDateTime(node.lastStart)}` : ''}
                    </p>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      )}

      <div className="recent-runs">
        <div className="subsection-head">
          <h3>Recent runs</h3>
          <span className="subtle-text">From `GET /api/runs`</span>
        </div>

        {history.status === 'loading' && history.runs.length === 0 ? (
          <div className="loading-state compact">
            <div className="skeleton-line" />
            <div className="skeleton-line short" />
            <div className="skeleton-line" />
          </div>
        ) : recentRuns.length === 0 ? (
          <div className="empty-inline">No recent review runs have been returned yet.</div>
        ) : (
          <div className="run-list">
            {recentRuns.map((run) => (
              <button key={run.run_id} type="button" className="run-chip" onClick={() => onOpenRun(run)}>
                <span>{run.run_id}</span>
                <strong>{formatStatusLabel(run.status ?? 'idle')}</strong>
              </button>
            ))}
          </div>
        )}

        {history.error && <div className="feedback error subdued">{history.error}</div>}
      </div>
    </section>
  );
}

function ResultPanel({ runId, status, resultState, result, resultPayload, resultError, failureMessage }) {
  const overview = deriveResultOverview(result, resultPayload, runId);

  return (
    <section className="panel result-panel">
      <div className="panel-topline">
        <p className="panel-kicker">Step 3</p>
        <span className="panel-tag">Result overview</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Review the outcome before delivery planning starts</h2>
          <p>This area surfaces the review signal first: coverage, risk, the leading finding, and the next unanswered question.</p>
        </div>
        {runId && <span className={`status-pill status-${status}`}>{formatStatusLabel(status)}</span>}
      </div>

      {status === 'failed' ? (
        <div className="empty-state soft">
          <div className="empty-grid" />
          <h3>Result unavailable</h3>
          <p>{failureMessage}</p>
        </div>
      ) : resultState === 'loading' ? (
        <div className="loading-state">
          <div className="skeleton-title" />
          <div className="metric-grid">
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
          </div>
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>
      ) : overview ? (
        <div className="result-stack">
          <div className="result-lead">
            <h3>{overview.title}</h3>
            <p>{overview.narrative}</p>
          </div>

          <div className="metric-grid">
            {overview.metrics.map((metric) => (
              <article key={metric.label} className="metric-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </article>
            ))}
          </div>

          <div className="chip-row">
            {overview.chips.map((chip) => (
              <span key={chip} className="chip">{chip}</span>
            ))}
          </div>

          <div className="insight-grid">
            {overview.insights.length === 0 ? (
              <div className="empty-inline">The run completed, but no structured findings were returned.</div>
            ) : (
              overview.insights.map((insight) => (
                <article key={insight.title} className={`insight-card tone-${insight.kind}`}>
                  <span className="insight-label">{insight.kind}</span>
                  <h4>{insight.title}</h4>
                  <p>{insight.detail}</p>
                </article>
              ))
            )}
          </div>
        </div>
      ) : (
        <div className="empty-state soft">
          <div className="empty-grid" />
          <h3>Result overview is waiting for a completed run</h3>
          <p>Once a run finishes, this panel will fetch `GET /api/review/{'{run_id}'}/result` and surface the highest-signal review output first.</p>
          {resultError && <div className="feedback error">{resultError}</div>}
        </div>
      )}
    </section>
  );
}

function App() {
  const [form, setForm] = useState(initialForm);
  const [workspace, setWorkspace] = useState(initialWorkspace);
  const [history, setHistory] = useState(initialHistory);

  const status = workspace.statusPayload?.status ?? workspace.status;
  const result = deriveResultData(workspace.resultPayload);

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function resetWorkspace() {
    setForm(initialForm);
    setWorkspace(initialWorkspace);
  }

  const loadRunHistory = useEffectEvent(async ({ preserveRuns = true } = {}) => {
    setHistory((current) => ({
      ...current,
      status: preserveRuns && current.runs.length > 0 ? current.status : 'loading',
      refreshing: preserveRuns && current.runs.length > 0,
      error: '',
    }));

    try {
      const payload = await fetchRuns();
      setHistory({
        status: 'ready',
        runs: asArray(payload.runs),
        error: '',
        refreshing: false,
      });
    } catch (error) {
      setHistory((current) => ({
        ...current,
        status: current.runs.length > 0 ? current.status : 'error',
        refreshing: false,
        error: formatApiError(error, 'Run history could not be loaded.'),
      }));
    }
  });

  const pollRunStatus = useEffectEvent(async (runId) => {
    try {
      const statusPayload = await fetchReviewStatus(runId);
      setWorkspace((current) => {
        if (current.runId !== runId) {
          return current;
        }

        return {
          ...current,
          status: statusPayload.status,
          statusPayload,
          failureMessage:
            statusPayload.status === 'failed'
              ? deriveFailureMessage(statusPayload, current.failureMessage)
              : current.failureMessage,
        };
      });
    } catch (error) {
      setWorkspace((current) => {
        if (current.runId !== runId) {
          return current;
        }

        return {
          ...current,
          failureMessage: formatApiError(error, 'Status polling failed.'),
        };
      });
    }
  });

  const fetchCompletedResult = useEffectEvent(async (runId) => {
    setWorkspace((current) => {
      if (current.runId !== runId || current.resultState === 'ready') {
        return current;
      }

      return {
        ...current,
        resultState: 'loading',
        resultError: '',
      };
    });

    try {
      const resultPayload = await fetchReviewResult(runId);
      startTransition(() => {
        setWorkspace((current) => {
          if (current.runId !== runId) {
            return current;
          }

          return {
            ...current,
            resultPayload,
            resultState: 'ready',
            resultError: '',
          };
        });
      });
    } catch (error) {
      const detail = error?.payload?.detail ?? {};
      const message = formatApiError(error, 'The run finished, but the result could not be loaded.');

      setWorkspace((current) => {
        if (current.runId !== runId) {
          return current;
        }

        return {
          ...current,
          resultState: 'error',
          resultError: message,
          status: detail.status === 'failed' ? 'failed' : current.status,
          failureMessage: detail.status === 'failed' ? message : current.failureMessage,
        };
      });
    }
  });

  useEffect(() => {
    void loadRunHistory({ preserveRuns: false });
  }, [loadRunHistory]);

  useEffect(() => {
    if (!workspace.runId || !['queued', 'running'].includes(status)) {
      return undefined;
    }

    const handle = window.setTimeout(() => {
      void pollRunStatus(workspace.runId);
    }, pollIntervalMs);

    return () => {
      window.clearTimeout(handle);
    };
  }, [workspace.runId, status, pollRunStatus]);

  useEffect(() => {
    if (!workspace.runId || status !== 'completed' || workspace.resultPayload || workspace.resultState === 'loading') {
      return;
    }

    void fetchCompletedResult(workspace.runId);
  }, [workspace.runId, status, workspace.resultPayload, workspace.resultState, fetchCompletedResult]);

  useEffect(() => {
    if (!workspace.runId || !['completed', 'failed'].includes(status)) {
      return;
    }

    void loadRunHistory({ preserveRuns: true });
  }, [workspace.runId, status, loadRunHistory]);

  async function handleSubmit(event) {
    event.preventDefault();

    const payload = buildSubmissionPayload(form);
    const validationMessage = validateSubmission(payload);
    if (validationMessage) {
      setWorkspace((current) => ({
        ...current,
        submitError: validationMessage,
      }));
      return;
    }

    setWorkspace({
      ...initialWorkspace,
      submitState: 'submitting',
      submitError: '',
    });

    try {
      const response = await submitReview(payload);

      setWorkspace({
        ...initialWorkspace,
        runId: response.run_id,
        status: 'queued',
        statusPayload: {
          run_id: response.run_id,
          status: 'queued',
          progress: {
            percent: 0,
            current_node: '',
            nodes: {},
            updated_at: new Date().toISOString(),
          },
        },
      });

      void loadRunHistory({ preserveRuns: true });
      await pollRunStatus(response.run_id);
    } catch (error) {
      setWorkspace((current) => ({
        ...current,
        submitState: 'idle',
        submitError: formatApiError(error, 'Review submission failed.'),
      }));
    }
  }

  async function handleOpenRun(run) {
    const runId = String(run?.run_id ?? '');
    if (!runId) {
      return;
    }

    setWorkspace({
      ...initialWorkspace,
      runId,
      status: run.status ?? 'idle',
      statusPayload: {
        run_id: runId,
        status: run.status ?? 'idle',
        progress: {
          percent: run.status === 'completed' ? 100 : 0,
          current_node: '',
          nodes: {},
          updated_at: run.updated_at ?? run.created_at ?? '',
        },
      },
    });

    await pollRunStatus(runId);
  }

  return (
    <div className="app-shell">
      <div className="background-glow glow-left" />
      <div className="background-glow glow-right" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Review Workspace MVP</p>
          <h1>Keep requirement review intake, run tracking, and outcome inspection in one place.</h1>
          <p>
            This frontend stays review-first. There are no platform menus or CRUD furniture here, only the surfaces needed to
            submit a PRD, follow the run, and decide what needs clarification before planning continues.
          </p>
        </div>

        <aside className="hero-aside">
          <span className="hero-tag">Review flow</span>
          <ol>
            <li>Submit one PRD through `prd_text`, `prd_path`, or `source`.</li>
            <li>Track the active run and reopen recent runs when needed.</li>
            <li>Inspect the result summary before delivery planning starts.</li>
          </ol>
        </aside>
      </header>

      <main className="workspace-layout">
        <div className="left-column">
          <SubmissionPanel
            form={form}
            isSubmitting={workspace.submitState === 'submitting'}
            errorMessage={workspace.submitError}
            onFieldChange={updateField}
            onLoadSample={() => setForm(loadSampleForm())}
            onReset={resetWorkspace}
            onSubmit={handleSubmit}
          />

          <StatusPanel
            runId={workspace.runId}
            status={status}
            statusPayload={workspace.statusPayload}
            failureMessage={workspace.failureMessage}
            history={history}
            onRefreshHistory={() => loadRunHistory({ preserveRuns: true })}
            onOpenRun={handleOpenRun}
          />
        </div>

        <div className="right-column">
          <ResultPanel
            runId={workspace.runId}
            status={status}
            resultState={workspace.resultState}
            result={result}
            resultPayload={workspace.resultPayload}
            resultError={workspace.resultError}
            failureMessage={workspace.failureMessage}
          />
        </div>
      </main>
    </div>
  );
}

export default App;
