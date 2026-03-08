"""Shared runner for requirement_review_v1 CLI and API."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workflow import build_review_graph

ProgressHook = Callable[[str, str, dict[str, Any]], None]


def make_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_model_provider(result: dict[str, Any]) -> tuple[str, str]:
    model, provider = "unknown", "unknown"
    try:
        from review_runtime.config.config import Config as _Cfg

        cfg = _Cfg()
        model = cfg.smart_llm_model or "unknown"
        provider = cfg.smart_llm_provider or "unknown"
    except Exception:
        trace = result.get("trace", {})
        if isinstance(trace, dict):
            for agent_name in ("parser", "reviewer"):
                maybe_model = trace.get(agent_name, {}).get("model", "")
                if isinstance(maybe_model, str) and maybe_model and maybe_model not in ("unknown", "none"):
                    model = maybe_model
                    break
    return model, provider


def build_report_data(result: dict[str, Any], run_id: str) -> dict[str, Any]:
    model, provider = resolve_model_provider(result)
    report_data: dict[str, Any] = {
        "schema_version": "v1.1",
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "provider": provider,
        "project": "requirement_review_v1",
    }
    report_data.update(result)
    parallel_review_meta = result.get("parallel_review_meta") if isinstance(result.get("parallel_review_meta"), dict) else {}
    if parallel_review_meta:
        report_data["parallel-review_meta"] = parallel_review_meta
    return report_data


def write_outputs(run_dir: str | Path, run_id: str, result: dict[str, Any]) -> dict[str, str]:
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)

    report_path = run_path / "report.md"
    state_path = run_path / "report.json"
    trace_path = run_path / "run_trace.json"

    report_path.write_text(str(result.get("final_report", "")), encoding="utf-8")
    state_path.write_text(
        json.dumps(build_report_data(result, run_id), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    trace_path.write_text(
        json.dumps(result.get("trace", {}), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "report_md": str(report_path),
        "report_json": str(state_path),
        "run_trace": str(trace_path),
    }


async def run_review(
    requirement_doc: str,
    *,
    run_id: str | None = None,
    outputs_root: str | Path = "outputs",
    progress_hook: ProgressHook | None = None,
    review_mode_override: str | None = None,
) -> dict[str, Any]:
    resolved_run_id = run_id or make_run_id()
    run_dir = os.path.join(str(outputs_root), resolved_run_id)

    graph = build_review_graph(progress_hook=progress_hook)
    initial_state: dict[str, Any] = {
        "requirement_doc": requirement_doc,
        "run_dir": run_dir,
    }
    if isinstance(review_mode_override, str) and review_mode_override.strip():
        initial_state["review_mode_override"] = review_mode_override.strip()

    result = await graph.ainvoke(initial_state)
    if not isinstance(result, dict):
        raise ValueError("workflow result must be an object")
    parallel_review_meta = result.get("parallel_review_meta") if isinstance(result.get("parallel_review_meta"), dict) else {}
    if parallel_review_meta:
        result["parallel-review_meta"] = parallel_review_meta

    report_paths = write_outputs(run_dir=run_dir, run_id=resolved_run_id, result=result)
    return {
        "run_id": resolved_run_id,
        "run_dir": run_dir,
        "result": result,
        "report_paths": report_paths,
    }
