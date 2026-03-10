import { excerpt, formatPercent, formatStatusLabel, normalizeText, pluralize } from './formatters';

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

export function severityRank(value) {
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

export function deriveModeLabel(result) {
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

export function deriveFindings(result) {
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

export function deriveRisks(result) {
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

export function deriveOpenQuestions(result) {
  return asArray(result?.review_open_questions).map((item, index) => ({
    id: item.id ?? item.question ?? `question-${index}`,
    question: item.question ?? `Open question ${index + 1}`,
    detail: asArray(item.issues).join(' '),
    reviewers: asArray(item.reviewers),
  }));
}

export function deriveSummary(result, runId, statusPayload, resultPayload) {
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

export function deriveFailureMessage(statusPayload, fallbackMessage = '') {
  return (
    normalizeText(statusPayload?.progress?.error) ||
    normalizeText(statusPayload?.error) ||
    fallbackMessage ||
    'The review run failed before the structured result became available.'
  );
}

export function deriveNodes(progress) {
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

export function describeHistoryRun(run) {
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
    actionLabel: 'Open',
    hasResult,
  };
}

