import { normalizeMultiline, normalizeText } from './formatters';

export function buildSubmissionPayload(form, options = {}) {
  const { includeMode = false, allowPrdPath = true } = options;
  const payload = {};
  const source = normalizeText(form.source);
  const prdText = normalizeMultiline(form.prd_text);
  const prdPath = normalizeText(form.prd_path);
  const mode = normalizeText(form.mode);

  if (source) {
    payload.source = source;
  }
  if (prdText) {
    payload.prd_text = prdText;
  }
  if (allowPrdPath && prdPath) {
    payload.prd_path = prdPath;
  }
  if (includeMode && mode) {
    payload.mode = mode;
  }

  return payload;
}

export function validateSubmission(payload, options = {}) {
  const { allowPrdPath = true, requireSourceOrText = false } = options;
  const hasSource = Boolean(payload.source);
  const hasText = Boolean(payload.prd_text);
  const hasPath = allowPrdPath && Boolean(payload.prd_path);

  if (hasSource) {
    return '';
  }

  if (requireSourceOrText) {
    return hasText ? '' : 'Provide source or prd_text.';
  }

  if (hasText === hasPath) {
    return 'Provide source, or exactly one of prd_text or prd_path.';
  }

  return '';
}
