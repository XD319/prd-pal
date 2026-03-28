from __future__ import annotations

import asyncio
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, model_validator

from requirement_review_v1.monitoring import query_audit_events
from requirement_review_v1.run_review import make_run_id
from requirement_review_v1.server.sse import ProgressBroadcaster
from requirement_review_v1.service.review_service import (
    ReviewArtifactNotFoundError,
    ReviewResultNotReadyError,
    ReviewRunNotFoundError,
    answer_review_clarification,
    classify_review_input_error,
    get_review_artifact_preview_payload,
    get_review_result_payload,
    review_prd_text_async,
)
from requirement_review_v1.service.report_service import RUN_ID_PATTERN
from requirement_review_v1.templates import TemplateRegistryError, list_template_records

OUTPUTS_ROOT = Path("outputs")
FRONTEND_DIST_ROOT = Path(__file__).resolve().parents[2] / "frontend" / "dist"
RUN_PROGRESS_FILENAME = "run_progress.json"
PRIMARY_NODES = (
    "parser",
    "parallel_start",
    "planner",
    "risk",
    "review_join",
    "delivery_planning",
    "reviewer",
    "route_decider",
    "reporter",
    "finalize_artifacts",
)
TRACKED_NODES = PRIMARY_NODES + ("clarify",)
NODE_ORDER = (
    "parser",
    "parallel_start",
    "planner",
    "risk",
    "review_join",
    "delivery_planning",
    "reviewer",
    "route_decider",
    "clarify",
    "reporter",
    "finalize_artifacts",
)
RUN_LIST_ARTIFACTS: dict[str, str] = {
    "report_md": "report.md",
    "report_json": "report.json",
    "run_trace": "run_trace.json",
    "review_report_json": "review_report.json",
    "risk_items_json": "risk_items.json",
    "open_questions_json": "open_questions.json",
    "review_summary_md": "review_summary.md",
}
_API_AUTH_DISABLED_ENV = "MARRDP_API_AUTH_DISABLED"
_API_KEY_ENV = "MARRDP_API_KEY"
_API_BEARER_TOKEN_ENV = "MARRDP_API_BEARER_TOKEN"
_API_RATE_LIMIT_DISABLED_ENV = "MARRDP_API_RATE_LIMIT_DISABLED"
_API_RATE_LIMIT_MAX_REQUESTS_ENV = "MARRDP_API_RATE_LIMIT_MAX_REQUESTS"
_API_RATE_LIMIT_WINDOW_SEC_ENV = "MARRDP_API_RATE_LIMIT_WINDOW_SEC"
_FALSE_VALUES = {"0", "false", "no", "off"}
_submission_rate_limits: dict[str, deque[float]] = defaultdict(deque)
_submission_rate_limit_lock = threading.Lock()


@dataclass(frozen=True)
class ApiSecuritySettings:
    auth_disabled: bool = True
    api_key: str = ""
    bearer_token: str = ""
    rate_limit_disabled: bool = True
    rate_limit_max_requests: int = 5
    rate_limit_window_sec: int = 60


def _run_id_to_datetime(run_id: str) -> datetime | None:
    normalized = str(run_id or "").strip()
    if not RUN_ID_PATTERN.fullmatch(normalized):
        return None
    return datetime.strptime(normalized, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


def _timestamp_to_iso(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _safe_iso_to_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or "").strip())
    except ValueError:
        return None


def _artifact_presence(run_dir: Path) -> dict[str, bool]:
    return {key: (run_dir / filename).exists() for key, filename in RUN_LIST_ARTIFACTS.items()}


def _latest_run_timestamp(run_dir: Path) -> float:
    timestamps = [run_dir.stat().st_mtime]
    for child in run_dir.iterdir():
        try:
            timestamps.append(child.stat().st_mtime)
        except OSError:
            continue
    return max(timestamps)


