import ErrorBoundary from './ErrorBoundary';

function PanelErrorBoundary({ children, panelTitle, resetKey = '' }) {
  return (
    <ErrorBoundary
      resetKey={resetKey}
      fallback={({ retry }) => (
        <section className="panel panel-error-state" role="alert">
          <div className="empty-state empty-state-compact">
            <div className="empty-grid" />
            <h3>该模块加载失败</h3>
            <p>{panelTitle} 暂时无法显示。你可以重试，或稍后刷新页面再试。</p>
            <button type="button" className="secondary-button" onClick={retry}>
              重试
            </button>
          </div>
        </section>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

export default PanelErrorBoundary;
