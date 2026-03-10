export function normalizeText(value) {
  return String(value ?? '').trim();
}

export function normalizeMultiline(value) {
  return String(value ?? '').trimEnd();
}

export function pluralize(count, singular, plural = `${singular}s`) {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function formatDateTime(value) {
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

export function formatPercent(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric * 100)}%`;
}

export function formatPercentFromWhole(value) {
  const numeric = Number(value ?? 0);
  if (Number.isNaN(numeric)) {
    return '0%';
  }
  return `${Math.round(numeric)}%`;
}

export function formatStatusLabel(status) {
  const normalized = String(status ?? 'idle');
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

export function excerpt(value, maxLength = 200) {
  const normalized = String(value ?? '').replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 1).trim()}...`;
}

export function joinList(values) {
  return values.filter(Boolean).join(', ');
}
