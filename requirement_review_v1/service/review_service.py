"""Reusable review service API for CLI/FastAPI/MCP entrypoints."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from requirement_review_v1.run_review import run_review


@dataclass(slots=True)
class ReviewResultSummary:
    run_id: str
    report_md_path: str
    report_json_path: str
    high_risk_ratio: float
    coverage_ratio: float
    revision_round: int
    status: str
    run_trace_path: str = ""

    def to_report_paths(self) -> dict[str, str]:
        return {
            "report_md": self.report_md_path,
            "report_json": self.report_json_path,
            "run_trace": self.run_trace_path,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _derive_status(result: dict[str, Any]) -> str:
    trace = result.get("trace", {})
    if not isinstance(trace, dict):
        return "completed"
    for span in trace.values():
        if not isinstance(span, dict):
            continue
        status = str(span.get("status", "") or "").lower()
        if status and status not in ("ok", "success", "completed"):
            return "failed"
    return "completed"


def _build_summary(run_output: dict[str, Any]) -> ReviewResultSummary:
    result = run_output.get("result", {})
    report_paths = run_output.get("report_paths", {})
    metrics = result.get("metrics", {}) if isinstance(result, dict) else {}
    return ReviewResultSummary(
        run_id=str(run_output.get("run_id", "")),
        report_md_path=str(report_paths.get("report_md", "")),
        report_json_path=str(report_paths.get("report_json", "")),
        run_trace_path=str(report_paths.get("run_trace", "")),
        high_risk_ratio=_to_float(result.get("high_risk_ratio") if isinstance(result, dict) else 0.0),
        coverage_ratio=_to_float(metrics.get("coverage_ratio") if isinstance(metrics, dict) else 0.0),
        revision_round=int((result.get("revision_round", 0) if isinstance(result, dict) else 0) or 0),
        status=_derive_status(result if isinstance(result, dict) else {}),
    )


async def review_prd_text_async(
    prd_text: str,
    *,
    run_id: str | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> ReviewResultSummary:
    overrides = config_overrides or {}
    outputs_root = Path(str(overrides.get("outputs_root", "outputs")))
    progress_hook = overrides.get("progress_hook")
    if progress_hook is not None and not callable(progress_hook):
        raise TypeError("config_overrides['progress_hook'] must be callable")

    run_output = await run_review(
        requirement_doc=prd_text,
        run_id=run_id,
        outputs_root=outputs_root,
        progress_hook=progress_hook,
    )
    return _build_summary(run_output)


def review_prd_text(
    prd_text: str,
    *,
    run_id: str | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> ReviewResultSummary:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            review_prd_text_async(
                prd_text=prd_text,
                run_id=run_id,
                config_overrides=config_overrides,
            )
        )
    raise RuntimeError("review_prd_text cannot run inside an active event loop; use review_prd_text_async")


def _read_prd_text(prd_text: str | None, prd_path: str | None) -> str:
    if isinstance(prd_text, str) and prd_text.strip():
        return prd_text
    if isinstance(prd_path, str) and prd_path.strip():
        path = Path(prd_path)
        if not path.exists():
            raise FileNotFoundError(f"PRD file not found: {prd_path}")
        return path.read_text(encoding="utf-8")
    raise ValueError("Either prd_text or prd_path must be provided")


def _attach_trace_invocation(summary: ReviewResultSummary, invocation_meta: dict[str, Any]) -> None:
    if not summary.run_trace_path:
        return
    trace_path = Path(summary.run_trace_path)
    if not trace_path.exists():
        return

    trace_data: dict[str, Any] = {}
    try:
        loaded = json.loads(trace_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            trace_data = loaded
    except Exception:
        trace_data = {}

    invocation_trace = trace_data.get("invocation")
    if not isinstance(invocation_trace, dict):
        invocation_trace = {}
    invocation_trace.update(invocation_meta)
    trace_data["invocation"] = invocation_trace
    trace_path.write_text(json.dumps(trace_data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Keep report.json trace aligned with run_trace.json when possible.
    if summary.report_json_path:
        report_path = Path(summary.report_json_path)
        if report_path.exists():
            try:
                report_data = json.loads(report_path.read_text(encoding="utf-8"))
                if isinstance(report_data, dict):
                    report_trace = report_data.get("trace")
                    if not isinstance(report_trace, dict):
                        report_trace = {}
                    report_trace["invocation"] = invocation_trace
                    report_data["trace"] = report_trace
                    report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception:
                # Do not fail review completion because of metadata write-back.
                pass


def review_prd_for_mcp(
    *,
    prd_text: str | None,
    prd_path: str | None,
    options: dict[str, Any] | None = None,
    invocation_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = options or {}
    if not isinstance(resolved_options, dict):
        raise TypeError("options must be an object")

    requirement_doc = _read_prd_text(prd_text=prd_text, prd_path=prd_path)
    run_id_raw = resolved_options.get("run_id")
    run_id = str(run_id_raw).strip() if run_id_raw is not None else ""
    outputs_root = str(resolved_options.get("outputs_root", "outputs"))

    summary = review_prd_text(
        prd_text=requirement_doc,
        run_id=run_id or None,
        config_overrides={"outputs_root": outputs_root},
    )

    trace_meta = {"invoked_via": "mcp"}
    if invocation_meta:
        trace_meta.update(invocation_meta)
    _attach_trace_invocation(summary, trace_meta)

    return {
        "run_id": summary.run_id,
        "status": summary.status,
        "metrics": {
            "coverage_ratio": summary.coverage_ratio,
            "high_risk_ratio": summary.high_risk_ratio,
            "revision_round": summary.revision_round,
        },
        "artifacts": {
            "report_md_path": summary.report_md_path,
            "report_json_path": summary.report_json_path,
            "trace_path": summary.run_trace_path,
        },
    }
