"""Minimal MCP server entrypoint (stdio transport).

Run:
    python -m requirement_review_v1.mcp_server.server
"""

from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import Context, FastMCP

from requirement_review_v1.service.execution_service import (
    get_execution_status_for_mcp,
    get_traceability_for_mcp,
    handoff_to_executor_for_mcp,
    list_execution_tasks_for_mcp,
    update_execution_task_for_mcp,
)
from requirement_review_v1.service.report_service import get_report_for_mcp
from requirement_review_v1.service.review_service import (
    approve_handoff_for_mcp,
    generate_delivery_bundle_for_mcp,
    get_review_workspace_for_mcp,
    review_prd_for_mcp_async,
)

mcp = FastMCP("requirement-review-v1")


@mcp.tool()
def ping() -> dict[str, Any]:
    """Health check tool for MCP connectivity."""
    return {"ok": True}


@mcp.tool()
async def review_prd(
    prd_text: str | None = None,
    prd_path: str | None = None,
    source: str | None = None,
    options: dict[str, Any] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Run one PRD review and return run status, metrics and artifact paths."""
    try:
        client_meta = _extract_client_metadata(ctx=ctx, options=options)
        return await review_prd_for_mcp_async(
            prd_text=prd_text,
            prd_path=prd_path,
            source=source,
            options=options,
            invocation_meta={"client_metadata": client_meta} if client_meta else {},
        )
    except FileNotFoundError as exc:
        return _error_response("PRD_NOT_FOUND", str(exc))
    except NotImplementedError as exc:
        return _error_response("NOT_IMPLEMENTED", str(exc))
    except (TypeError, ValueError) as exc:
        return _error_response("INVALID_INPUT", str(exc))
    except Exception as exc:
        return _error_response("INTERNAL_ERROR", f"review_prd failed: {exc}")


@mcp.tool()
def get_report(
    run_id: str,
    format: Literal["md", "json"] = "md",
    offset: int = 0,
    limit: int | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Fetch report artifact content by run_id (supports markdown/json)."""
    try:
        resolved_options = options or {}
        if not isinstance(resolved_options, dict):
            raise TypeError("options must be an object")
        outputs_root = resolved_options.get("outputs_root", "outputs")
        return get_report_for_mcp(
            run_id=run_id,
            format=format,
            offset=offset,
            limit=limit,
            outputs_root=str(outputs_root),
        )
    except (TypeError, ValueError) as exc:
        return {
            "run_id": str(run_id or ""),
            "format": str(format or "md"),
            "content": "",
            "paths": {
                "report_md_path": "",
                "report_json_path": "",
            },
            "error": {"code": "invalid_input", "message": str(exc)},
        }
    except Exception as exc:
        return {
            "run_id": str(run_id or ""),
            "format": str(format or "md"),
            "content": "",
            "paths": {
                "report_md_path": "",
                "report_json_path": "",
            },
            "error": {"code": "internal_error", "message": f"get_report failed: {exc}"},
        }


@mcp.tool()
async def generate_delivery_bundle(
    run_id: str,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate or regenerate the standardized delivery bundle for a completed run."""
    try:
        return generate_delivery_bundle_for_mcp(run_id=run_id, options=options)
    except FileNotFoundError as exc:
        return {"run_id": str(run_id or ""), "error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"run_id": str(run_id or ""), "error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"run_id": str(run_id or ""), "error": {"code": "internal_error", "message": f"generate_delivery_bundle failed: {exc}"}}


@mcp.tool()
def approve_handoff(
    bundle_id: str,
    action: Literal["approve", "need_more_info", "block_by_risk", "reset_to_draft"],
    reviewer: str = "",
    comment: str = "",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one approval operation to a persisted delivery bundle and return updated record paths."""
    try:
        return approve_handoff_for_mcp(
            bundle_id=bundle_id,
            action=action,
            reviewer=reviewer,
            comment=comment,
            options=options,
        )
    except FileNotFoundError as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "internal_error", "message": f"approve_handoff failed: {exc}"}}


