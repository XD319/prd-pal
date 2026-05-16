export const primaryNodes = [
  'parser',
  'parallel_start',
  'planner',
  'risk',
  'review_join',
  'delivery_planning',
  'reviewer',
  'route_decider',
  'reporter',
  'finalize_artifacts',
];

export function cloneProgressPayload(payload) {
  if (!payload || typeof payload !== 'object') {
    return null;
  }
  return {
    ...payload,
    progress: payload.progress && typeof payload.progress === 'object'
      ? {
        ...payload.progress,
        nodes: payload.progress.nodes && typeof payload.progress.nodes === 'object'
          ? Object.fromEntries(
            Object.entries(payload.progress.nodes).map(([key, value]) => [key, { ...value }]),
          )
          : {},
      }
      : { nodes: {} },
  };
}

export function nodeWeight(status) {
  const normalized = String(status ?? '').toLowerCase();
  if (normalized === 'running') {
    return 0.5;
  }
  if (normalized === 'completed' || normalized === 'failed') {
    return 1;
  }
  return 0;
}

export function computeProgressPercent(nodes, runStatus) {
  if (runStatus === 'completed') {
    return 100;
  }

  const completedWeight = primaryNodes.reduce((total, nodeId) => {
    const node = nodes?.[nodeId];
    return total + nodeWeight(node?.status);
  }, 0);

  const percent = primaryNodes.length
    ? Math.round((completedWeight / primaryNodes.length) * 100)
    : 0;

  return runStatus === 'failed' ? percent : Math.min(percent, 99);
}

export function normalizeNodeStatus(eventStatus, payload) {
  const normalized = String(eventStatus ?? '').toLowerCase();
  if (normalized === 'start') {
    return 'running';
  }
  if (normalized === 'end') {
    return payload?.error ? 'failed' : 'completed';
  }
  if (normalized === 'running' || normalized === 'completed' || normalized === 'failed') {
    return normalized;
  }
  return 'pending';
}

export function mergeSseProgressPayload(currentPayload, payload) {
  if (!payload || typeof payload !== 'object') {
    return currentPayload;
  }

  const nextPayload = cloneProgressPayload(currentPayload) ?? {
    run_id: String(payload.run_id ?? ''),
    status: 'running',
    progress: {
      percent: 0,
      current_node: '',
      nodes: {},
      updated_at: String(payload.timestamp ?? ''),
      error: '',
    },
    report_paths: {},
  };

  const nextProgress = nextPayload.progress ?? { nodes: {} };
  nextProgress.nodes = nextProgress.nodes ?? {};

  if (payload.node === 'run' || payload.terminal) {
    nextPayload.status = String(payload.status ?? nextPayload.status ?? 'running');
    nextProgress.current_node = '';
    nextProgress.updated_at = String(payload.timestamp ?? nextProgress.updated_at ?? '');
    nextProgress.error = String(payload.error ?? nextProgress.error ?? '');
    nextProgress.percent = computeProgressPercent(nextProgress.nodes, nextPayload.status);
    if (nextPayload.status === 'completed') {
      nextProgress.percent = 100;
    }
    nextPayload.progress = nextProgress;
    return nextPayload;
  }

  const nodeId = String(payload.node ?? '').trim();
  if (!nodeId) {
    return nextPayload;
  }

  const node = { ...(nextProgress.nodes[nodeId] ?? { status: 'pending', runs: 0 }) };
  const nodeStatus = normalizeNodeStatus(payload.status, payload);
  if (String(payload.status ?? '').toLowerCase() === 'start') {
    node.runs = Number(node.runs ?? 0) + 1;
    node.last_start = String(payload.timestamp ?? node.last_start ?? '');
    nextProgress.current_node = nodeId;
  } else if (String(payload.status ?? '').toLowerCase() === 'end') {
    node.last_end = String(payload.timestamp ?? node.last_end ?? '');
    if (nextProgress.current_node === nodeId) {
      nextProgress.current_node = '';
    }
  }

  node.status = nodeStatus;
  nextProgress.nodes[nodeId] = node;
  nextProgress.updated_at = String(payload.timestamp ?? nextProgress.updated_at ?? '');
  if (payload.error) {
    nextProgress.error = String(payload.error);
  }
  nextPayload.status = nextPayload.status === 'queued' ? 'running' : (nextPayload.status ?? 'running');
  nextProgress.percent = computeProgressPercent(nextProgress.nodes, nextPayload.status);
  nextPayload.progress = nextProgress;
  return nextPayload;
}
