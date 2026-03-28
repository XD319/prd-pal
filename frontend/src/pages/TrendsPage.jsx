import { useEffect, useMemo, useState } from 'react';
import { fetchStatsSummary, fetchTrendData } from '../api';
import PanelErrorBoundary from '../components/PanelErrorBoundary';
import { formatApiError } from '../utils/errors';
import '../styles/panels.css';
import '../styles/components.css';

function formatPointLabel(timestamp, runId) {
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) {
    return runId;
  }
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
  });
}

function buildPolyline(points, width, height, accessor, maxValue) {
  const safeMax = maxValue > 0 ? maxValue : 1;
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
      const y = height - (accessor(point) / safeMax) * height;
      return `${x},${y}`;
    })
    .join(' ');
}

function TrendsPage() {
  const [trendState, setTrendState] = useState({ status: 'loading', data: null, error: '' });
  const [statsState, setStatsState] = useState({ status: 'loading', data: null, error: '' });

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setTrendState({ status: 'loading', data: null, error: '' });
      setStatsState({ status: 'loading', data: null, error: '' });

      try {
        const [trendPayload, statsPayload] = await Promise.all([
          fetchTrendData(20),
          fetchStatsSummary(),
        ]);
        if (cancelled) {
          return;
        }
        setTrendState({ status: 'success', data: trendPayload, error: '' });
        setStatsState({ status: 'success', data: statsPayload, error: '' });
      } catch (error) {
        if (cancelled) {
          return;
        }
        const message = formatApiError(error, 'Trend data is unavailable.');
        setTrendState({ status: 'error', data: null, error: message });
        setStatsState({ status: 'error', data: null, error: message });
      }
    }

    loadData();
    return () => {
      cancelled = true;
    };
  }, []);

  const points = Array.isArray(trendState.data?.points) ? trendState.data.points.slice().reverse() : [];
  const svgModel = useMemo(() => {
    const width = 640;
    const height = 220;
    const maxFindings = Math.max(1, ...points.map((point) => Number(point.total_findings ?? 0)));
    const maxCoverage = Math.max(1, ...points.map((point) => Number(point.coverage_pct ?? 0)));
    return {
      width,
      height,
      findingsLine: buildPolyline(points, width, height, (point) => Number(point.total_findings ?? 0), maxFindings),
      coverageLine: buildPolyline(points, width, height, (point) => Number(point.coverage_pct ?? 0), maxCoverage),
      maxFindings,
      maxCoverage,
    };
  }, [points]);

  return (
    <>
      <header className="page-header">
        <div>
          <p className="eyebrow">Review trend workspace</p>
          <h1>趋势分析</h1>
          <p className="hero-copy">
            从最近的 review 运行中观察问题总量和覆盖率的变化曲线，快速判断评审质量是在收敛还是波动。
          </p>
        </div>
      </header>

      <main className="workspace-grid trend-layout">
        <section className="stack stack-wide">
          <PanelErrorBoundary panelTitle="Trend chart" resetKey={trendState.status}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Timeline</p>
                  <h2>Review 折线图</h2>
                </div>
              </div>

              {trendState.error ? <div className="feedback-banner feedback-error">{trendState.error}</div> : null}

              {points.length < 2 ? (
                <div className="empty-state empty-state-compact">
                  <div className="empty-grid" aria-hidden="true" />
                  <div>
                    <h3>数据不足</h3>
                    <p>至少需要 2 个 run 才能形成趋势线。当前先完成更多 review，再回来查看波动。</p>
                  </div>
                </div>
              ) : (
                <div className="trend-chart-shell">
                  <div className="trend-axis-note">
                    <span>左轴: Findings 总数</span>
                    <span>右轴: Coverage 百分比</span>
                  </div>
                  <div className="trend-chart-card">
                    <svg
                      className="trend-chart"
                      viewBox={`0 0 ${svgModel.width} ${svgModel.height + 28}`}
                      role="img"
                      aria-label="Findings and coverage trend chart"
                    >
                      {[0.25, 0.5, 0.75, 1].map((ratio) => (
                        <line
                          key={`grid-${ratio}`}
                          x1="0"
                          y1={svgModel.height - svgModel.height * ratio}
                          x2={svgModel.width}
                          y2={svgModel.height - svgModel.height * ratio}
                          className="trend-grid-line"
                        />
                      ))}
                      <polyline points={svgModel.findingsLine} className="trend-line trend-line-findings" />
                      <polyline points={svgModel.coverageLine} className="trend-line trend-line-coverage" />
                      {points.map((point, index) => {
                        const x = (index / (points.length - 1)) * svgModel.width;
                        const findingsY = svgModel.height - (Number(point.total_findings ?? 0) / svgModel.maxFindings) * svgModel.height;
                        const coverageY = svgModel.height - (Number(point.coverage_pct ?? 0) / svgModel.maxCoverage) * svgModel.height;
                        return (
                          <g key={point.run_id}>
                            <circle cx={x} cy={findingsY} r="4.5" className="trend-dot trend-dot-findings" />
                            <circle cx={x} cy={coverageY} r="4.5" className="trend-dot trend-dot-coverage" />
                            <text x={x} y={svgModel.height + 18} textAnchor="middle" className="trend-label">
                              {formatPointLabel(point.timestamp, point.run_id)}
                            </text>
                          </g>
                        );
                      })}
                    </svg>
                  </div>
                  <div className="trend-legend">
                    <span className="trend-legend-item"><i className="trend-swatch trend-swatch-findings" />Findings</span>
                    <span className="trend-legend-item"><i className="trend-swatch trend-swatch-coverage" />Coverage</span>
                  </div>
                </div>
              )}
            </div>
          </PanelErrorBoundary>
        </section>

        <section className="stack">
          <PanelErrorBoundary panelTitle="Stats summary" resetKey={statsState.status}>
            <div className="panel">
              <div className="panel-header">
                <div>
                  <p className="section-kicker">Stats</p>
                  <h2>统计摘要</h2>
                </div>
              </div>

              <div className="comparison-summary-grid">
                <article className="metric-delta-card metric-delta-neutral">
                  <div className="metric-delta-header">
                    <span>总 run 数</span>
                    <strong>{statsState.data?.total_runs ?? 0}</strong>
                  </div>
                  <p className="subtle-note">当前可用于趋势分析的历史 review 数量。</p>
                </article>
                <article className="metric-delta-card metric-delta-neutral">
                  <div className="metric-delta-header">
                    <span>平均 findings</span>
                    <strong>{Number(statsState.data?.average_findings ?? 0).toFixed(1)}</strong>
                  </div>
                  <p className="subtle-note">帮助判断总体问题密度是否正在下降。</p>
                </article>
              </div>

              <div className="trend-top-issues">
                <span>最常见问题类型</span>
                {Array.isArray(statsState.data?.top_issue_types) && statsState.data.top_issue_types.length > 0 ? (
                  <div className="chip-row">
                    {statsState.data.top_issue_types.map((item) => (
                      <span key={item.issue_type} className="inline-meta inline-meta-soft">
                        {item.issue_type} · {item.count}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="subtle-note">还没有足够的 findings 类型数据。</p>
                )}
              </div>
            </div>
          </PanelErrorBoundary>
        </section>
      </main>
    </>
  );
}

export default TrendsPage;
