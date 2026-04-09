function getErrorMessage(payload, fallbackMessage) {
  if (payload?.detail?.message) {
    return payload.detail.message;
  }
  if (typeof payload?.detail === 'string') {
    return payload.detail;
  }
  if (typeof payload?.message === 'string') {
    return payload.message;
  }
  return fallbackMessage;
}

const defaultRequestTimeoutMs = 15000;

async function fetchWithTimeout(path, options = {}) {
  const { timeoutMs = defaultRequestTimeoutMs, headers, ...restOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    return await fetch(path, {
      headers: {
        'Content-Type': 'application/json',
        ...(headers ?? {}),
      },
      ...restOptions,
      signal: controller.signal,
    });
  } catch (error) {
    if (error?.name === 'AbortError') {
      const timeoutError = new Error(`Request timed out after ${timeoutMs}ms.`);
      timeoutError.name = 'TimeoutError';
      throw timeoutError;
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

async function requestJson(path, options = {}) {
  const response = await fetchWithTimeout(path, options);

  const contentType = response.headers.get('content-type') ?? '';
  const payload = contentType.includes('application/json')
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const error = new Error(getErrorMessage(payload, `Request failed with status ${response.status}.`));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return payload;
}

function parseFilename(response, fallback) {
  const disposition = response.headers.get('content-disposition') ?? '';
  const match = disposition.match(/filename="?([^";]+)"?/i);
  return match?.[1] ?? fallback;
}

export function submitReview(payload) {
  return requestJson('/api/review', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function submitFeishuReview(payload) {
  return requestJson('/api/feishu/submit', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchReviewStatus(runId) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}`);
}

export function fetchReviewResult(runId) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}/result`);
}

export function answerReviewClarification(runId, payload) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}/clarification`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function fetchArtifactPreview(runId, artifactKey) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactKey)}`);
}

export function fetchRuns() {
  return requestJson('/api/runs');
}

export function fetchComparison(runA, runB) {
  const params = new URLSearchParams({
    run_a: runA,
    run_b: runB,
  });
  return requestJson(`/api/compare?${params.toString()}`);
}

export function fetchTrendData(limit = 20) {
  return requestJson(`/api/trends?limit=${encodeURIComponent(limit)}`);
}

export function fetchStatsSummary() {
  return requestJson('/api/stats');
}

export async function downloadReportArtifact(runId, format) {
  const response = await fetchWithTimeout(`/api/report/${encodeURIComponent(runId)}?format=${encodeURIComponent(format)}`, {
    timeoutMs: 20000,
    headers: {},
  });
  const fallbackNameByFormat = {
    md: 'report.md',
    json: 'report.json',
    html: 'report.html',
    csv: 'report.csv',
  };
  const fallbackName = fallbackNameByFormat[format] ?? 'report.md';

  if (!response.ok) {
    let payload = null;
    try {
      payload = await response.json();
    } catch {
      payload = null;
    }
    const error = new Error(getErrorMessage(payload, `Download failed with status ${response.status}.`));
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = parseFilename(response, fallbackName);
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}