def _build_run_list_entry(run_dir: Path, job: JobRecord | None = None) -> dict[str, Any]:
    run_id = run_dir.name
    artifacts = _artifact_presence(run_dir)

    if job is not None:
        created_dt = _safe_iso_to_datetime(job.created_at)
        if created_dt is None:
            created_dt = _run_id_to_datetime(run_id)
        created_at = created_dt.isoformat() if created_dt else _timestamp_to_iso(run_dir.stat().st_ctime)

        updated_dt = _safe_iso_to_datetime(job.updated_at)
        updated_at = updated_dt.isoformat() if updated_dt else _timestamp_to_iso(_latest_run_timestamp(run_dir))
        status = job.status
    else:
        persisted = _persisted_status_payload(run_id, run_dir)
        created_dt = _safe_iso_to_datetime(str(persisted.get("created_at", "") or ""))
        if created_dt is None:
            created_dt = _run_id_to_datetime(run_id)
        created_at = created_dt.isoformat() if created_dt else _timestamp_to_iso(run_dir.stat().st_ctime)

        updated_dt = _safe_iso_to_datetime(str(persisted.get("updated_at", "") or ""))
        updated_at = updated_dt.isoformat() if updated_dt else _timestamp_to_iso(_latest_run_timestamp(run_dir))
        status = str(persisted.get("status", "failed") or "failed")

    return {
        "run_id": run_id,
        "status": status,
        "created_at": created_at,
        "updated_at": updated_at,
        "artifact_presence": artifacts,
    }


def _run_sort_timestamp(run_dir: Path, job: JobRecord | None = None) -> float:
    if job is not None:
        created_dt = _safe_iso_to_datetime(job.created_at)
        if created_dt is not None:
            return created_dt.timestamp()
    run_dt = _run_id_to_datetime(run_dir.name)
    if run_dt is not None:
        return run_dt.timestamp()
    return _latest_run_timestamp(run_dir)


def _ordered_node_names(nodes: dict[str, Any]) -> list[str]:
    known = [name for name in NODE_ORDER if name in nodes]
    extras = sorted(name for name in nodes if name not in NODE_ORDER)
    return [*known, *extras]


class ReviewCreateRequest(BaseModel):
    prd_text: str | None = None
    prd_path: str | None = None
    source: str | None = None
    mode: Literal["auto", "quick", "full"] | None = None
    fast_llm: str | None = None
    smart_llm: str | None = None
    strategic_llm: str | None = None
    temperature: float | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None
    llm_kwargs: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _validate_input(self) -> "ReviewCreateRequest":
        has_source = bool(self.source and self.source.strip())
        if has_source:
            return self

        has_text = bool(self.prd_text and self.prd_text.strip())
        has_path = bool(self.prd_path and self.prd_path.strip())
        if has_text == has_path:
            raise ValueError("Provide source, or exactly one of prd_text or prd_path.")
        return self


class ClarificationAnswerItem(BaseModel):
    question_id: str
    answer: str


class ClarificationAnswerRequest(BaseModel):
    answers: list[ClarificationAnswerItem]


@dataclass
class JobRecord:
    run_id: str
    run_dir: Path
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    current_node: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: str = ""
    error_code: str = ""
    report_paths: dict[str, str] = field(default_factory=dict)
    node_progress: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {name: {"status": "pending", "runs": 0} for name in TRACKED_NODES}
    )
    task: asyncio.Task[Any] | None = None

    def as_progress_payload(self) -> dict[str, Any]:
        ordered_nodes = {name: self.node_progress[name] for name in _ordered_node_names(self.node_progress)}
        return {
            "percent": _progress_percent_from_nodes(ordered_nodes, status=self.status),
            "current_node": self.current_node,
            "nodes": ordered_nodes,
            "updated_at": self.updated_at,
            "error": self.error,
        }


@asynccontextmanager
async def _app_lifespan(_: FastAPI):
    load_dotenv()
    yield


app = FastAPI(title="Requirement Review V2 API", version="2.0", lifespan=_app_lifespan)
_jobs: dict[str, JobRecord] = {}
_jobs_lock = asyncio.Lock()


