import { normalizeMultiline, normalizeText } from './formatters';

export function buildSubmissionPayload(form) {
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

export function validateSubmission(payload) {
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
