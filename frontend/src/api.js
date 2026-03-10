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

async function requestJson(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });

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

export function fetchReviewStatus(runId) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}`);
}

export function fetchReviewResult(runId) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}/result`);
}

export function fetchArtifactPreview(runId, artifactKey) {
  return requestJson(`/api/review/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactKey)}`);
}

export function fetchRuns() {
  return requestJson('/api/runs');
}

export async function downloadReportArtifact(runId, format) {
  const response = await fetch(`/api/report/${encodeURIComponent(runId)}?format=${encodeURIComponent(format)}`);
  const fallbackName = format === 'json' ? 'report.json' : 'report.md';

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
