import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export function ReportPanel({ reportMarkdown, reportMessage, runId }) {
  const downloadBase = runId ? `/api/report/${encodeURIComponent(runId)}` : "#";

  return (
    <section className="panel report-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Review Report</p>
          <h2>报告输出</h2>
        </div>
        <div className="report-actions">
          <a className={`btn btn-ghost ${runId ? "" : "disabled"}`} href={`${downloadBase}?format=md`} target="_blank" rel="noreferrer">Markdown</a>
          <a className={`btn btn-ghost ${runId ? "" : "disabled"}`} href={`${downloadBase}?format=json`} target="_blank" rel="noreferrer">JSON</a>
        </div>
      </div>

      <div className="report-summary">
        <p>{reportMessage}</p>
      </div>
      <article className={`report-preview markdown-body ${reportMarkdown ? "" : "empty"}`}>
        {reportMarkdown ? (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
            }}
          >
            {reportMarkdown}
          </ReactMarkdown>
        ) : (
          <p>暂无预览。</p>
        )}
      </article>
    </section>
  );
}
