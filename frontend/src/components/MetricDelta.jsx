import '../styles/panels.css';
import '../styles/components.css';

function formatValue(value, formatter) {
  if (typeof formatter === 'function') {
    return formatter(value);
  }
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0';
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function formatDeltaPercent(previousValue, nextValue) {
  if (!Number.isFinite(previousValue) || !Number.isFinite(nextValue)) {
    return '0.0%';
  }
  if (previousValue === 0) {
    if (nextValue === 0) {
      return '0.0%';
    }
    return '100.0%';
  }
  return `${(((nextValue - previousValue) / Math.abs(previousValue)) * 100).toFixed(1)}%`;
}

function MetricDelta({
  label,
  previousValue = 0,
  nextValue = 0,
  betterWhen = 'down',
  formatter,
  hint = '',
}) {
  const delta = nextValue - previousValue;
  const direction = delta === 0 ? 'neutral' : delta > 0 ? 'up' : 'down';
  const positiveDirection = betterWhen === 'up' ? 'up' : 'down';
  const tone = delta === 0 ? 'neutral' : direction === positiveDirection ? 'positive' : 'negative';
  const arrow = delta === 0 ? '→' : direction === 'up' ? '↑' : '↓';

  return (
    <article className={`metric-delta-card metric-delta-${tone}`}>
      <div className="metric-delta-header">
        <span>{label}</span>
        <strong>{formatValue(nextValue, formatter)}</strong>
      </div>
      <p className="metric-delta-range">
        {formatValue(previousValue, formatter)}
        <span aria-hidden="true"> → </span>
        {formatValue(nextValue, formatter)}
      </p>
      <div className={`metric-delta-badge metric-delta-badge-${tone}`} aria-live="polite">
        <span aria-hidden="true">{arrow}</span>
        <span>{formatDeltaPercent(previousValue, nextValue)}</span>
      </div>
      {hint ? <p className="subtle-note">{hint}</p> : null}
    </article>
  );
}

export default MetricDelta;
