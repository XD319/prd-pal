"""Reusable review service API for CLI/FastAPI/MCP entrypoints."""

from __future__ import annotations

import asyncio
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
