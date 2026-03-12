import { excerpt, formatPercent, formatStatusLabel, normalizeText, pluralize } from './formatters';

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

const RUN_NODE_ORDER = [
  'parser',
  'parallel_start',
  'planner',
  'risk',
  'review_join',
  'delivery_planning',
  'reviewer',
  'route_decider',
  'clarify',
  'reporter',
  'finalize_artifacts',
];

export function formatNodeLabel(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return '';
  }
  return normalized.replace(/_/g, ' ');
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

function deriveParallelMeta(result) {
  return result?.['parallel-review_meta'] ?? result?.parallel_review_meta ?? {};
}

export function deriveModeLabel(result) {
  const meta = deriveParallelMeta(result);
  const mode = String(result?.mode ?? result?.review_mode ?? meta.selected_mode ?? meta.review_mode ?? 'quick');
  if (mode === 'full' || mode === 'parallel_review') {
    return 'Full review';
  }
  if (mode === 'quick' || mode === 'single_review') {
    return 'Quick triage';
  }
  if (mode === 'skip') {
    return 'Manual review';
  }
  return mode.replace(/_/g, ' ');
}

export function deriveReviewers(result, resultPayload) {
  const directUsed = asArray(resultPayload?.reviewers_used);
  const directSkipped = asArray(resultPayload?.reviewers_skipped);
  const meta = deriveParallelMeta(result);
  const nested = result?.parallel_review ?? {};

  return {
    used: directUsed.length > 0 ? directUsed : asArray(result?.reviewers_used ?? nested.reviewers_used ?? meta.reviewers_used),
    skipped: directSkipped.length > 0 ? directSkipped : asArray(result?.reviewers_skipped ?? nested.reviewers_skipped ?? meta.reviewers_skipped),
  };
}

export function deriveGatingInfo(result, resultPayload) {
  const meta = deriveParallelMeta(result);
  const nested = result?.parallel_review ?? {};
  const gating = resultPayload?.gating ?? result?.gating ?? nested.gating ?? meta.gating ?? {};
  const reasons = asArray(gating.reasons).filter(Boolean);
  return {
    selectedMode: String(gating.selected_mode ?? resultPayload?.mode ?? result?.mode ?? result?.review_mode ?? meta.selected_mode ?? 'quick'),
    skipped: Boolean(gating.skipped),
    reasons,
  };
}


