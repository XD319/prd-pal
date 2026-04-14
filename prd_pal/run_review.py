"""Shared runner for prd_pal CLI and API."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .review.memory_store import FileBackedMemoryStore, NoopMemoryStore
from .review.normalizer import NormalizedRequirement, normalize_requirement
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
        "project": "prd_pal",
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


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_memory_config(
    *,
    outputs_root: str | Path,
    review_memory_path: str | Path | None,
    review_memory_enabled: bool | None,
    review_memory_seeds_dir: str | Path | None,
) -> dict[str, Any]:
    configured_path = str(review_memory_path or "").strip()
    enabled = review_memory_enabled if review_memory_enabled is not None else _truthy(os.getenv("REVIEW_MEMORY_ENABLED", ""))
    if not configured_path and enabled:
        configured_path = str(Path(outputs_root) / "_memory" / "review_memory.json")
    return {
        "enabled": bool(enabled or configured_path),
        "path": configured_path,
        "seeds_dir": str(review_memory_seeds_dir or os.getenv("REVIEW_MEMORY_SEEDS_DIR", "")).strip(),
    }


def _resolve_normalizer_cache_config(normalizer_cache_path: str | Path | None) -> dict[str, Any]:
    configured_path = str(normalizer_cache_path or os.getenv("NORMALIZER_CACHE_PATH", "")).strip()
    return {"path": configured_path}


def _resolve_memory_store(memory_config: dict[str, Any]):
    storage_path = str(memory_config.get("path", "") or "").strip()
    seeds_dir = str(memory_config.get("seeds_dir", "") or "").strip()
    if not storage_path:
        return NoopMemoryStore()
    return FileBackedMemoryStore(storage_path, seeds_dir=seeds_dir or None)


def _normalized_requirement_from_state(result: dict[str, Any], requirement_doc: str) -> NormalizedRequirement:
    payload = result.get("normalized_requirement") if isinstance(result.get("normalized_requirement"), dict) else {}
    if payload:
        return NormalizedRequirement(
            source_text=str(payload.get("source_text", "") or requirement_doc),
            summary=str(payload.get("summary", "") or ""),
            scenarios=tuple(str(item) for item in payload.get("scenarios", []) or []),
            acceptance_criteria=tuple(str(item) for item in payload.get("acceptance_criteria", []) or []),
            dependency_hints=tuple(str(item) for item in payload.get("dependency_hints", []) or []),
            risk_hints=tuple(str(item) for item in payload.get("risk_hints", []) or []),
            modules=tuple(str(item) for item in payload.get("modules", []) or []),
            roles=tuple(str(item) for item in payload.get("roles", []) or []),
            headings=tuple(str(item) for item in payload.get("headings", []) or []),
            in_scope=tuple(str(item) for item in payload.get("in_scope", []) or []),
            out_of_scope=tuple(str(item) for item in payload.get("out_of_scope", []) or []),
            completeness_signals=tuple(str(item) for item in payload.get("completeness_signals", []) or []),
        )
    return normalize_requirement(requirement_doc)


async def run_review(
    requirement_doc: str,
    *,
    run_id: str | None = None,
    outputs_root: str | Path = "outputs",
    progress_hook: ProgressHook | None = None,
    review_mode_override: str | None = None,
    mode: str | None = None,
    review_memory_path: str | Path | None = None,
    review_memory_enabled: bool | None = None,
    review_memory_seeds_dir: str | Path | None = None,
    normalizer_cache_path: str | Path | None = None,
    review_profile: dict[str, Any] | None = None,
    review_profile_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_run_id = run_id or make_run_id()
    run_dir = os.path.join(str(outputs_root), resolved_run_id)
    memory_config = _resolve_memory_config(
        outputs_root=outputs_root,
        review_memory_path=review_memory_path,
        review_memory_enabled=review_memory_enabled,
        review_memory_seeds_dir=review_memory_seeds_dir,
    )
    normalizer_cache_config = _resolve_normalizer_cache_config(normalizer_cache_path)

    graph = build_review_graph(progress_hook=progress_hook)
    initial_state: dict[str, Any] = {
        "requirement_doc": requirement_doc,
        "run_dir": run_dir,
        "memory_config": memory_config,
        "normalizer_cache_config": normalizer_cache_config,
        "review_profile": dict(review_profile or {}),
        "review_profile_pack": dict(review_profile_pack or {}),
    }
    if isinstance(review_mode_override, str) and review_mode_override.strip():
        initial_state["review_mode_override"] = review_mode_override.strip()
    if isinstance(mode, str) and mode.strip():
        initial_state["mode"] = mode.strip()

    result = await graph.ainvoke(initial_state)
    if not isinstance(result, dict):
        raise ValueError("workflow result must be an object")
    parallel_review_meta = result.get("parallel_review_meta") if isinstance(result.get("parallel_review_meta"), dict) else {}
    if parallel_review_meta:
        result["parallel-review_meta"] = parallel_review_meta

    memory_store = _resolve_memory_store(memory_config)
    if not isinstance(memory_store, NoopMemoryStore):
        memory_store.import_seeds()
        memory_store.store_review_case(
            run_id=resolved_run_id,
            requirement=_normalized_requirement_from_state(result, requirement_doc),
            review_payload=result.get("parallel_review") if isinstance(result.get("parallel_review"), dict) else result,
        )

    report_paths = write_outputs(run_dir=run_dir, run_id=resolved_run_id, result=result)
    return {
        "run_id": resolved_run_id,
        "run_dir": run_dir,
        "result": result,
        "report_paths": report_paths,
    }
