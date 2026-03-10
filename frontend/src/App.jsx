import { startTransition, useEffect, useEffectEvent, useState } from 'react';
import {
  downloadReportArtifact,
  fetchReviewResult,
  fetchReviewStatus,
  fetchRuns,
  submitReview,
} from './api';

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
  submission: null,
  statusPayload: null,
  resultPayload: null,
  submitError: '',
  failureMessage: '',
  resultError: '',
  downloadFormat: '',
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

function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
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
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatPercent(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric * 100)}%`;
}

function formatPercentFromWhole(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric)}%`;
}

function formatStatusLabel(status) {
  const normalized = String(status ?? 'idle');
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function excerpt(value, maxLength = 200) {
  const normalized = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 1).trim()}...`;
}

function joinList(values) {
  return values.filter(Boolean).join(', ');
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function severityRank(value) {
  const normalized = String(value ?? '').toLowerCase();
  if (normalized === 'high') {
    return 3;
  }
  if (normalized === 'medium') {
    return 2;
  }
  if (normalized === 'low') {
    return 1;
  }
  return 0;
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
    return 'Provide source, or exactly one of prd_text or prd_path.';
  }

  return '';
}

function deriveModeLabel(result) {
  const meta = result?.['parallel-review_meta'] ?? result?.parallel_review_meta ?? {};
  const mode = String(result?.review_mode ?? meta.selected_mode ?? meta.review_mode ?? 'single_review');
  if (mode === 'parallel_review') {
    return 'Parallel review';
  }
  if (mode === 'single_review') {
    return 'Single review';
  }
  return mode.replace(/_/g, ' ');
}

function deriveFindings(result) {
  const parallelFindings = asArray(result?.parallel_review?.findings);
  if (parallelFindings.length > 0) {
    return parallelFindings
      .map((item, index) => ({
        id: item.finding_id ?? item.id ?? `finding-${index}`,
        title: item.title ?? `Finding ${index + 1}`,
        detail: item.detail ?? item.description ?? item.summary ?? 'No detail provided.',
        severity: String(item.severity ?? 'medium').toLowerCase(),
        category: item.category ?? 'review',
        reviewers: asArray(item.reviewers),
        assignee: item.assignee ?? '',
        action: item.suggested_action ?? '',
      }))
      .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
  }

  return asArray(result?.review_results)
    .map((item, index) => {
      const issues = asArray(item.issues).filter(Boolean);
      const severity = item.is_ambiguous || item.is_clear === false || item.is_testable === false
        ? issues.length > 1
          ? 'high'
          : 'medium'
        : 'low';
      return {
        id: item.id ?? `finding-${index}`,
        title: item.id ? `${item.id} review note` : `Finding ${index + 1}`,
        detail:
          issues.length > 0
            ? issues.join(' ')
            : item.suggestions || 'The reviewer did not flag any blocking issues.',
        severity,
        category: 'review_quality',
        reviewers: ['single_reviewer'],
        assignee: '',
        action: item.suggestions ?? '',
      };
    })
    .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
}

function deriveRisks(result) {
  const reviewRisks = asArray(result?.review_risk_items);
  if (reviewRisks.length > 0) {
    return reviewRisks
      .map((item, index) => ({
        id: item.id ?? item.title ?? `risk-${index}`,
        title: item.title ?? `Risk ${index + 1}`,
        detail: item.detail ?? item.description ?? 'No risk detail provided.',
        severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
        category: item.category ?? 'delivery',
        mitigation: item.mitigation ?? '',
        reviewers: asArray(item.reviewers),
      }))
      .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
  }

  return asArray(result?.risks).map((item, index) => ({
    id: item.id ?? `risk-${index}`,
    title: item.title ?? item.id ?? `Risk ${index + 1}`,
    detail: item.description ?? 'No risk detail provided.',
    severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
    category: item.category ?? 'delivery',
    mitigation: item.mitigation ?? '',
    reviewers: [],
  }));
}

function deriveOpenQuestions(result) {
  return asArray(result?.review_open_questions).map((item, index) => ({
    id: item.id ?? item.question ?? `question-${index}`,
    question: item.question ?? `Open question ${index + 1}`,
    detail: asArray(item.issues).join(' '),
    reviewers: asArray(item.reviewers),
  }));
}

function deriveSummary(result, runId, statusPayload, resultPayload) {
  if (!result) {
    return {
      title: 'Result overview is waiting for a completed run',
      narrative:
        'Once the run finishes, this workspace will pull the structured review result and surface the highest-signal issues first.',
      metrics: [],
      chips: [],
    };
  }

  const findings = deriveFindings(result);
  const risks = deriveRisks(result);
  const questions = deriveOpenQuestions(result);
  const metrics = result.metrics ?? {};
  const meta = result['parallel-review_meta'] ?? result.parallel_review_meta ?? {};
  const artifactCount = Object.keys(resultPayload?.artifact_paths ?? {}).length;
  const narrative =
    meta.manual_review_message ||
    excerpt(result.final_report, 220) ||
    'The review finished successfully and structured output is ready for inspection.';

  return {
    title: `Run ${runId} completed`,
    narrative,
    metrics: [
      { label: 'Coverage', value: formatPercent(Number(metrics.coverage_ratio ?? 0)) },
      { label: 'High-risk ratio', value: formatPercent(Number(result.high_risk_ratio ?? 0)) },
      { label: 'Findings', value: `${findings.length}` },
      { label: 'Artifacts', value: `${artifactCount}` },
    ],
    chips: [
      deriveModeLabel(result),
      pluralize(asArray(result.parsed_items).length, 'requirement'),
      pluralize(findings.length, 'finding'),
      pluralize(risks.length, 'risk'),
      pluralize(questions.length, 'open question'),
      statusPayload?.status ? `Status: ${statusPayload.status}` : '',
    ].filter(Boolean),
  };
}

function deriveFailureMessage(statusPayload, fallbackMessage = '') {
  return (
    normalizeText(statusPayload?.progress?.error) ||
    normalizeText(statusPayload?.error) ||
    fallbackMessage ||
    'The review run failed before the structured result became available.'
  );
}

function deriveNodes(progress) {
  const nodes = progress?.nodes;
  if (!nodes || typeof nodes !== 'object') {
    return [];
  }

  return Object.entries(nodes)
    .map(([name, node]) => ({
      name,
      status: node?.status ?? 'pending',
      runs: node?.runs ?? 0,
      lastStart: node?.last_start ?? '',
      lastEnd: node?.last_end ?? '',
    }))
    .sort((left, right) => {
      const order = ['running', 'failed', 'completed', 'pending'];
      return order.indexOf(left.status) - order.indexOf(right.status);
    });
}

function describeHistoryRun(run) {
  const artifactPresence = run?.artifact_presence ?? {};
  const status = String(run?.status ?? 'running');
  const hasResult = Boolean(artifactPresence.report_json);

  return {
    status,
    statusLabel: formatStatusLabel(status),
    detail: hasResult
      ? 'Structured review output is available to inspect.'
      : status === 'failed'
        ? 'The run ended without a ready result artifact.'
        : 'The review is still producing or finalizing artifacts.',
    actionLabel: hasResult ? 'Open result details' : 'Open run details',
    hasResult,
  };
}

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
function ReviewHistoryPanel({ history, activeRunId, onRefresh, onOpenRun }) {
  const recentRuns = history.runs.slice(0, 8);

  return (
    <section className="panel review-history-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">Review History</p>
          <h2>Recent runs</h2>
        </div>
        <button type="button" className="ghost-button" onClick={onRefresh} disabled={history.refreshing}>
          {history.refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {history.status === 'loading' && history.runs.length === 0 ? (
        <div className="loading-state loading-state-history">
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
        </div>
      ) : history.status === 'error' && history.runs.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>Run history is unavailable</h3>
          <p>{history.error}</p>
        </div>
      ) : recentRuns.length === 0 ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-grid" />
          <h3>No review runs yet</h3>
          <p>Completed and in-progress review runs from <code>GET /api/runs</code> will appear here for quick follow-up.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.status === 'error' && <div className="feedback-banner feedback-error">{history.error}</div>}

          {recentRuns.map((run) => {
            const summary = describeHistoryRun(run);
            const isActive = run.run_id === activeRunId;

            return (
              <article key={run.run_id} className={`history-card${isActive ? ' history-card-active' : ''}`}>
                <div className="history-header">
                  <div>
                    <span className="history-kicker">{run.run_id}</span>
                    <h3>{summary.hasResult ? 'Result ready for inspection' : 'Review run in motion'}</h3>
                  </div>
                  <span className={`status-badge status-${summary.status}`}>{summary.statusLabel}</span>
                </div>

                <p className="history-note">{summary.detail}</p>

                <div className="history-meta">
                  <div>
                    <span>Created</span>
                    <strong>{formatDateTime(run.created_at)}</strong>
                  </div>
                  <div>
                    <span>Updated</span>
                    <strong>{formatDateTime(run.updated_at)}</strong>
                  </div>
                </div>

                <div className="history-actions">
                  <button type="button" className="secondary-button" onClick={() => onOpenRun(run)}>
                    {summary.actionLabel}
                  </button>
                  <span className="inline-meta inline-meta-soft">
                    {run.artifact_presence?.report_json ? 'Report artifact ready' : 'Waiting on report artifact'}
                  </span>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}

function RunProgressCard({ runId, status, statusPayload, failureMessage }) {
  const progress = statusPayload?.progress ?? {};
  const nodes = deriveNodes(progress);
  const statusLabel = formatStatusLabel(status);

  return (
    <section className="panel run-progress-card">
      <div className="panel-header">
        <div>
          <p className="section-kicker">RunProgressCard</p>
          <h2>Run progress</h2>
        </div>
        <span className={`status-badge status-${status}`}>{statusLabel}</span>
      </div>

      {!runId ? (
        <div className="empty-state empty-state-compact">
          <div className="empty-orb" />
          <h3>No run in focus</h3>
          <p>Submit a PRD or pick a recent run to inspect progress and result details here.</p>
        </div>
      ) : (
        <div className="status-stack">
          <div className="status-meta status-meta-two-up">
            <div>
              <span>Run ID</span>
              <strong>{runId}</strong>
            </div>
            <div>
              <span>Percent complete</span>
              <strong>{formatPercentFromWhole(progress.percent ?? 0)}</strong>
            </div>
            <div>
              <span>Current node</span>
              <strong>{progress.current_node || 'Waiting for next stage'}</strong>
            </div>
            <div>
              <span>Updated</span>
              <strong>{formatDateTime(progress.updated_at)}</strong>
            </div>
          </div>

          {failureMessage && <div className="feedback-banner feedback-error">{failureMessage}</div>}

          <div className="progress-bar-shell" aria-hidden="true">
            <div className="progress-bar-fill" style={{ width: `${Math.max(8, Number(progress.percent ?? 0))}%` }} />
          </div>

          <div className="node-list">
            {nodes.length === 0 ? (
              <div className="empty-inline">Node-level progress has not been reported yet.</div>
            ) : (
              nodes.map((node) => (
                <article key={node.name} className={`node-card node-${node.status}`}>
                  <div className="node-header">
                    <strong>{node.name}</strong>
                    <span className={`node-pill node-pill-${node.status}`}>{node.status}</span>
                  </div>
                  <p>
                    {node.runs > 0 ? `${pluralize(node.runs, 'attempt')}` : 'Not started'}
                    {node.lastEnd ? ` - finished ${formatDateTime(node.lastEnd)}` : ''}
                    {!node.lastEnd && node.lastStart ? ` - started ${formatDateTime(node.lastStart)}` : ''}
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function ReviewSummaryPanel({ runId, status, result, statusPayload, resultPayload, resultState, failureMessage, resultError }) {
  const summary = deriveSummary(result, runId, statusPayload, resultPayload);

  return (
    <section className="panel review-summary-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">ReviewSummaryPanel</p>
          <h2>Result overview</h2>
        </div>
        {result && <span className="inline-meta">{deriveModeLabel(result)}</span>}
      </div>

      {status === 'failed' ? (
        <div className="empty-state empty-state-soft">
          <div className="empty-grid" />
          <h3>Run failed before review output was ready</h3>
          <p>{failureMessage}</p>
        </div>
      ) : resultState === 'loading' ? (
        <div className="loading-state loading-state-summary">
          <div className="shimmer-block shimmer-title" />
          <div className="metric-grid">
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
            <div className="metric-card loading-card" />
          </div>
        </div>
      ) : result ? (
        <div className="result-content">
          <div className="result-lead">
            <h3>{summary.title}</h3>
            <p>{summary.narrative}</p>
          </div>

          <div className="metric-grid">
            {summary.metrics.map((metric) => (
              <div key={metric.label} className="metric-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </div>
            ))}
          </div>

          <div className="chip-row">
            {summary.chips.map((chip) => (
              <span key={chip} className="inline-meta inline-meta-soft">{chip}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-state empty-state-soft">
          <div className="empty-grid" />
          <h3>Review summary will land here</h3>
          <p>
            The workspace will pull structured output from <code>GET /api/review/{'{run_id}'}/result</code> as soon as the run completes.
          </p>
          {resultError && <div className="feedback-banner feedback-error">{resultError}</div>}
        </div>
      )}
    </section>
  );
}

function FindingsPanel({ result, status, resultState }) {
  const findings = result ? deriveFindings(result) : [];

  return (
    <section className="panel findings-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">FindingsPanel</p>
          <h2>Findings</h2>
        </div>
        <span className="inline-meta">{pluralize(findings.length, 'item')}</span>
      </div>

      {status === 'completed' && resultState === 'loading' ? (
        <div className="loading-state loading-state-list">
          <div className="shimmer-block shimmer-line" />
          <div className="shimmer-block shimmer-line short" />
          <div className="shimmer-block shimmer-line" />
        </div>
      ) : findings.length === 0 ? (
        <div className="empty-inline">No findings are available for this run yet.</div>
      ) : (
        <div className="list-stack">
          {findings.map((finding) => (
            <article key={finding.id} className="finding-card">
              <div className="finding-header">
                <h4>{finding.title}</h4>
                <span className={`severity severity-${finding.severity}`}>{finding.severity}</span>
              </div>
              <p>{finding.detail}</p>
              <div className="detail-row">
                {finding.category && <span>{finding.category}</span>}
                {finding.reviewers.length > 0 && <span>{joinList(finding.reviewers)}</span>}
                {finding.assignee && <span>Owner: {finding.assignee}</span>}
              </div>
              {finding.action && <div className="subtle-note">Suggested action: {finding.action}</div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
function RisksPanel({ result }) {
  const risks = result ? deriveRisks(result) : [];

  return (
    <section className="panel risks-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">RisksPanel</p>
          <h2>Risks</h2>
        </div>
        <span className="inline-meta">{pluralize(risks.length, 'item')}</span>
      </div>

      {risks.length === 0 ? (
        <div className="empty-inline">No structured risks were returned for this run.</div>
      ) : (
        <div className="list-stack">
          {risks.map((risk) => (
            <article key={risk.id} className="finding-card risk-card">
              <div className="finding-header">
                <h4>{risk.title}</h4>
                <span className={`severity severity-${risk.severity}`}>{risk.severity}</span>
              </div>
              <p>{risk.detail}</p>
              <div className="detail-row">
                {risk.category && <span>{risk.category}</span>}
                {risk.reviewers.length > 0 && <span>{joinList(risk.reviewers)}</span>}
              </div>
              {risk.mitigation && <div className="subtle-note">Mitigation: {risk.mitigation}</div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function OpenQuestionsPanel({ result }) {
  const questions = result ? deriveOpenQuestions(result) : [];

  return (
    <section className="panel open-questions-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">OpenQuestionsPanel</p>
          <h2>Open questions</h2>
        </div>
        <span className="inline-meta">{pluralize(questions.length, 'item')}</span>
      </div>

      {questions.length === 0 ? (
        <div className="empty-inline">No open questions were generated for this run.</div>
      ) : (
        <div className="list-stack">
          {questions.map((question) => (
            <article key={question.id} className="question-card">
              <h4>{question.question}</h4>
              {question.detail && <p>{question.detail}</p>}
              {question.reviewers.length > 0 && (
                <div className="detail-row">
                  <span>{joinList(question.reviewers)}</span>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ArtifactDownloadPanel({ runId, status, resultPayload, statusPayload, downloadFormat, onDownload }) {
  const artifactPaths = resultPayload?.artifact_paths ?? statusPayload?.report_paths ?? {};
  const artifactKeys = Object.keys(artifactPaths);
  const canDownload = Boolean(runId) && status === 'completed';

  return (
    <section className="panel artifact-download-panel">
      <div className="panel-header">
        <div>
          <p className="section-kicker">ArtifactDownloadPanel</p>
          <h2>Artifacts</h2>
        </div>
        <span className="inline-meta">{pluralize(artifactKeys.length, 'path')}</span>
      </div>

      <p className="panel-copy">
        Download the canonical review report as Markdown or JSON after the run completes. Additional artifact paths are listed for inspection.
      </p>

      <div className="action-row">
        <button
          type="button"
          className="primary-button"
          disabled={!canDownload || downloadFormat === 'md'}
          onClick={() => onDownload('md')}
        >
          {downloadFormat === 'md' ? 'Downloading Markdown...' : 'Download Markdown'}
        </button>
        <button
          type="button"
          className="secondary-button"
          disabled={!canDownload || downloadFormat === 'json'}
          onClick={() => onDownload('json')}
        >
          {downloadFormat === 'json' ? 'Downloading JSON...' : 'Download JSON'}
        </button>
      </div>

      {!canDownload && <div className="empty-inline">Artifacts unlock after a run completes successfully.</div>}

      {artifactKeys.length > 0 && (
        <div className="artifact-list">
          {artifactKeys.map((key) => (
            <div key={key} className="artifact-row">
              <span>{key}</span>
              <code>{artifactPaths[key]}</code>
            </div>
          ))}
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
  const result = workspace.resultPayload?.result && typeof workspace.resultPayload.result === 'object'
    ? workspace.resultPayload.result
    : null;

  function updateField(field, value) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function loadSample() {
    setForm({
      prd_text:
        'Goal: reviewers should submit one PRD, monitor progress, inspect structured findings, and download a report without leaving the workspace.\n\nAcceptance criteria should clarify success metrics, rollout risk, and who owns ambiguous requirements before delivery planning begins.\n\nEdge cases must explain how missing inputs, failed review runs, and unavailable result artifacts are surfaced to the reviewer.',
      prd_path: '',
      source: '',
    });
  }

  function resetWorkspace() {
    setWorkspace(initialWorkspace);
    setForm(initialForm);
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
      const message = formatApiError(error, 'Review history could not be loaded.');
      setHistory((current) => ({
        ...current,
        status: current.runs.length > 0 ? current.status : 'error',
        refreshing: false,
        error: message,
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
          failureMessage: statusPayload.status === 'failed'
            ? deriveFailureMessage(statusPayload)
            : current.failureMessage,
        };
      });
    } catch (error) {
      const message = formatApiError(error, 'Status polling failed.');
      setWorkspace((current) => {
        if (current.runId !== runId) {
          return current;
        }
        return {
          ...current,
          failureMessage: message,
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
      const message = formatApiError(error, 'The run finished, but the structured result could not be loaded.');
      const detail = error?.payload?.detail ?? {};
      setWorkspace((current) => {
        if (current.runId !== runId) {
          return current;
        }
        return {
          ...current,
          resultState: 'error',
          resultError: message,
          status: detail.status === 'failed' ? 'failed' : current.status,
          failureMessage: detail.status === 'failed'
            ? message
            : current.failureMessage,
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
      submission: payload,
    });

    try {
      const response = await submitReview(payload);
      const queuedStatus = {
        run_id: response.run_id,
        status: 'queued',
        progress: {
          percent: 0,
          current_node: '',
          nodes: {},
          updated_at: new Date().toISOString(),
          error: '',
        },
        report_paths: {},
      };

      setWorkspace({
        ...initialWorkspace,
        runId: response.run_id,
        submission: payload,
        status: 'queued',
        statusPayload: queuedStatus,
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
          error: '',
        },
        report_paths: {},
      },
    });

    await pollRunStatus(runId);
  }

  async function handleDownload(format) {
    if (!workspace.runId) {
      return;
    }

    setWorkspace((current) => ({
      ...current,
      downloadFormat: format,
    }));

    try {
      await downloadReportArtifact(workspace.runId, format);
    } catch (error) {
      const message = formatApiError(error, `Failed to download the ${format.toUpperCase()} report.`);
      setWorkspace((current) => ({
        ...current,
        failureMessage: current.failureMessage || message,
      }));
    } finally {
      setWorkspace((current) => ({
        ...current,
        downloadFormat: '',
      }));
    }
  }

  return (
    <div className="app-shell">
      <div className="ambient ambient-left" />
      <div className="ambient ambient-right" />

      <header className="hero hero-tight">
        <div>
          <p className="eyebrow">Requirement Review Workspace</p>
          <h1>Review intake, history, progress, and result inspection in one focused workspace.</h1>
          <p className="hero-copy">
            This phase stays review-first: submit a PRD, reopen recent runs, inspect progress, and pull the result package without adding approval or orchestration controls.
          </p>
        </div>

        <div className="hero-panel">
          <span className="hero-label">Connected endpoints</span>
          <strong>POST /api/review and GET /api/runs</strong>
          <p>The detail view continues to rely on status, result, and report endpoints, while the history view keeps recent review work within easy reach.</p>
        </div>
      </header>

      <main className="workspace-grid workspace-grid-expanded">
        <section className="stack">
          <ReviewSubmitPanel
            form={form}
            onFieldChange={updateField}
            onSubmit={handleSubmit}
            onReset={resetWorkspace}
            onLoadSample={loadSample}
            isSubmitting={workspace.submitState === 'submitting'}
            errorMessage={workspace.submitError}
          />

          <ReviewHistoryPanel
            history={history}
            activeRunId={workspace.runId}
            onRefresh={() => loadRunHistory({ preserveRuns: true })}
            onOpenRun={handleOpenRun}
          />

          <RunProgressCard
            runId={workspace.runId}
            status={status}
            statusPayload={workspace.statusPayload}
            failureMessage={workspace.failureMessage}
          />

          <ArtifactDownloadPanel
            runId={workspace.runId}
            status={status}
            resultPayload={workspace.resultPayload}
            statusPayload={workspace.statusPayload}
            downloadFormat={workspace.downloadFormat}
            onDownload={handleDownload}
          />
        </section>

        <section className="stack stack-wide">
          <ReviewSummaryPanel
            runId={workspace.runId}
            status={status}
            result={result}
            statusPayload={workspace.statusPayload}
            resultPayload={workspace.resultPayload}
            resultState={workspace.resultState}
            failureMessage={workspace.failureMessage}
            resultError={workspace.resultError}
          />

          <div className="panel-grid panel-grid-two-up">
            <FindingsPanel result={result} status={status} resultState={workspace.resultState} />
            <RisksPanel result={result} />
          </div>

          <OpenQuestionsPanel result={result} />
        </section>
      </main>
    </div>
  );
}

export default App;
