function RouteLoadingFallback() {
  return (
    <section className="panel panel-loading-state">
      <div className="loading-state loading-state-summary">
        <div className="shimmer-block shimmer-title" />
        <div className="metric-grid">
          <div className="metric-card loading-card" />
          <div className="metric-card loading-card" />
          <div className="metric-card loading-card" />
          <div className="metric-card loading-card" />
        </div>
      </div>
    </section>
  );
}

export default RouteLoadingFallback;