@mcp.tool()
async def handoff_to_executor(
    bundle_id: str,
    execution_mode: str = "agent_assisted",
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Turn one approved delivery bundle into persisted execution tasks."""
    try:
        return handoff_to_executor_for_mcp(bundle_id=bundle_id, execution_mode=execution_mode, options=options)
    except FileNotFoundError as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"bundle_id": str(bundle_id or ""), "error": {"code": "internal_error", "message": f"handoff_to_executor failed: {exc}"}}


@mcp.tool()
def update_execution_task(
    task_id: str,
    status: Literal["assigned", "in_progress", "waiting_review", "completed", "failed", "cancelled"],
    actor: str = "",
    assigned_to: str = "",
    detail: str = "",
    result_summary: str = "",
    artifact_paths: dict[str, Any] | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Persist one execution task status update from an external executor callback or polling loop."""
    try:
        return update_execution_task_for_mcp(
            task_id=task_id,
            status=status,
            actor=actor,
            assigned_to=assigned_to,
            detail=detail,
            result_summary=result_summary,
            artifact_paths=artifact_paths,
            options=options,
        )
    except FileNotFoundError as exc:
        return {"task_id": str(task_id or ""), "error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"task_id": str(task_id or ""), "error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"task_id": str(task_id or ""), "error": {"code": "internal_error", "message": f"update_execution_task failed: {exc}"}}


@mcp.tool()
def list_execution_tasks(
    bundle_id: str | None = None,
    status: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """List persisted execution tasks, optionally filtered by bundle or status."""
    try:
        return list_execution_tasks_for_mcp(bundle_id=bundle_id, status=status, options=options)
    except FileNotFoundError as exc:
        return {"error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"error": {"code": "internal_error", "message": f"list_execution_tasks failed: {exc}"}}


@mcp.tool()
def get_review_workspace(
    run_id: str | None = None,
    bundle_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query persisted review workspace state by run or bundle identifier."""
    try:
        return get_review_workspace_for_mcp(run_id=run_id, bundle_id=bundle_id, options=options)
    except FileNotFoundError as exc:
        return {"error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"error": {"code": "internal_error", "message": f"get_review_workspace failed: {exc}"}}


@mcp.tool()
def get_execution_status(
    bundle_id: str | None = None,
    task_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query persisted execution task status by bundle or task identifier."""
    try:
        return get_execution_status_for_mcp(bundle_id=bundle_id, task_id=task_id, options=options)
    except FileNotFoundError as exc:
        return {"error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"error": {"code": "internal_error", "message": f"get_execution_status failed: {exc}"}}


@mcp.tool()
def get_traceability(
    requirement_id: str | None = None,
    task_id: str | None = None,
    bundle_id: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query persisted traceability links by requirement, task, or bundle."""
    try:
        return get_traceability_for_mcp(
            requirement_id=requirement_id,
            task_id=task_id,
            bundle_id=bundle_id,
            options=options,
        )
    except FileNotFoundError as exc:
        return {"error": {"code": "not_found", "message": str(exc)}}
    except (TypeError, ValueError) as exc:
        return {"error": {"code": "invalid_input", "message": str(exc)}}
    except Exception as exc:
        return {"error": {"code": "internal_error", "message": f"get_traceability failed: {exc}"}}


def _extract_client_metadata(ctx: Context | None, options: dict[str, Any] | None) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    if isinstance(options, dict):
        option_meta = options.get("client_metadata")
        if isinstance(option_meta, dict):
            metadata.update(option_meta)

    if ctx is None:
        return metadata

    try:
        client_id = ctx.client_id
        if client_id:
            metadata["client_id"] = client_id
    except Exception:
        pass

    try:
        request_meta = ctx.request_context.meta
        if request_meta is not None:
            request_meta_dump = request_meta.model_dump(exclude_none=True)
            if request_meta_dump:
                metadata["request_meta"] = request_meta_dump
    except Exception:
        pass

    try:
        client_info = getattr(getattr(ctx.request_context.session, "client_params", None), "clientInfo", None)
        if client_info is not None:
            if hasattr(client_info, "model_dump"):
                metadata["client_info"] = client_info.model_dump(exclude_none=True)
            elif isinstance(client_info, dict):
                metadata["client_info"] = client_info
    except Exception:
        pass

    return metadata


def _error_response(code: str, message: str) -> dict[str, Any]:
    return {
        "run_id": "",
        "status": "failed",
        "metrics": {
            "coverage_ratio": 0.0,
            "high_risk_ratio": 0.0,
            "revision_round": 0,
        },
        "artifacts": {
            "report_md_path": "",
            "report_json_path": "",
            "trace_path": "",
        },
        "error": {
            "code": code,
            "message": message,
        },
    }


def main() -> None:
    """Start MCP server over stdio transport."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