export function deriveClarification(result) {
  const nested = result?.parallel_review ?? {};
  const clarification = result?.review_clarification ?? result?.clarification ?? nested.clarification ?? {};
  const questions = asArray(clarification.questions).map((item, index) => ({
    id: item.id ?? `clarify-${index}`,
    question: item.question ?? `Clarification ${index + 1}`,
    reviewer: item.reviewer ?? '',
    ambiguityType: item.ambiguity_type ?? '',
    findingIds: asArray(item.finding_ids),
  }));
  const answersApplied = asArray(clarification.answers_applied);
  const findingsUpdated = asArray(clarification.findings_updated);

  return {
    triggered: Boolean(clarification.triggered),
    status: String(clarification.status ?? (questions.length > 0 ? 'pending' : 'not_needed')),
    questions,
    answersApplied,
    findingsUpdated,
  };
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
        originalSeverity: String(item.original_severity ?? item.severity ?? 'medium').toLowerCase(),
        clarificationApplied: Boolean(item.clarification_applied),
        userClarification: item.user_clarification ?? '',
        ambiguityType: item.ambiguity_type ?? '',
        category: item.category ?? 'review',
        reviewers: asArray(item.reviewers),
        assignee: item.assignee ?? '',
        action: item.suggested_action ?? '',
        evidence: asArray(item.evidence),
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
        originalSeverity: severity,
        clarificationApplied: false,
        userClarification: '',
        ambiguityType: '',
        category: 'review_quality',
        reviewers: ['single_reviewer'],
        assignee: '',
        action: item.suggestions ?? '',
        evidence: [],
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


export function deriveMemoryHits(result, resultPayload) {
  const meta = deriveParallelMeta(result);
  const nested = result?.parallel_review ?? {};
  const source = asArray(resultPayload?.memory_hits ?? result?.memory_hits ?? nested.memory_hits ?? meta.memory_hits);
  return source.map((item, index) => ({
    id: item.reference_id ?? `memory-${index}`,
    sourceKind: item.source_kind ?? 'history',
    title: item.title ?? `Reference ${index + 1}`,
    summary: item.summary ?? '',
    findingExcerpt: item.finding_excerpt ?? '',
    score: Number(item.score ?? 0),
    reviewMode: item.review_mode ?? 'quick',
    tags: asArray(item.tags),
  }));
}
export function deriveReviewerInsights(result, resultPayload) {
  const meta = deriveParallelMeta(result);
  const nested = result?.parallel_review ?? {};
  const source = asArray(result?.reviewer_insights ?? nested.reviewer_summaries ?? meta.reviewer_insights ?? meta.reviewer_notes);
  const memoryHits = deriveMemoryHits(result, resultPayload);

  return source.map((item, index) => ({
    id: `${item.reviewer ?? 'reviewer'}-${index}`,
    reviewer: item.reviewer ?? `Reviewer ${index + 1}`,
    status: String(item.status ?? 'completed').toLowerCase(),
    summary: item.summary ?? '',
    statusDetail: item.status_detail ?? '',
    ambiguityType: item.ambiguity_type ?? '',
    clarificationQuestion: item.clarification_question ?? '',
    notes: asArray(item.notes),
    memoryHitCount: memoryHits.length,
    memoryHits,
  }));
}

export function deriveToolCalls(result) {
  const meta = deriveParallelMeta(result);
  const nested = result?.parallel_review ?? {};
  const source = asArray(result?.review_tool_calls ?? nested.tool_calls ?? meta.tool_calls);

  return source.map((item, index) => ({
    id: `${item.reviewer ?? 'tool'}-${item.tool_name ?? 'call'}-${index}`,
    reviewer: item.reviewer ?? 'unknown',
    toolName: item.tool_name ?? 'tool',
    status: String(item.status ?? 'unknown').toLowerCase(),
    query: item.query ?? '',
    inputSummary: item.input_summary ?? '',
    outputSummary: item.output_summary ?? '',
    evidenceCount: Number(item.evidence_count ?? 0),
    degradedReason: item.degraded_reason ?? '',
    errorMessage: item.error_message ?? '',
  }));
}

export function deriveConflicts(result) {
  const nested = result?.parallel_review ?? {};
  const source = asArray(result?.conflicts ?? nested.conflicts);

  return source
    .map((item, index) => ({
      id: item.conflict_id ?? `conflict-${index}`,
      title: item.topic ?? item.type ?? `Conflict ${index + 1}`,
      type: item.type ?? 'conflict',
      description: item.description ?? 'Conflict requires manual review.',
      reviewers: asArray(item.reviewers),
      severity: String(item.conflict_severity ?? 'medium').toLowerCase(),
      requiresManualResolution: Boolean(item.requires_manual_resolution ?? true),
      recommendation: item.resolution?.recommendation ?? '',
      reasoning: item.resolution?.reasoning ?? '',
      decidedBy: item.resolution?.decided_by ?? '',
    }))
    .sort((left, right) => {
      if (left.requiresManualResolution !== right.requiresManualResolution) {
        return left.requiresManualResolution ? 1 : -1;
      }
      return severityRank(right.severity) - severityRank(left.severity);
    });
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
  const reviewers = deriveReviewers(result, resultPayload);
  const gating = deriveGatingInfo(result, resultPayload);
  const toolCalls = deriveToolCalls(result);
  const memoryHits = deriveMemoryHits(result, resultPayload);
  const metrics = result.metrics ?? {};
  const meta = deriveParallelMeta(result);
  const summaryMeta = result.summary ?? result.parallel_review?.summary ?? resultPayload?.result?.summary ?? {};
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
      { label: 'Overall risk', value: String(summaryMeta.overall_risk ?? 'unknown') },
      { label: 'Tool calls', value: `${toolCalls.length}` },
      { label: 'Memory hits', value: `${memoryHits.length}` },
    ],
    chips: [
      deriveModeLabel(result),
      pluralize(asArray(result.parsed_items).length, 'requirement'),
      pluralize(findings.length, 'finding'),
      pluralize(risks.length, 'risk'),
      pluralize(questions.length, 'open question'),
      reviewers.used.length > 0 ? pluralize(reviewers.used.length, 'reviewer') : '',
      memoryHits.length > 0 ? pluralize(memoryHits.length, 'memory hit') : '',
      resultPayload?.normalizer_cache_hit || meta.normalizer_cache_hit ? 'Normalizer cache hit' : '',
      gating.skipped ? 'Manual follow-up needed' : '',
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
      id: name,
      name: formatNodeLabel(name),
      status: node?.status ?? 'pending',
      runs: node?.runs ?? 0,
      lastStart: node?.last_start ?? '',
      lastEnd: node?.last_end ?? '',
    }))
    .sort((left, right) => {
      const leftIndex = RUN_NODE_ORDER.indexOf(left.id);
      const rightIndex = RUN_NODE_ORDER.indexOf(right.id);
      const resolvedLeft = leftIndex === -1 ? RUN_NODE_ORDER.length : leftIndex;
      const resolvedRight = rightIndex === -1 ? RUN_NODE_ORDER.length : rightIndex;
      if (resolvedLeft !== resolvedRight) {
        return resolvedLeft - resolvedRight;
      }
      return left.name.localeCompare(right.name);
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





