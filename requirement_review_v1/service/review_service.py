"""Reusable review service API for CLI/FastAPI/MCP entrypoints."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

from requirement_review_v1.handoff import render_claude_code_prompt, render_codex_prompt
from requirement_review_v1.packs import (
    ArtifactSplitter,
    DeliveryBundle,
    DeliveryBundleBuilder,
    ExecutionPackBuilder,
    ImplementationPackBuilder,
    TestPackBuilder,
    approve_bundle,
    block_by_risk,
    request_more_info,
    reset_to_draft,
)
from requirement_review_v1.run_review import run_review
from requirement_review_v1.service.report_service import RUN_ID_PATTERN


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
    implementation_pack_path: str = ""
    test_pack_path: str = ""
    execution_pack_path: str = ""
    delivery_bundle_path: str = ""

    def to_report_paths(self) -> dict[str, str]:
        return {
            "report_md": self.report_md_path,
            "report_json": self.report_json_path,
            "run_trace": self.run_trace_path,
            "implementation_pack": self.implementation_pack_path,
            "test_pack": self.test_pack_path,
            "execution_pack": self.execution_pack_path,
            "delivery_bundle": self.delivery_bundle_path,
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
        if span.get("non_blocking") is True:
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
        implementation_pack_path=str(report_paths.get("implementation_pack", "")),
        test_pack_path=str(report_paths.get("test_pack", "")),
        execution_pack_path=str(report_paths.get("execution_pack", "")),
        delivery_bundle_path=str(report_paths.get("delivery_bundle", "")),
        high_risk_ratio=_to_float(result.get("high_risk_ratio") if isinstance(result, dict) else 0.0),
        coverage_ratio=_to_float(metrics.get("coverage_ratio") if isinstance(metrics, dict) else 0.0),
        revision_round=int((result.get("revision_round", 0) if isinstance(result, dict) else 0) or 0),
        status=_derive_status(result if isinstance(result, dict) else {}),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_outputs_root(outputs_root: str | Path = "outputs") -> Path:
    return Path(outputs_root).resolve()


def _resolve_run_dir(run_id: str, outputs_root: str | Path = "outputs") -> Path:
    normalized_run_id = str(run_id or "").strip()
    if not RUN_ID_PATTERN.fullmatch(normalized_run_id):
        raise ValueError("run_id must match YYYYMMDDTHHMMSSZ")
    outputs_root_path = _resolve_outputs_root(outputs_root)
    run_dir = (outputs_root_path / normalized_run_id).resolve()
    if outputs_root_path not in run_dir.parents and run_dir != outputs_root_path:
        raise ValueError("run_id resolves outside outputs root")
    if not run_dir.exists() or not run_dir.is_dir():
        raise FileNotFoundError(f"run_id not found: {normalized_run_id}")
    return run_dir


def _locate_bundle_path(bundle_id: str, outputs_root: str | Path = "outputs") -> Path:
    normalized_bundle_id = str(bundle_id or "").strip()
    if not normalized_bundle_id:
        raise ValueError("bundle_id is required")
    outputs_root_path = _resolve_outputs_root(outputs_root)
    for candidate in outputs_root_path.glob("*/delivery_bundle.json"):
        payload = _load_json_object(candidate)
        if payload.get("bundle_id") == normalized_bundle_id:
            return candidate
    raise FileNotFoundError(f"delivery bundle not found: {normalized_bundle_id}")


def _generate_delivery_bundle(run_output: dict[str, Any]) -> tuple[dict[str, str], DeliveryBundle]:
    result = run_output.get("result", {})
    if not isinstance(result, dict):
        raise TypeError("run_output.result must be an object")

    run_dir_raw = str(run_output.get("run_dir", "") or "")
    if not run_dir_raw:
        raise ValueError("run_dir is required")
    run_dir = Path(run_dir_raw)

    report_paths = run_output.get("report_paths", {})
    pack_paths = {
        "implementation_pack": str(report_paths.get("implementation_pack", "") or ""),
        "test_pack": str(report_paths.get("test_pack", "") or ""),
        "execution_pack": str(report_paths.get("execution_pack", "") or ""),
    }
    missing = [name for name, path in pack_paths.items() if not path]
    if missing:
        raise ValueError(f"missing pack paths: {', '.join(missing)}")

    artifact_refs = ArtifactSplitter().split(result, run_dir)
    bundle = DeliveryBundleBuilder().build(run_output=run_output, artifact_refs=artifact_refs, pack_paths=pack_paths)
    bundle_path = DeliveryBundleBuilder().save(bundle, run_dir)

    artifact_paths = {artifact_type: ref.path for artifact_type, ref in artifact_refs.items()}
    artifact_paths["delivery_bundle"] = str(bundle_path)
    return artifact_paths, bundle


def build_handoff_prompts(
    execution_pack_path: str | Path | None,
    *,
    trace: dict[str, Any] | None = None,
) -> dict[str, str]:
    renderer_trace: dict[str, Any] = {
        "start": _utc_now_iso(),
        "end": "",
        "duration_ms": 0,
        "status": "running",
        "template_version": "handoff_markdown_v1",
        "output_paths": {},
        "error_message": "",
        "non_blocking": True,
    }
    prompt_paths: dict[str, str] = {}
    handoff_render_error = ""
    started = perf_counter()

    try:
        execution_pack_path_str = str(execution_pack_path or "").strip()
        if not execution_pack_path_str:
            renderer_trace["status"] = "skipped"
            renderer_trace["error_message"] = "execution_pack_path_missing"
            return {}

        execution_pack_file = Path(execution_pack_path_str)
        if not execution_pack_file.exists():
            renderer_trace["status"] = "skipped"
            renderer_trace["error_message"] = "execution_pack_not_found"
            return {}

        execution_pack = json.loads(execution_pack_file.read_text(encoding="utf-8"))
        output_dir = execution_pack_file.parent
        render_targets = (
            ("codex_prompt", output_dir / "codex_prompt.md", render_codex_prompt),
            ("claude_code_prompt", output_dir / "claude_code_prompt.md", render_claude_code_prompt),
        )
        render_failures: list[str] = []

        for prompt_name, output_path, renderer in render_targets:
            try:
                rendered = renderer(execution_pack)
                output_path.write_text(rendered, encoding="utf-8")
                prompt_paths[prompt_name] = str(output_path)
            except Exception as exc:
                render_failures.append(prompt_name)
                if not handoff_render_error:
                    handoff_render_error = str(exc)

        renderer_trace["output_paths"] = dict(prompt_paths)
        if not render_failures:
            renderer_trace["status"] = "ok"
        elif len(render_failures) == len(render_targets):
            renderer_trace["status"] = "failed"
        else:
            renderer_trace["status"] = "partial_success"
        renderer_trace["error_message"] = ", ".join(render_failures) if render_failures else ""
    except Exception as exc:
        handoff_render_error = str(exc)
        renderer_trace["status"] = "failed"
        renderer_trace["error_message"] = str(exc)
    finally:
        renderer_trace["end"] = _utc_now_iso()
        renderer_trace["duration_ms"] = round((perf_counter() - started) * 1000)
        if isinstance(trace, dict):
            trace["handoff_renderer"] = renderer_trace
            if handoff_render_error:
                trace["handoff_render_error"] = handoff_render_error

    return prompt_paths


def build_delivery_handoff_outputs(run_output: dict[str, Any]) -> dict[str, str]:
    result = run_output.get("result", {})
    if not isinstance(result, dict):
        return {}

    run_dir_raw = str(run_output.get("run_dir", "") or "")
    if not run_dir_raw:
        return {}
    run_dir = Path(run_dir_raw)
    run_dir.mkdir(parents=True, exist_ok=True)

    trace = result.get("trace")
    if not isinstance(trace, dict):
        trace = {}
        result["trace"] = trace

    started = perf_counter()
    pack_builder_trace: dict[str, Any] = {
        "start": _utc_now_iso(),
        "end": "",
        "duration_ms": 0,
        "status": "running",
        "input_chars": len(json.dumps(result, ensure_ascii=False, default=str)),
        "output_chars": 0,
        "model": "none",
        "prompt_version": "handoff_pack_v1",
        "raw_output_path": "",
        "error_message": "",
        "non_blocking": True,
        "packs": {},
    }

    builder_inputs = {
        "requirements": result.get("parsed_items"),
        "tasks": result.get("tasks"),
        "risks": result.get("risks"),
        "implementation_plan_output": result.get("implementation_plan"),
        "test_plan_output": result.get("test_plan"),
        "codex_prompt_output": result.get("codex_prompt_handoff"),
        "claude_code_prompt_output": result.get("claude_code_prompt_handoff"),
    }
    builders = (
        ("implementation_pack", ImplementationPackBuilder(), run_dir / "implementation_pack.json"),
        ("test_pack", TestPackBuilder(), run_dir / "test_pack.json"),
        ("execution_pack", ExecutionPackBuilder(), run_dir / "execution_pack.json"),
    )

    artifact_paths: dict[str, str] = {}
    failed_packs: list[str] = []

    for pack_name, builder, output_path in builders:
        pack_started = perf_counter()
        pack_trace = {
            "status": "running",
            "duration_ms": 0,
            "output_path": str(output_path),
            "error_message": "",
        }
        try:
            pack = builder.build(**builder_inputs)
            payload = pack.model_dump(mode="python")
            serialized = json.dumps(payload, ensure_ascii=False, indent=2)
            output_path.write_text(serialized, encoding="utf-8")
            artifact_paths[pack_name] = str(output_path)
            pack_trace["status"] = "ok"
        except Exception as exc:
            failed_packs.append(pack_name)
            pack_trace["status"] = "error"
            pack_trace["error_message"] = str(exc)
        finally:
            pack_trace["duration_ms"] = round((perf_counter() - pack_started) * 1000)
            pack_builder_trace["packs"][pack_name] = pack_trace

    pack_builder_trace["end"] = _utc_now_iso()
    pack_builder_trace["duration_ms"] = round((perf_counter() - started) * 1000)
    if not failed_packs:
        pack_builder_trace["status"] = "ok"
    elif len(failed_packs) == len(builders):
        pack_builder_trace["status"] = "failed"
    else:
        pack_builder_trace["status"] = "partial_success"
    pack_builder_trace["error_message"] = ", ".join(failed_packs)
    pack_builder_trace["output_chars"] = sum(
        len(Path(path).read_text(encoding="utf-8"))
        for path in artifact_paths.values()
        if Path(path).exists()
    )
    trace["pack_builder"] = pack_builder_trace

    prompt_paths = build_handoff_prompts(artifact_paths.get("execution_pack"), trace=trace)
    artifact_paths.update(prompt_paths)

    bundle_builder_trace: dict[str, Any] = {
        "start": _utc_now_iso(),
        "end": "",
        "duration_ms": 0,
        "status": "running",
        "error_message": "",
        "non_blocking": True,
        "output_paths": {},
    }
    bundle_started = perf_counter()
    try:
        report_paths = run_output.get("report_paths", {})
        if isinstance(report_paths, dict):
            report_paths.update(artifact_paths)
        bundle_artifact_paths, _bundle = _generate_delivery_bundle(run_output)
        artifact_paths.update(bundle_artifact_paths)
        if isinstance(report_paths, dict):
            report_paths.update(bundle_artifact_paths)
        bundle_builder_trace["status"] = "ok"
        bundle_builder_trace["output_paths"] = bundle_artifact_paths
    except Exception as exc:
        bundle_builder_trace["status"] = "failed"
        bundle_builder_trace["error_message"] = str(exc)
    finally:
        bundle_builder_trace["end"] = _utc_now_iso()
        bundle_builder_trace["duration_ms"] = round((perf_counter() - bundle_started) * 1000)
        trace["bundle_builder"] = bundle_builder_trace

    report_paths = run_output.get("report_paths", {})
    if isinstance(report_paths, dict):
        report_paths.update(artifact_paths)

    trace_path_raw = str(report_paths.get("run_trace", "") or "")
    if trace_path_raw:
        Path(trace_path_raw).write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    report_json_raw = str(report_paths.get("report_json", "") or "")
    if report_json_raw:
        report_json_path = Path(report_json_raw)
        report_payload = _load_json_object(report_json_path)
        if report_payload:
            report_trace = report_payload.get("trace")
            if not isinstance(report_trace, dict):
                report_trace = {}
            report_trace["pack_builder"] = pack_builder_trace
            handoff_renderer_trace = trace.get("handoff_renderer")
            if isinstance(handoff_renderer_trace, dict):
                report_trace["handoff_renderer"] = handoff_renderer_trace
            if "handoff_render_error" in trace:
                report_trace["handoff_render_error"] = trace["handoff_render_error"]
            report_trace["bundle_builder"] = bundle_builder_trace
            report_payload["trace"] = report_trace

            artifacts = report_payload.get("artifacts")
            if not isinstance(artifacts, dict):
                artifacts = {}
            artifacts.update(artifact_paths)
            report_payload["artifacts"] = artifacts
            report_json_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return artifact_paths


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
    build_delivery_handoff_outputs(run_output)
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
    has_prd_text = isinstance(prd_text, str) and bool(prd_text.strip())
    has_prd_path = isinstance(prd_path, str) and bool(prd_path.strip())

    if has_prd_text and has_prd_path:
        raise ValueError("Provide only one of prd_text or prd_path")
    if has_prd_text:
        return prd_text
    if has_prd_path:
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


def generate_delivery_bundle_for_mcp(
    *,
    run_id: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = options or {}
    if not isinstance(resolved_options, dict):
        raise TypeError("options must be an object")

    outputs_root = resolved_options.get("outputs_root", "outputs")
    run_dir = _resolve_run_dir(run_id, outputs_root)
    report_json = _load_json_object(run_dir / "report.json")
    if not report_json:
        raise FileNotFoundError(f"report.json not found for run_id={run_id}")

    run_output = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "result": report_json,
        "report_paths": {
            "report_md": str(run_dir / "report.md"),
            "report_json": str(run_dir / "report.json"),
            "run_trace": str(run_dir / "run_trace.json"),
            "implementation_pack": str(run_dir / "implementation_pack.json"),
            "test_pack": str(run_dir / "test_pack.json"),
            "execution_pack": str(run_dir / "execution_pack.json"),
        },
    }
    artifact_paths, bundle = _generate_delivery_bundle(run_output)
    report_payload = _load_json_object(run_dir / "report.json")
    artifacts = report_payload.get("artifacts") if isinstance(report_payload, dict) else {}
    if not isinstance(artifacts, dict):
        artifacts = {}
    artifacts.update(artifact_paths)
    if isinstance(report_payload, dict):
        report_payload["artifacts"] = artifacts
        (run_dir / "report.json").write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "run_id": run_id,
        "bundle_id": bundle.bundle_id,
        "status": bundle.status,
        "artifacts": artifact_paths,
    }


def approve_handoff_for_mcp(
    *,
    bundle_id: str,
    action: str,
    reviewer: str = "",
    comment: str = "",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    resolved_options = options or {}
    if not isinstance(resolved_options, dict):
        raise TypeError("options must be an object")

    bundle_path = _locate_bundle_path(bundle_id, resolved_options.get("outputs_root", "outputs"))
    bundle = DeliveryBundle.model_validate(_load_json_object(bundle_path))

    actions = {
        "approve": approve_bundle,
        "need_more_info": request_more_info,
        "block_by_risk": block_by_risk,
        "reset_to_draft": reset_to_draft,
    }
    if action not in actions:
        raise ValueError("action must be one of approve, need_more_info, block_by_risk, reset_to_draft")

    updated_bundle = actions[action](bundle, reviewer, comment)
    bundle_path.write_text(json.dumps(updated_bundle.model_dump(mode="python"), ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "bundle_id": updated_bundle.bundle_id,
        "status": updated_bundle.status,
        "approval_history": [event.model_dump(mode="python") for event in updated_bundle.approval_history],
        "bundle_path": str(bundle_path),
    }


async def review_prd_for_mcp_async(
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

    summary = await review_prd_text_async(
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
            "implementation_pack_path": summary.implementation_pack_path,
            "test_pack_path": summary.test_pack_path,
            "execution_pack_path": summary.execution_pack_path,
            "delivery_bundle_path": summary.delivery_bundle_path,
        },
    }


def review_prd_for_mcp(
    *,
    prd_text: str | None,
    prd_path: str | None,
    options: dict[str, Any] | None = None,
    invocation_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            review_prd_for_mcp_async(
                prd_text=prd_text,
                prd_path=prd_path,
                options=options,
                invocation_meta=invocation_meta,
            )
        )
    raise RuntimeError("review_prd_for_mcp cannot run inside an active event loop; use review_prd_for_mcp_async")
