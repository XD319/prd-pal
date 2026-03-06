export function InputPanel({
  errorMessage,
  formError,
  isSubmitting,
  mode,
  onModeChange,
  onPrdPathChange,
  onPrdTextChange,
  onStopListening,
  onSubmit,
  prdPath,
  prdText,
  statusClass,
  statusLabel,
}) {
  return (
    <section className="panel input-panel">
      <div className="panel-header">
        <div>
          <p className="panel-kicker">Submit Review</p>
          <h2>发起需求评审</h2>
        </div>
        <div className={statusClass}>{statusLabel}</div>
      </div>

      <div className="input-mode-switch" role="tablist" aria-label="PRD 输入模式">
        <button className={`mode-btn ${mode === "text" ? "active" : ""}`} id="input-tab-text" role="tab" aria-selected={mode === "text"} aria-controls="input-panel-text" tabIndex={mode === "text" ? 0 : -1} type="button" onClick={() => onModeChange("text")}>PRD 文本</button>
        <button className={`mode-btn ${mode === "path" ? "active" : ""}`} id="input-tab-path" role="tab" aria-selected={mode === "path"} aria-controls="input-panel-path" tabIndex={mode === "path" ? 0 : -1} type="button" onClick={() => onModeChange("path")}>文件路径</button>
      </div>

      <form className="review-form" onSubmit={onSubmit}>
        {mode === "text" ? (
          <div id="input-panel-text" role="tabpanel" aria-labelledby="input-tab-text">
            <label className="field-label" htmlFor="prdText">PRD 内容</label>
            <textarea id="prdText" className={`field-input field-textarea ${formError && mode === "text" ? "field-input-error" : ""}`} value={prdText} onChange={(event) => onPrdTextChange(event.target.value)} placeholder="# PRD\n\n背景：...\n目标：...\n验收标准：..." aria-invalid={Boolean(formError && mode === "text")} aria-describedby={formError && mode === "text" ? "prd-input-error" : undefined} />
          </div>
        ) : (
          <div id="input-panel-path" role="tabpanel" aria-labelledby="input-tab-path">
            <label className="field-label" htmlFor="prdPath">PRD 文件路径</label>
            <input id="prdPath" className={`field-input ${formError && mode === "path" ? "field-input-error" : ""}`} type="text" value={prdPath} onChange={(event) => onPrdPathChange(event.target.value)} placeholder="例如：docs/sample_prd.md" aria-invalid={Boolean(formError && mode === "path")} aria-describedby={formError && mode === "path" ? "prd-input-error" : undefined} />
          </div>
        )}

        {formError ? <p id="prd-input-error" className="field-error">{formError}</p> : null}
        {errorMessage ? <div className="inline-alert" role="alert">{errorMessage}</div> : null}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={isSubmitting}>{isSubmitting ? "评审进行中" : "开始评审"}</button>
          {isSubmitting ? (
            <button className="btn btn-secondary" type="button" onClick={onStopListening}>
              停止监听
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
