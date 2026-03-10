import React, { startTransition, useEffect, useEffectEvent, useState } from 'react';
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
  statusPayload: null,
  resultPayload: null,
  submitError: '',
  failureMessage: '',
  resultError: '',
  downloadFormat: '',
  artifactError: '',
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

function joinList(values) {
  return values.filter(Boolean).join(', ');
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
  const status = String(run?.status ?? 'idle');
  const hasResult = Boolean(run?.artifact_presence?.report_json) || status === 'completed';

  return {
    status,
    statusLabel: formatStatusLabel(status),
    createdAt: formatDateTime(run?.created_at),
    detail: hasResult
      ? 'Structured review output is available to inspect.'
      : status === 'failed'
        ? 'The run ended without a ready result artifact.'
        : 'The run is still producing or finalizing review output.',
    actionLabel: hasResult ? 'Open result details' : 'Open run details',
  };
}

function deriveFindings(result) {
  const structuredFindings = asArray(result?.parallel_review?.findings);
  if (structuredFindings.length > 0) {
    return structuredFindings
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
    .map((item, index) => ({
      id: item.id ?? `finding-${index}`,
      title: item.id ? `${item.id} review note` : `Finding ${index + 1}`,
      detail: asArray(item.issues).join(' ') || item.suggestions || 'No detail provided.',
      severity: item.is_ambiguous || item.is_clear === false || item.is_testable === false ? 'high' : 'medium',
      category: 'review_quality',
      reviewers: ['single_reviewer'],
      assignee: '',
      action: item.suggestions ?? '',
    }))
    .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
}

function deriveRisks(result) {
  const structuredRisks = asArray(result?.review_risk_items);
  if (structuredRisks.length > 0) {
    return structuredRisks
      .map((item, index) => ({
        id: item.id ?? `risk-${index}`,
        title: item.title ?? `Risk ${index + 1}`,
        detail: item.detail ?? item.description ?? 'No detail provided.',
        severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
        category: item.category ?? 'delivery',
        mitigation: item.mitigation ?? '',
        reviewers: asArray(item.reviewers),
      }))
      .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
  }

  return asArray(result?.risks)
    .map((item, index) => ({
      id: item.id ?? `risk-${index}`,
      title: item.title ?? `Risk ${index + 1}`,
      detail: item.description ?? 'No detail provided.',
      severity: String(item.severity ?? item.impact ?? 'medium').toLowerCase(),
      category: item.category ?? 'delivery',
      mitigation: item.mitigation ?? '',
      reviewers: [],
    }))
    .sort((left, right) => severityRank(right.severity) - severityRank(left.severity));
}

function deriveOpenQuestions(result) {
  return asArray(result?.review_open_questions).map((item, index) => ({
    id: item.id ?? `question-${index}`,
    question: item.question ?? `Open question ${index + 1}`,
    detail: asArray(item.issues).join(' '),
    reviewers: asArray(item.reviewers),
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

function deriveResultOverview(result, resultPayload, runId, statusPayload) {
  if (!result) {
    return {
      title: 'Result overview is waiting for a completed run',
      narrative: 'When a run completes, the structured review result will land here with the highest-signal issues first.',
      metrics: [],
      chips: [],
    };
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
    metrics: [
      { label: 'Coverage', value: formatRatio(metrics.coverage_ratio) },
      { label: 'High-risk ratio', value: formatRatio(result.high_risk_ratio) },
      { label: 'Findings', value: String(findings.length) },
      { label: 'Open questions', value: String(openQuestions.length) },
    ],
    chips: [
      `Mode: ${deriveReviewMode(result)}`,
      `${asArray(result.parsed_items).length} parsed requirements`,
      `${risks.length} risks`,
      `${artifactCount} artifacts`,
      statusPayload?.status ? `Status: ${statusPayload.status}` : '',
    ].filter(Boolean),
  };
}

function loadSampleForm() {
  return {
    prd_text:
      'Goal: reviewers should submit one PRD, monitor progress, inspect findings, and download the result package without leaving the workspace.\n\nAcceptance criteria should state success metrics, delivery risks, and ownership for ambiguous requirements before planning begins.\n\nEdge cases should explain how failed runs and missing artifacts are surfaced to the reviewer.',
    prd_path: '',
    source: '',
  };
}

function ReviewSubmitPanel({ form, isSubmitting, errorMessage, onFieldChange, onLoadSample, onReset, onSubmit }) {
  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">ReviewSubmitPanel</p>
        <span className="panel-tag">Start a run</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Submit the PRD you want reviewed</h2>
          <p>Provide a canonical `source` when you already have one. Otherwise use exactly one of `prd_text` or `prd_path`.</p>
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
            placeholder="Paste a PRD draft when you want to review text directly."
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
              placeholder="docs/sample_prd.md or connector source"
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
            Reset workspace
          </button>
        </div>
      </form>
    </section>
  );
}

function RunProgressCard({ runId, status, statusPayload, failureMessage }) {
  const progress = statusPayload?.progress ?? {};
  const percent = Number(progress.percent ?? 0);
  const nodes = deriveProgressNodes(progress);

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">RunProgressCard</p>
        <span className={`status-pill status-${status}`}>{formatStatusLabel(status)}</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Track the review run</h2>
          <p>Poll the active run until it completes or fails, with clear node-level progress and failure messaging.</p>
        </div>
      </div>

      {!runId ? (
        <div className="empty-state">
          <div className="empty-rings" />
          <h3>No active review yet</h3>
          <p>Submit a PRD to start a run. Progress, status, and polling updates will appear here.</p>
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

          <div className="status-grid status-grid-three">
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
              <div className="empty-inline">Node-level progress will appear here when the backend reports it.</div>
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
    </section>
  );
}

function ReviewHistoryPanel({ history, activeRunId, onRefreshHistory, onOpenRun }) {
  const recentRuns = history.runs.slice(0, 8);

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">ReviewHistoryPanel</p>
        <span className="panel-tag">Recent review runs</span>
      </div>

      <div className="panel-heading">
        <div>
          <h2>Review history</h2>
          <p>Reopen recent review runs without leaving the workspace. This phase stays focused on review intake and inspection only.</p>
        </div>
        <button type="button" className="button ghost" onClick={onRefreshHistory} disabled={history.refreshing}>
          {history.refreshing ? 'Refreshing...' : 'Refresh runs'}
        </button>
      </div>

      {history.status === 'loading' && history.runs.length === 0 ? (
        <div className="loading-state compact loading-state-list">
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
          <div className="history-skeleton-card" />
        </div>
      ) : history.status === 'error' && history.runs.length === 0 ? (
        <div className="empty-state compact">
          <div className="empty-grid" />
          <h3>Review history is unavailable</h3>
          <p>{history.error}</p>
        </div>
      ) : recentRuns.length === 0 ? (
        <div className="empty-state compact">
          <div className="empty-rings" />
          <h3>No review runs yet</h3>
          <p>Recent runs from `GET /api/runs` will appear here once the workspace has review activity.</p>
        </div>
      ) : (
        <div className="history-list">
          {history.error && <div className="feedback error subdued">{history.error}</div>}

          {recentRuns.map((run) => {
            const summary = describeHistoryRun(run);
            const isActive = run.run_id === activeRunId;

            return (
              <article key={run.run_id} className={`history-card${isActive ? ' history-card-active' : ''}`}>
                <div className="card-head">
                  <div>
                    <span className="history-id">{run.run_id}</span>
                    <h4>{summary.actionLabel}</h4>
                  </div>
                  <span className={`status-pill status-${summary.status}`}>{summary.statusLabel}</span>
                </div>

                <p>{summary.detail}</p>

                <div className="detail-row">
                  <span>Created {summary.createdAt}</span>
                  {run.updated_at && <span>Updated {formatDateTime(run.updated_at)}</span>}
                </div>

                <div className="history-actions">
                  <button type="button" className="button secondary" onClick={() => onOpenRun(run)}>
                    {summary.actionLabel}
                  </button>
                  <span className="subtle-text">
                    {run.artifact_presence?.report_json ? 'Result artifact ready' : 'Waiting on result artifact'}
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

function ReviewSummaryPanel({
  runId,
  status,
  statusPayload,
  result,
  resultPayload,
  resultState,
  failureMessage,
  resultError,
}) {
  const summary = deriveResultOverview(result, resultPayload, runId, statusPayload);

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">ReviewSummaryPanel</p>
        {result ? <span className="panel-tag">{deriveReviewMode(result)}</span> : <span className="panel-tag">Result overview</span>}
      </div>

      <div className="panel-heading">
        <div>
          <h2>Review the outcome before planning starts</h2>
          <p>This area surfaces the run summary first: coverage, risk signal, findings volume, and the review narrative.</p>
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
        </div>
      ) : result ? (
        <div className="result-stack">
          <div className="result-lead">
            <h3>{summary.title}</h3>
            <p>{summary.narrative}</p>
          </div>

          <div className="metric-grid">
            {summary.metrics.map((metric) => (
              <article key={metric.label} className="metric-card">
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
              </article>
            ))}
          </div>

          <div className="chip-row">
            {summary.chips.map((chip) => (
              <span key={chip} className="chip">{chip}</span>
            ))}
          </div>
        </div>
      ) : (
        <div className="empty-state soft">
          <div className="empty-grid" />
          <h3>Result overview is waiting for a completed run</h3>
          <p>Once the run completes, the frontend will fetch `GET /api/review/{'{run_id}'}/result` and render the structured review output here.</p>
          {resultError && <div className="feedback error">{resultError}</div>}
        </div>
      )}
    </section>
  );
}

function FindingsPanel({ result, status, resultState }) {
  const findings = result ? deriveFindings(result) : [];

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">FindingsPanel</p>
        <span className="panel-tag">{findings.length} findings</span>
      </div>

      <div className="panel-heading panel-heading-tight">
        <div>
          <h2>Findings</h2>
          <p>The strongest review issues appear first so reviewers can act on the most important gaps quickly.</p>
        </div>
      </div>

      {status === 'completed' && resultState === 'loading' ? (
        <div className="loading-state compact">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </div>
      ) : findings.length === 0 ? (
        <div className="empty-inline">No findings are available for this run yet.</div>
      ) : (
        <div className="list-stack">
          {findings.map((finding) => (
            <article key={finding.id} className="finding-card">
              <div className="card-head">
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

function RisksPanel({ result, status, resultState }) {
  const risks = result ? deriveRisks(result) : [];

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">RisksPanel</p>
        <span className="panel-tag">{risks.length} risks</span>
      </div>

      <div className="panel-heading panel-heading-tight">
        <div>
          <h2>Risks</h2>
          <p>Structured delivery risks stay separate from findings so review quality and execution exposure are easy to parse.</p>
        </div>
      </div>

      {status === 'completed' && resultState === 'loading' ? (
        <div className="loading-state compact">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
          <div className="skeleton-line" />
        </div>
      ) : risks.length === 0 ? (
        <div className="empty-inline">No structured risks were returned for this run.</div>
      ) : (
        <div className="list-stack">
          {risks.map((risk) => (
            <article key={risk.id} className="finding-card">
              <div className="card-head">
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

function OpenQuestionsPanel({ result, status, resultState }) {
  const questions = result ? deriveOpenQuestions(result) : [];

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">OpenQuestionsPanel</p>
        <span className="panel-tag">{questions.length} open questions</span>
      </div>

      <div className="panel-heading panel-heading-tight">
        <div>
          <h2>Open questions</h2>
          <p>Questions that still need clarification stay visible so delivery planning does not advance on unresolved assumptions.</p>
        </div>
      </div>

      {status === 'completed' && resultState === 'loading' ? (
        <div className="loading-state compact">
          <div className="skeleton-line" />
          <div className="skeleton-line short" />
        </div>
      ) : questions.length === 0 ? (
        <div className="empty-inline">No open questions were generated for this run.</div>
      ) : (
        <div className="list-stack">
          {questions.map((question) => (
            <article key={question.id} className="question-card">
              <h4>{question.question}</h4>
              {question.detail && <p>{question.detail}</p>}
              {question.reviewers.length > 0 && <div className="detail-row"><span>{joinList(question.reviewers)}</span></div>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function ArtifactDownloadPanel({
  runId,
  status,
  resultPayload,
  statusPayload,
  downloadFormat,
  artifactError,
  onDownload,
}) {
  const artifactPaths = resultPayload?.artifact_paths ?? statusPayload?.report_paths ?? {};
  const artifactKeys = Object.keys(artifactPaths);
  const canDownload = Boolean(runId) && status === 'completed';

  return (
    <section className="panel">
      <div className="panel-topline">
        <p className="panel-kicker">ArtifactDownloadPanel</p>
        <span className="panel-tag">{artifactKeys.length} artifact paths</span>
      </div>

      <div className="panel-heading panel-heading-tight">
        <div>
          <h2>Download result artifacts</h2>
          <p>Export the review report as Markdown or JSON after the run completes, and keep the resolved artifact paths visible.</p>
        </div>
      </div>

      <p className="panel-copy">Downloads call `GET /api/report/{'{run_id}'}?format=md|json` and preserve the filename returned by the backend.</p>

      <div className="button-row">
        <button
          type="button"
          className="button primary"
          disabled={!canDownload || downloadFormat === 'md'}
          onClick={() => onDownload('md')}
        >
          {downloadFormat === 'md' ? 'Downloading Markdown...' : 'Download Markdown'}
        </button>
        <button
          type="button"
          className="button secondary"
          disabled={!canDownload || downloadFormat === 'json'}
          onClick={() => onDownload('json')}
        >
          {downloadFormat === 'json' ? 'Downloading JSON...' : 'Download JSON'}
        </button>
      </div>

      {!canDownload && <div className="empty-inline">Artifacts unlock after a run completes successfully.</div>}
      {artifactError && <div className="feedback error">{artifactError}</div>}

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
              : '',
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
          report_paths: {},
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
      artifactError: '',
    }));

    try {
      await downloadReportArtifact(workspace.runId, format);
    } catch (error) {
      setWorkspace((current) => ({
        ...current,
        artifactError: formatApiError(error, `Failed to download the ${format.toUpperCase()} report.`),
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
      <div className="background-glow glow-left" />
      <div className="background-glow glow-right" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Review Workspace</p>
          <h1>Submit a PRD, watch the run, inspect the result, and download the review artifacts.</h1>
          <p>
            This frontend stays review-first. It connects directly to review submit, status, result, and report endpoints
            without adding heavy state machinery or generic platform menus.
          </p>
        </div>

        <aside className="hero-aside">
          <span className="hero-tag">Connected endpoints</span>
          <ol>
            <li>`POST /api/review` starts a run and returns the `run_id`.</li>
            <li>`GET /api/review/{'{run_id}'}` powers live polling and failure messaging.</li>
            <li>`GET /api/review/{'{run_id}'}/result` hydrates the structured review output.</li>
            <li>`GET /api/report/{'{run_id}'}?format=md|json` downloads final report artifacts.</li>
          </ol>
        </aside>
      </header>

      <main className="workspace-layout">
        <section className="left-column">
          <ReviewSubmitPanel
            form={form}
            isSubmitting={workspace.submitState === 'submitting'}
            errorMessage={workspace.submitError}
            onFieldChange={updateField}
            onLoadSample={() => setForm(loadSampleForm())}
            onReset={resetWorkspace}
            onSubmit={handleSubmit}
          />

          <ReviewHistoryPanel
            history={history}
            activeRunId={workspace.runId}
            onRefreshHistory={() => loadRunHistory({ preserveRuns: true })}
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
            artifactError={workspace.artifactError}
            onDownload={handleDownload}
          />
        </section>

        <section className="right-column">
          <ReviewSummaryPanel
            runId={workspace.runId}
            status={status}
            statusPayload={workspace.statusPayload}
            result={result}
            resultPayload={workspace.resultPayload}
            resultState={workspace.resultState}
            failureMessage={workspace.failureMessage}
            resultError={workspace.resultError}
          />

          <div className="panel-grid">
            <FindingsPanel result={result} status={status} resultState={workspace.resultState} />
            <RisksPanel result={result} status={status} resultState={workspace.resultState} />
          </div>

          <OpenQuestionsPanel result={result} status={status} resultState={workspace.resultState} />
        </section>
      </main>
    </div>
  );
}

export default App;
