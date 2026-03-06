async function readError(response) {
  try {
    const data = await response.json();
    return data.detail || response.statusText;
  } catch {
    return response.statusText;
  }
}

async function unwrapJson(response) {
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.json();
}

export async function createReview(payload) {
  const response = await fetch("/api/review", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return unwrapJson(response);
}

export async function getReviewStatus(runId) {
  const response = await fetch(`/api/review/${encodeURIComponent(runId)}`);
  return unwrapJson(response);
}

export async function getReportMarkdown(runId) {
  const response = await fetch(`/api/report/${encodeURIComponent(runId)}?format=md`);
  if (!response.ok) {
    throw new Error(await readError(response));
  }
  return response.text();
}

export function buildWebSocketUrl(runId) {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/review/${encodeURIComponent(runId)}`;
}
