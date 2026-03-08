"""Execution orchestration services used by MCP and other entrypoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from requirement_review_v1.adapters import get_adapter
from requirement_review_v1.execution import ExecutionMode, ExecutionTask, ExecutorRouter, TraceabilityMap
from requirement_review_v1.packs.delivery_bundle import DeliveryBundle
from requirement_review_v1.service.review_service import _load_json_object, _locate_bundle_path, _resolve_outputs_root

TASKS_FILENAME = "execution_tasks.json"
TRACEABILITY_FILENAME = "traceability_map.json"


def _resolve_mode(execution_mode: str) -> ExecutionMode:
    normalized = str(execution_mode or "").strip()
    try:
        return ExecutionMode(normalized)
    except ValueError as exc:
        allowed = ", ".join(mode.value for mode in ExecutionMode)
        raise ValueError(f"execution_mode must be one of: {allowed}") from exc


def _validate_options(options: dict[str, Any] | None) -> dict[str, Any]:
    resolved = options or {}
    if not isinstance(resolved, dict):
        raise TypeError("options must be an object")
    return resolved


def _load_bundle_context(bundle_id: str, outputs_root: str | Path) -> tuple[Path, Path, DeliveryBundle]:
    bundle_path = _locate_bundle_path(bundle_id, outputs_root)
    bundle = DeliveryBundle.model_validate(_load_json_object(bundle_path))
    return bundle_path, bundle_path.parent, bundle


def _tasks_path(run_dir: Path) -> Path:
    return run_dir / TASKS_FILENAME


def _traceability_path(run_dir: Path) -> Path:
    return run_dir / TRACEABILITY_FILENAME


def _save_tasks(tasks: list[ExecutionTask], run_dir: Path) -> Path:
    path = _tasks_path(run_dir)
    payload = {"tasks": [task.model_dump(mode="python") for task in tasks]}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_tasks(run_dir: Path) -> list[ExecutionTask]:
    payload = _load_json_object(_tasks_path(run_dir))
    raw_tasks = payload.get("tasks")
    if not isinstance(raw_tasks, list):
        return []
    return [ExecutionTask.model_validate(item) for item in raw_tasks if isinstance(item, dict)]


def _load_traceability_payload(run_dir: Path) -> dict[str, Any]:
    return _load_json_object(_traceability_path(run_dir))


def _find_all_run_dirs(outputs_root: str | Path) -> list[Path]:
    root = _resolve_outputs_root(outputs_root)
    if not root.exists():
        return []
    return [path for path in root.iterdir() if path.is_dir()]


def _resolve_adapter(executor_type: str):
    normalized = str(executor_type or "").strip()
    try:
        return get_adapter(normalized)
    except ValueError as exc:
        raise ValueError(f"no adapter available for executor_type '{normalized}'") from exc


def _sanitize_filename_fragment(value: str) -> str:
    raw = str(value or "").strip()
    normalized = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in raw)
    normalized = normalized.strip("_")
    return normalized or "task"


def _task_context_path(run_dir: Path, task: ExecutionTask) -> Path:
    return run_dir / f"{_sanitize_filename_fragment(task.task_id)}_execution_context.md"


def _rewrite_request_context_paths(request_payload: dict[str, Any], context_path: Path) -> dict[str, Any]:
    payload = dict(request_payload)
    payload["context_path"] = str(context_path)

    current_input = payload.get("input")
    if isinstance(current_input, dict):
        updated_input = dict(current_input)
        updated_input["context_file"] = str(context_path)
        payload["input"] = updated_input

    current_callback = payload.get("callback")
    if isinstance(current_callback, dict):
        updated_callback = dict(current_callback)
        updated_callback["context_file"] = str(context_path)
        payload["callback"] = updated_callback

    return payload


def _attach_adapter_artifacts(
    task: ExecutionTask,
    *,
    request_path: Path,
    context_path: Path,
    request_payload: dict[str, Any],
) -> ExecutionTask:
    payload = task.model_dump(mode="python")
    metadata = dict(task.metadata or {})
    metadata["adapter_artifacts"] = {
        "adapter": task.executor_type,
        "request_path": str(request_path),
        "context_path": str(context_path),
        "request_type": str(request_payload.get("request_type", "") or ""),
    }
    payload["metadata"] = metadata
    return ExecutionTask.model_validate(payload)


def _materialize_adapter_requests(tasks: list[ExecutionTask], bundle: DeliveryBundle, run_dir: Path) -> list[ExecutionTask]:
    materialized_tasks: list[ExecutionTask] = []
    for task in tasks:
        adapter = _resolve_adapter(task.executor_type)
        result = adapter.build_pack({"task": task, "bundle": bundle})

        request_path = Path(str(result.get("request_path", "")).strip())
        request_payload = result.get("request") if isinstance(result.get("request"), dict) else {}
        if not request_path.name:
            raise ValueError(f"adapter did not return a request path for task '{task.task_id}'")
        if not request_payload:
            request_payload = _load_json_object(request_path)

        temporary_context_path = Path(str(result.get("context_path", "")).strip())
        final_context_path = _task_context_path(run_dir, task)
        if temporary_context_path.exists():
            final_context_path.write_text(temporary_context_path.read_text(encoding="utf-8"), encoding="utf-8")
            if temporary_context_path != final_context_path:
                temporary_context_path.unlink()

        updated_request_payload = _rewrite_request_context_paths(request_payload, final_context_path)
        request_path.write_text(json.dumps(updated_request_payload, ensure_ascii=False, indent=2), encoding="utf-8")

        materialized_tasks.append(
            _attach_adapter_artifacts(
                task,
                request_path=request_path,
                context_path=final_context_path,
                request_payload=updated_request_payload,
            )
        )
    return materialized_tasks


def handoff_to_executor_for_mcp(
    *,
    bundle_id: str,
    execution_mode: str = "agent_assisted",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = _validate_options(options)
    _, run_dir, bundle = _load_bundle_context(bundle_id, resolved_options.get("outputs_root", "outputs"))
    router = ExecutorRouter(default_mode=_resolve_mode(execution_mode))
    tasks = router.route(bundle)
    tasks = _materialize_adapter_requests(tasks, bundle, run_dir)
    tasks_path = _save_tasks(tasks, run_dir)

    traceability = TraceabilityMap().build_from_bundle(bundle, tasks)
    traceability_path = _traceability_path(run_dir)
    traceability.save(traceability_path)

    return {
        "bundle_id": bundle.bundle_id,
        "status": "routed",
        "task_count": len(tasks),
        "tasks": [task.model_dump(mode="python") for task in tasks],
        "paths": {
            "bundle_path": str(run_dir / "delivery_bundle.json"),
            "tasks_path": str(tasks_path),
            "traceability_path": str(traceability_path),
        },
    }


def get_execution_status_for_mcp(
    *,
    bundle_id: str | None = None,
    task_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = _validate_options(options)
    outputs_root = resolved_options.get("outputs_root", "outputs")
    if bool(str(bundle_id or "").strip()) == bool(str(task_id or "").strip()):
        raise ValueError("provide exactly one of bundle_id or task_id")

    if bundle_id:
        _, run_dir, bundle = _load_bundle_context(bundle_id, outputs_root)
        tasks = _load_tasks(run_dir)
        traceability = _load_traceability_payload(run_dir)
        return {
            "bundle_id": bundle.bundle_id,
            "task_count": len(tasks),
            "tasks": [task.model_dump(mode="python") for task in tasks],
            "traceability": traceability,
        }

    normalized_task_id = str(task_id or "").strip()
    for run_dir in _find_all_run_dirs(outputs_root):
        tasks = _load_tasks(run_dir)
        for task in tasks:
            if task.task_id == normalized_task_id:
                traceability = _load_traceability_payload(run_dir)
                links = [link for link in traceability.get("links", []) if isinstance(link, dict) and link.get("execution_task_id") == normalized_task_id]
                return {
                    "bundle_id": task.bundle_id,
                    "task": task.model_dump(mode="python"),
                    "traceability": {"links": links, "counts": {"total": len(links)}},
                }
    raise FileNotFoundError(f"execution task not found: {normalized_task_id}")


def get_traceability_for_mcp(
    *,
    requirement_id: str | None = None,
    task_id: str | None = None,
    bundle_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = _validate_options(options)
    outputs_root = resolved_options.get("outputs_root", "outputs")
    requirement_key = str(requirement_id or "").strip()
    task_key = str(task_id or "").strip()
    bundle_key = str(bundle_id or "").strip()
    if not any((requirement_key, task_key, bundle_key)):
        raise ValueError("provide at least one of requirement_id, task_id, or bundle_id")

    if bundle_key:
        _, run_dir, bundle = _load_bundle_context(bundle_key, outputs_root)
        payload = _load_traceability_payload(run_dir)
        payload["bundle_id"] = bundle.bundle_id
        return payload

    matching_links: list[dict[str, Any]] = []
    matched_bundles: list[str] = []
    for run_dir in _find_all_run_dirs(outputs_root):
        payload = _load_traceability_payload(run_dir)
        links = payload.get("links")
        if not isinstance(links, list):
            continue
        filtered = []
        for link in links:
            if not isinstance(link, dict):
                continue
            if requirement_key and link.get("requirement_id") != requirement_key:
                continue
            if task_key and link.get("execution_task_id") != task_key:
                continue
            filtered.append(link)
        if filtered:
            matching_links.extend(filtered)
            matched_bundles.append(run_dir.name)

    return {
        "links": matching_links,
        "count": len(matching_links),
        "bundles": matched_bundles,
    }