def _env_disabled(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in _FALSE_VALUES


def _env_int(name: str, *, default: int, minimum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return max(minimum, int(raw.strip()))
    except ValueError:
        return default


def _security_settings() -> ApiSecuritySettings:
    return ApiSecuritySettings(
        auth_disabled=_env_disabled(_API_AUTH_DISABLED_ENV, default=True),
        api_key=str(os.getenv(_API_KEY_ENV, "") or "").strip(),
        bearer_token=str(os.getenv(_API_BEARER_TOKEN_ENV, "") or "").strip(),
        rate_limit_disabled=_env_disabled(_API_RATE_LIMIT_DISABLED_ENV, default=True),
        rate_limit_max_requests=_env_int(_API_RATE_LIMIT_MAX_REQUESTS_ENV, default=5, minimum=1),
        rate_limit_window_sec=_env_int(_API_RATE_LIMIT_WINDOW_SEC_ENV, default=60, minimum=1),
    )


def _controlled_error_response(
    status_code: int,
    *,
    code: str,
    message: str,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    detail = {"code": code, "message": message}
    if extra:
        detail.update(extra)
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


def _extract_bearer_token(request: Request) -> str:
    authorization = str(request.headers.get("authorization", "") or "").strip()
    if not authorization:
        return ""
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return ""
    return token.strip()


def _authenticate_request(request: Request, settings: ApiSecuritySettings) -> JSONResponse | None:
    if settings.auth_disabled:
        return None
    if not settings.api_key and not settings.bearer_token:
        return _controlled_error_response(
            503,
            code="api_auth_not_configured",
            message=(
                "API authentication is enabled but no credentials were configured. "
                f"Set {_API_KEY_ENV} or {_API_BEARER_TOKEN_ENV}, or opt out with {_API_AUTH_DISABLED_ENV}=true."
            ),
        )

    provided_api_key = str(request.headers.get("x-api-key", "") or "").strip()
    provided_bearer = _extract_bearer_token(request)
    if settings.api_key and provided_api_key == settings.api_key:
        return None
    if settings.bearer_token and provided_bearer == settings.bearer_token:
        return None

    if not provided_api_key and not provided_bearer:
        return _controlled_error_response(
            401,
            code="authentication_required",
            message="Provide a valid X-API-Key header or Authorization: Bearer token.",
        )

    return _controlled_error_response(
        401,
        code="invalid_api_credentials",
        message="The provided API credentials are invalid.",
    )


def _rate_limit_identity(request: Request) -> str:
    provided_api_key = str(request.headers.get("x-api-key", "") or "").strip()
    if provided_api_key:
        return f"api-key:{provided_api_key}"
    provided_bearer = _extract_bearer_token(request)
    if provided_bearer:
        return f"bearer:{provided_bearer}"
    client_host = request.client.host if request.client is not None else "unknown"
    return f"ip:{client_host}"


def _enforce_submission_rate_limit(request: Request, settings: ApiSecuritySettings) -> JSONResponse | None:
    if request.method.upper() != "POST" or request.url.path != "/api/review":
        return None
    if settings.rate_limit_disabled:
        return None

    identity = _rate_limit_identity(request)
    now = time.monotonic()
    with _submission_rate_limit_lock:
        requests = _submission_rate_limits[identity]
        while requests and now - requests[0] >= settings.rate_limit_window_sec:
            requests.popleft()
        if len(requests) >= settings.rate_limit_max_requests:
            retry_after = max(1, int(settings.rate_limit_window_sec - (now - requests[0])) + 1)
            return _controlled_error_response(
                429,
                code="rate_limit_exceeded",
                message="Review submission rate limit exceeded. Retry later.",
                extra={
                    "limit": settings.rate_limit_max_requests,
                    "window_sec": settings.rate_limit_window_sec,
                    "retry_after_sec": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )
        requests.append(now)
    return None


def _reset_submission_rate_limits() -> None:
    with _submission_rate_limit_lock:
        _submission_rate_limits.clear()


@app.middleware("http")
async def _api_security_middleware(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    settings = _security_settings()
    auth_error = _authenticate_request(request, settings)
    if auth_error is not None:
        return auth_error

    rate_limit_error = _enforce_submission_rate_limit(request, settings)
    if rate_limit_error is not None:
        return rate_limit_error

    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def _handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return _controlled_error_response(
        422,
        code="request_validation_error",
        message="Request validation failed.",
        extra={"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    return _controlled_error_response(
        500,
        code="internal_server_error",
        message=f"The server could not process the request: {type(exc).__name__}.",
    )


def _resolve_review_inputs(payload: ReviewCreateRequest) -> dict[str, str | None]:
    if payload.source and payload.source.strip():
        return {"prd_text": None, "prd_path": None, "source": payload.source.strip(), "mode": payload.mode}

    if payload.prd_text:
        return {"prd_text": payload.prd_text, "prd_path": None, "source": None, "mode": payload.mode}

    if not payload.prd_path:
        raise HTTPException(status_code=400, detail="Missing prd_path")

    prd_file = Path(payload.prd_path).expanduser()
    if not prd_file.is_absolute():
        prd_file = Path.cwd() / prd_file
    if not prd_file.exists() or not prd_file.is_file():
        raise HTTPException(status_code=404, detail=f"PRD file not found: {prd_file}")
    return {"prd_text": None, "prd_path": str(prd_file), "source": None, "mode": payload.mode}


def _resolve_runtime_llm_options(payload: ReviewCreateRequest) -> dict[str, Any]:
    options: dict[str, Any] = {}
    for key in ("fast_llm", "smart_llm", "strategic_llm", "temperature", "reasoning_effort", "llm_kwargs"):
        value = getattr(payload, key)
        if value is not None:
            options[key] = value
    return options


def _apply_progress_event(job: JobRecord, event: str, node_name: str, state: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    node = job.node_progress.setdefault(node_name, {"status": "pending", "runs": 0})
    if event == "start":
        job.current_node = node_name
        node["status"] = "running"
        node["runs"] = int(node.get("runs", 0) or 0) + 1
        node["last_start"] = now
    elif event == "end":
        trace = state.get("trace", {}) if isinstance(state, dict) else {}
        node_status = "completed"
        if isinstance(trace, dict):
            trace_status = trace.get(node_name, {}).get("status")
            if isinstance(trace_status, str) and trace_status:
                node_status = _trace_status_to_node_status(trace_status)
        node["status"] = node_status
        node["last_end"] = now
    job.updated_at = now
    _persist_job_snapshot(job)


def _read_trace_progress(run_dir: Path) -> dict[str, Any] | None:
    trace_path = run_dir / "run_trace.json"
    if not trace_path.exists():
        return None
    try:
        trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(trace_data, dict):
        return None

    observed_nodes = {
        name: payload
        for name, payload in trace_data.items()
        if isinstance(payload, dict) and any(key in payload for key in ("status", "start", "end"))
    }
    if not observed_nodes:
        return None

    nodes = {name: {"status": "pending", "runs": 0} for name in _ordered_node_names(observed_nodes)}
    for node_name in _ordered_node_names(observed_nodes):
        node_trace = trace_data.get(node_name)
        if not isinstance(node_trace, dict):
            continue
        status = node_trace.get("status", "ok")
        nodes[node_name] = {
            "status": _trace_status_to_node_status(status),
            "runs": 1,
            "last_start": node_trace.get("start"),
            "last_end": node_trace.get("end"),
        }
    return nodes


def _progress_snapshot_path(run_dir: Path) -> Path:
    return run_dir / RUN_PROGRESS_FILENAME


def _ordered_nodes_payload(nodes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(nodes, dict):
        return {}

    ordered: dict[str, dict[str, Any]] = {}
    for node_name in _ordered_node_names(nodes):
        node_payload = nodes.get(node_name)
        if isinstance(node_payload, dict):
            ordered[node_name] = dict(node_payload)
        else:
            ordered[node_name] = {"status": "pending", "runs": 0}
    return ordered


def _trace_status_to_node_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", "ok", "success", "completed", "partial_success", "skipped"}:
        return "completed"
    if normalized == "running":
        return "running"
    return "failed"


def _node_progress_weight(value: Any) -> float:
    normalized = str(value or "").strip().lower()
    if normalized in {"completed", "failed"}:
        return 1.0
    if normalized == "running":
        return 0.5
    return 0.0


def _progress_percent_from_nodes(nodes: dict[str, Any] | None, *, status: str) -> int:
    normalized_nodes = nodes if isinstance(nodes, dict) else {}
    completed_weight = sum(
        _node_progress_weight(normalized_nodes.get(node_name, {}).get("status"))
        for node_name in PRIMARY_NODES
    )
    percent = int((completed_weight / len(PRIMARY_NODES)) * 100) if PRIMARY_NODES else 0
    if status in {"queued", "running"}:
        return min(percent, 99)
    if status == "completed":
        return 100
    return percent


def _terminal_sse_payload(run_id: str, status: str, timestamp: str, *, error: str = "") -> dict[str, Any]:
    payload = {
        "node": "run",
        "status": str(status or "").strip(),
        "timestamp": str(timestamp or "").strip() or datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "terminal": True,
    }
    if error:
        payload["error"] = error
    return payload


def _terminal_payload_for_job(job: JobRecord) -> dict[str, Any] | None:
    if job.status not in {"completed", "failed"}:
        return None
    return _terminal_sse_payload(job.run_id, job.status, job.updated_at, error=job.error)


def _terminal_payload_for_run_dir(run_id: str, run_dir: Path) -> dict[str, Any] | None:
    persisted = _persisted_status_payload(run_id, run_dir)
    status = str(persisted.get("status", "") or "").strip()
    if status not in {"completed", "failed"}:
        return None
    progress = persisted.get("progress", {}) if isinstance(persisted.get("progress"), dict) else {}
    error = str(progress.get("error", "") or "")
    return _terminal_sse_payload(run_id, status, str(persisted.get("updated_at", "") or ""), error=error)


def _job_status_payload(job: JobRecord) -> dict[str, Any]:
    payload = {
        "run_id": job.run_id,
        "status": job.status,
        "progress": job.as_progress_payload(),
        "report_paths": dict(job.report_paths),
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }
    if job.status == "failed" and job.error_code:
        payload["error"] = {"code": job.error_code, "message": job.error}
    elif job.status == "failed" and job.error:
        payload["error"] = {"code": "run_error", "message": job.error}
    return payload


def _persist_job_snapshot(job: JobRecord) -> None:
    job.run_dir.mkdir(parents=True, exist_ok=True)
    _progress_snapshot_path(job.run_dir).write_text(
        json.dumps(_job_status_payload(job), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_progress_snapshot(run_dir: Path) -> dict[str, Any] | None:
    snapshot_path = _progress_snapshot_path(run_dir)
    if not snapshot_path.exists():
        return None
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    progress = dict(payload.get("progress", {}) or {}) if isinstance(payload.get("progress"), dict) else {}
    nodes = _ordered_nodes_payload(progress.get("nodes"))
    progress["nodes"] = nodes
    progress["percent"] = _progress_percent_from_nodes(nodes, status=str(payload.get("status", "running") or "running"))
    progress.setdefault("current_node", "")
    progress.setdefault("updated_at", str(payload.get("updated_at", "") or ""))
    progress.setdefault("error", "")
    payload["progress"] = progress
    return payload


def _merge_trace_nodes(progress_nodes: dict[str, Any] | None, trace_nodes: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    if isinstance(progress_nodes, dict):
        for node_name, node_payload in progress_nodes.items():
            if isinstance(node_payload, dict):
                merged[node_name] = dict(node_payload)
    if isinstance(trace_nodes, dict):
        for node_name, node_payload in trace_nodes.items():
            if not isinstance(node_payload, dict):
                continue
            current = dict(merged.get(node_name, {}))
            trace_status = str(node_payload.get("status", "pending") or "pending")
            current_status = str(current.get("status", "pending") or "pending")
            if current_status in {"pending", "running"} and trace_status in {"completed", "failed"}:
                current["status"] = trace_status
            else:
                current.setdefault("status", trace_status)
            current["runs"] = max(int(current.get("runs", 0) or 0), int(node_payload.get("runs", 0) or 0))
            if node_payload.get("last_start"):
                current["last_start"] = node_payload.get("last_start")
            else:
                current.setdefault("last_start", "")
            if node_payload.get("last_end"):
                current["last_end"] = node_payload.get("last_end")
            else:
                current.setdefault("last_end", "")
            merged[node_name] = current
    return _ordered_nodes_payload(merged)


def _inactive_run_message(run_id: str) -> str:
    return (
        f"Run {run_id} is no longer active. The backend process was restarted or exited before the review finished."
    )


def _persisted_status_payload(run_id: str, run_dir: Path) -> dict[str, Any]:
    report_md = run_dir / "report.md"
    report_json = run_dir / "report.json"
    run_trace = run_dir / "run_trace.json"
    completed = report_md.exists() and report_json.exists()

    created_dt = _run_id_to_datetime(run_id)
    default_created_at = created_dt.isoformat() if created_dt else _timestamp_to_iso(run_dir.stat().st_ctime)
    default_updated_at = _timestamp_to_iso(_latest_run_timestamp(run_dir))

    payload = _read_progress_snapshot(run_dir) or {
        "run_id": run_id,
        "status": "completed" if completed else "failed",
        "created_at": default_created_at,
        "updated_at": default_updated_at,
        "progress": {
            "percent": 100 if completed else 0,
            "current_node": "",
            "nodes": {},
            "updated_at": default_updated_at,
            "error": "",
        },
        "report_paths": {},
    }

    progress = dict(payload.get("progress", {}) or {}) if isinstance(payload.get("progress"), dict) else {}
    trace_nodes = _read_trace_progress(run_dir) or {}
    merged_nodes = _merge_trace_nodes(progress.get("nodes"), trace_nodes)
    progress["nodes"] = merged_nodes

    created_at = str(payload.get("created_at", "") or default_created_at)
    updated_at = str(payload.get("updated_at", "") or progress.get("updated_at", "") or default_updated_at)

    payload["run_id"] = run_id
    payload["created_at"] = created_at
    payload["updated_at"] = updated_at

    report_paths = dict(payload.get("report_paths", {}) or {}) if isinstance(payload.get("report_paths"), dict) else {}
    report_paths.setdefault("report_md", str(report_md))
    report_paths.setdefault("report_json", str(report_json))
    report_paths.setdefault("run_trace", str(run_trace))
    payload["report_paths"] = report_paths

    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else None
    status = str(payload.get("status", "") or ("completed" if completed else "failed")).strip().lower()

    if completed:
        payload["status"] = "completed"
        progress["percent"] = 100
        progress["current_node"] = ""
        progress["error"] = ""
        payload.pop("error", None)
    else:
        message = str(progress.get("error", "") or "")
        if error_payload and error_payload.get("message"):
            message = message or str(error_payload.get("message", "") or "")
        if status in {"queued", "running"}:
            message = message or _inactive_run_message(run_id)
            payload["status"] = "failed"
            payload["error"] = {"code": "run_interrupted", "message": message}
            progress["error"] = message
        elif status == "failed":
            message = message or _inactive_run_message(run_id)
            code = str(error_payload.get("code", "") or "run_failed") if error_payload else "run_failed"
            payload["error"] = {"code": code, "message": message}
            progress["error"] = message
        progress["percent"] = _progress_percent_from_nodes(progress["nodes"], status=str(payload.get("status", "failed") or "failed"))

    progress.setdefault("current_node", "")
    progress["updated_at"] = updated_at
    payload["progress"] = progress
    return payload


def _result_unavailable_detail(run_id: str, job: JobRecord | None) -> dict[str, Any]:
    if job is not None:
        status = job.status
        if status in {"queued", "running"}:
            detail = {
                "code": "result_not_ready",
                "message": f"report.json not ready for run_id={run_id}",
                "run_id": run_id,
                "status": status,
            }
        else:
            detail = {
                "code": job.error_code if job.error_code else "result_unavailable",
                "message": job.error if job.error else f"review result unavailable for run_id={run_id}",
                "run_id": run_id,
                "status": status,
            }
        detail["progress"] = job.as_progress_payload()
        if job.error_code:
            detail["error"] = {"code": job.error_code, "message": job.error}
        return detail

    persisted = _persisted_status_payload(run_id, OUTPUTS_ROOT / run_id)
    persisted_error = persisted.get("error") if isinstance(persisted.get("error"), dict) else {}
    status = str(persisted.get("status", "failed") or "failed")
    if status in {"queued", "running"}:
        detail = {
            "code": "result_not_ready",
            "message": f"report.json not ready for run_id={run_id}",
            "run_id": run_id,
            "status": status,
        }
    else:
        detail = {
            "code": str(persisted_error.get("code", "") or "result_unavailable"),
            "message": str(persisted_error.get("message", "") or persisted.get("progress", {}).get("error", "") or f"review result unavailable for run_id={run_id}"),
            "run_id": run_id,
            "status": status,
        }
    if isinstance(persisted.get("progress"), dict):
        detail["progress"] = persisted["progress"]
    if persisted_error:
        detail["error"] = persisted_error
    return detail


async def _run_job(
    job: JobRecord,
    *,
    prd_text: str | None = None,
    prd_path: str | None = None,
    source: str | None = None,
    mode: str | None = None,
    llm_options: dict[str, Any] | None = None,
) -> None:
    job.status = "running"
    job.error = ""
    job.error_code = ""
    job.updated_at = datetime.now(timezone.utc).isoformat()
    _persist_job_snapshot(job)
    try:
        summary = await review_prd_text_async(
            prd_text=prd_text,
            prd_path=prd_path,
            source=source,
            run_id=job.run_id,
            config_overrides={
                "outputs_root": OUTPUTS_ROOT,
                "progress_hook": lambda event, node, state: _apply_progress_event(job, event, node, state),
                **({"mode": mode} if isinstance(mode, str) and mode.strip() else {}),
                **(dict(llm_options) if isinstance(llm_options, dict) else {}),
            },
        )
        job.status = summary.status
        job.current_node = ""
        job.report_paths = summary.to_report_paths()
    except Exception as exc:
        job.status = "failed"
        classified_error = classify_review_input_error(exc)
        job.error_code = classified_error.code if classified_error is not None else "INTERNAL_ERROR"
        job.error = classified_error.message if classified_error is not None else str(exc)
        job.current_node = ""
    finally:
        job.updated_at = datetime.now(timezone.utc).isoformat()
        _persist_job_snapshot(job)
        ProgressBroadcaster().publish(
            job.run_id,
            "run_status",
            _terminal_sse_payload(job.run_id, job.status, job.updated_at, error=job.error),
        )


@app.get("/api/templates")
def list_templates_endpoint(version: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        templates = list(list_template_records(version=version))
    except TemplateRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"count": len(templates), "templates": templates}


@app.get("/api/templates/{template_type}")
def list_templates_by_type_endpoint(template_type: str, version: str | None = Query(default=None)) -> dict[str, Any]:
    try:
        templates = list(list_template_records(template_type=template_type, version=version))
    except TemplateRegistryError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"template_type": template_type, "count": len(templates), "templates": templates}


@app.get("/api/audit")
def list_audit_events_endpoint(
    run_id: str | None = Query(default=None),
    bundle_id: str | None = Query(default=None),
    task_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    events = query_audit_events(
        OUTPUTS_ROOT,
        run_id=run_id,
        bundle_id=bundle_id,
        task_id=task_id,
        event_type=event_type,
        status=status,
    )
    return {
        "count": len(events),
        "events": events,
        "filters": {
            "run_id": run_id,
            "bundle_id": bundle_id,
            "task_id": task_id,
            "event_type": event_type,
            "status": status,
        },
    }


@app.get("/api/runs")
async def list_runs() -> dict[str, Any]:
    async with _jobs_lock:
        jobs = dict(_jobs)

    if not OUTPUTS_ROOT.exists() or not OUTPUTS_ROOT.is_dir():
        return {"count": 0, "runs": []}

    runs: list[tuple[float, str, dict[str, Any]]] = []
    for run_dir in OUTPUTS_ROOT.iterdir():
        if not run_dir.is_dir() or not RUN_ID_PATTERN.fullmatch(run_dir.name):
            continue
        job = jobs.get(run_dir.name)
        runs.append((_run_sort_timestamp(run_dir, job), run_dir.name, _build_run_list_entry(run_dir, job)))

    runs.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return {"count": len(runs), "runs": [item[2] for item in runs]}


@app.post("/api/review")
async def create_review(payload: ReviewCreateRequest) -> dict[str, str]:
    review_inputs = _resolve_review_inputs(payload)
    llm_options = _resolve_runtime_llm_options(payload)
    run_id = make_run_id()
    run_dir = OUTPUTS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    job = JobRecord(run_id=run_id, run_dir=run_dir)
    _persist_job_snapshot(job)
    task = asyncio.create_task(_run_job(job, **review_inputs, llm_options=llm_options))
    job.task = task

    async with _jobs_lock:
        _jobs[run_id] = job
    return {"run_id": run_id}


@app.get("/api/review/{run_id}")
async def get_review_status(run_id: str) -> dict[str, Any]:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    if job:
        return _job_status_payload(job)

    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    return _persisted_status_payload(run_id, run_dir)


@app.get("/api/review/{run_id}/progress/stream")
async def stream_review_progress(run_id: str) -> StreamingResponse:
    async with _jobs_lock:
        job = _jobs.get(run_id)

    run_dir = OUTPUTS_ROOT / run_id
    if job is None and not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    broadcaster = ProgressBroadcaster()

    async def event_stream():
        terminal_payload = _terminal_payload_for_job(job) if job is not None else None
        if terminal_payload is None and job is None and run_dir.exists():
            terminal_payload = _terminal_payload_for_run_dir(run_id, run_dir)
        if terminal_payload is not None:
            yield broadcaster.encode_event(terminal_payload)
            return

        async for event in broadcaster.subscribe(run_id):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/review/{run_id}/clarification")
async def submit_review_clarification(run_id: str, payload: ClarificationAnswerRequest) -> dict[str, Any]:
    try:
        return answer_review_clarification(
            run_id=run_id,
            answers=[item.model_dump(mode="python") for item in payload.answers],
            outputs_root=OUTPUTS_ROOT,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "clarification_unavailable", "message": str(exc), "run_id": run_id},
        ) from exc
    except TypeError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_clarification_payload", "message": str(exc), "run_id": run_id},
        ) from exc


@app.get("/api/review/{run_id}/result")
async def get_review_result(run_id: str) -> dict[str, Any]:
    try:
        return get_review_result_payload(run_id=run_id, outputs_root=OUTPUTS_ROOT)
    except ReviewRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ReviewResultNotReadyError as exc:
        async with _jobs_lock:
            job = _jobs.get(run_id)

        detail = _result_unavailable_detail(run_id, job)
        if detail.get("code") == "result_not_ready":
            detail["message"] = str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "invalid_report_content", "message": str(exc)},
        ) from exc


@app.get("/api/review/{run_id}/artifacts/{artifact_key}")
async def get_review_artifact_preview(run_id: str, artifact_key: str) -> dict[str, Any]:
    try:
        return get_review_artifact_preview_payload(
            run_id=run_id,
            artifact_key=artifact_key,
            outputs_root=OUTPUTS_ROOT,
        )
    except ReviewRunNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "run_not_found", "message": str(exc)},
        ) from exc
    except ReviewResultNotReadyError as exc:
        async with _jobs_lock:
            job = _jobs.get(run_id)

        detail = _result_unavailable_detail(run_id, job)
        if detail.get("code") == "result_not_ready":
            detail["message"] = str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    except ReviewArtifactNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "artifact_not_found", "message": str(exc), "run_id": run_id},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail={"code": "invalid_artifact_preview", "message": str(exc), "run_id": run_id},
        ) from exc


@app.get("/api/report/{run_id}")
async def get_report(run_id: str, format: Literal["md", "json"] = Query(default="md")) -> FileResponse:
    run_dir = OUTPUTS_ROOT / run_id
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail=f"run_id not found: {run_id}")

    filename = "report.md" if format == "md" else "report.json"
    path = run_dir / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} not found for run_id={run_id}")

    media_type = "text/markdown; charset=utf-8" if format == "md" else "application/json"
    return FileResponse(path=str(path), media_type=media_type, filename=filename)


if FRONTEND_DIST_ROOT.exists():
    # Mount the built SPA after registering API routes so `/api/*` keeps priority.
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_ROOT, html=True), name="frontend")




