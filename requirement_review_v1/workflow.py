"""Requirement-review workflow with parser-driven parallel planner/risk fan-out."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from .agents import delivery_planning_agent, planner_agent, parser_agent, reporter_agent, reviewer_agent
from .state import ReviewState, plan_from_state
from .subflows.risk_analysis import run_risk_analysis_from_review_state

_MAX_REVISION_ROUNDS = 2
_HIGH_RISK_THRESHOLD = 0.4
_PARALLEL_TRACE_KEY = "planner_risk_parallel"
ProgressHook = Callable[[str, str, ReviewState], None]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


async def _clarify_node(state: ReviewState) -> ReviewState:
    clarify_state: ReviewState = dict(state)
    clarify_state["parser_prompt_version"] = "v1.1-clarify"
    return await parser_agent.run(clarify_state)


def _parallel_start_node(state: ReviewState) -> ReviewState:
    trace: dict[str, Any] = dict(state.get("trace", {}))
    existing = trace.get(_PARALLEL_TRACE_KEY, {})
    round_no = int(state.get("revision_round", 0) or 0)
    trace[_PARALLEL_TRACE_KEY] = {
        **(existing if isinstance(existing, dict) else {}),
        "start": _utc_now_iso(),
        "status": "running",
        "round": round_no,
        "branches": ["planner", "risk"],
        "fan_out": "parser->planner+risk",
    }
    return {"trace": trace}


def _review_join_node(state: ReviewState) -> ReviewState:
    trace: dict[str, Any] = dict(state.get("trace", {}))
    plan = plan_from_state(state)
    planner_span = trace.get("planner", {}) if isinstance(trace.get("planner"), dict) else {}
    risk_span = trace.get("risk", {}) if isinstance(trace.get("risk"), dict) else {}
    start_span = trace.get(_PARALLEL_TRACE_KEY, {}) if isinstance(trace.get(_PARALLEL_TRACE_KEY), dict) else {}

    planner_ready = isinstance(state.get("plan"), dict)
    risk_ready = isinstance(state.get("evidence"), dict)
    validation_errors: list[str] = []
    if not planner_ready:
        validation_errors.append("planner output missing state.plan")
    if not risk_ready:
        validation_errors.append("risk output missing state.evidence")

    planner_start = _parse_iso(planner_span.get("start"))
    planner_end = _parse_iso(planner_span.get("end"))
    risk_start = _parse_iso(risk_span.get("start"))
    risk_end = _parse_iso(risk_span.get("end"))
    parallel_start = _parse_iso(start_span.get("start")) or planner_start or risk_start
    parallel_end = max([dt for dt in (planner_end, risk_end) if dt is not None], default=None)

    planner_duration_ms = int(planner_span.get("duration_ms", 0) or 0)
    risk_duration_ms = int(risk_span.get("duration_ms", 0) or 0)
    sum_step_time_ms = planner_duration_ms + risk_duration_ms
    parallel_wall_time_ms = (
        int((parallel_end - parallel_start).total_seconds() * 1000)
        if parallel_start and parallel_end
        else 0
    )
    overlap_ms = (
        int((min(planner_end, risk_end) - max(planner_start, risk_start)).total_seconds() * 1000)
        if planner_start and planner_end and risk_start and risk_end
        else 0
    )
    overlap_ms = max(0, overlap_ms)
    saved_ms = max(0, sum_step_time_ms - parallel_wall_time_ms)
    speedup_ratio = round(sum_step_time_ms / parallel_wall_time_ms, 3) if parallel_wall_time_ms > 0 else 1.0

    trace[_PARALLEL_TRACE_KEY] = {
        **start_span,
        "end": parallel_end.isoformat() if parallel_end else _utc_now_iso(),
        "status": "ok" if not validation_errors else "error",
        "join_node": "review_join",
        "fan_in": "planner+risk->reviewer",
        "planner_ready": planner_ready,
        "risk_ready": risk_ready,
        "validation_errors": validation_errors,
        "parallel_wall_time_ms": parallel_wall_time_ms,
        "sum_step_time_ms": sum_step_time_ms,
        "overlap_ms": overlap_ms,
        "saved_ms": saved_ms,
        "speedup_ratio": speedup_ratio,
        "parallelized": True,
    }

    return {
        "tasks": plan.get("tasks", []),
        "milestones": plan.get("milestones", []),
        "dependencies": plan.get("dependencies", []),
        "estimation": plan.get("estimation", {}),
        "trace": trace,
    }


def _route_decider_node(state: ReviewState) -> ReviewState:
    trace: dict[str, Any] = dict(state.get("trace", {}))
    revision_round = int(state.get("revision_round", 0) or 0)
    ratio = float(state.get("high_risk_ratio", 0.0) or 0.0)

    should_loop = ratio > _HIGH_RISK_THRESHOLD and revision_round < _MAX_REVISION_ROUNDS
    if should_loop:
        next_round = revision_round + 1
        reason = (
            f"loop: high_risk_ratio={ratio:.3f} > {_HIGH_RISK_THRESHOLD:.2f} "
            f"and revision_round={revision_round} < {_MAX_REVISION_ROUNDS}"
        )
    elif ratio <= _HIGH_RISK_THRESHOLD:
        next_round = revision_round
        reason = f"finish: high_risk_ratio={ratio:.3f} <= {_HIGH_RISK_THRESHOLD:.2f}"
    else:
        next_round = revision_round
        reason = f"finish: revision_round={revision_round} reached limit {_MAX_REVISION_ROUNDS}"

    routing_event = {
        "round": next_round if should_loop else revision_round,
        "ratio": ratio,
        "reason": reason,
        "decision": "clarify" if should_loop else "reporter",
    }
    routing_rounds = list(trace.get("routing_rounds", []))
    routing_rounds.append(routing_event)
    trace["routing_rounds"] = routing_rounds
    trace["router"] = routing_event

    return {
        "revision_round": next_round if should_loop else revision_round,
        "routing_reason": reason,
        "parser_prompt_version": "v1.1",
        "trace": trace,
    }


def _route_next(state: ReviewState) -> str:
    routing_reason = str(state.get("routing_reason", "") or "")
    if routing_reason.startswith("loop:"):
        return "clarify"
    return "reporter"


def _build_async_node(
    node_name: str,
    node_fn: Callable[[ReviewState], Awaitable[ReviewState]],
    progress_hook: ProgressHook | None,
) -> Callable[[ReviewState], Awaitable[ReviewState]]:
    async def _runner(state: ReviewState) -> ReviewState:
        if progress_hook:
            progress_hook("start", node_name, state)
        update = await node_fn(state)
        if progress_hook:
            merged_state: ReviewState = dict(state)
            if isinstance(update, dict):
                merged_state.update(update)
            progress_hook("end", node_name, merged_state)
        return update

    return _runner


def _build_sync_node(
    node_name: str,
    node_fn: Callable[[ReviewState], ReviewState],
    progress_hook: ProgressHook | None,
) -> Callable[[ReviewState], ReviewState]:
    def _runner(state: ReviewState) -> ReviewState:
        if progress_hook:
            progress_hook("start", node_name, state)
        update = node_fn(state)
        if progress_hook:
            merged_state: ReviewState = dict(state)
            if isinstance(update, dict):
                merged_state.update(update)
            progress_hook("end", node_name, merged_state)
        return update

    return _runner


def build_review_graph(progress_hook: ProgressHook | None = None):
    """Build and compile the review graph with fan-out / fan-in parallelism."""

    workflow = StateGraph(ReviewState)

    workflow.add_node("parser", _build_async_node("parser", parser_agent.run, progress_hook))
    workflow.add_node("clarify", _build_async_node("clarify", _clarify_node, progress_hook))
    workflow.add_node("parallel_start", _build_sync_node("parallel_start", _parallel_start_node, progress_hook))
    workflow.add_node("planner", _build_async_node("planner", planner_agent.run, progress_hook))
    workflow.add_node("risk", _build_async_node("risk", run_risk_analysis_from_review_state, progress_hook))
    workflow.add_node("review_join", _build_sync_node("review_join", _review_join_node, progress_hook))
    workflow.add_node(
        "delivery_planning",
        _build_async_node("delivery_planning", delivery_planning_agent.run, progress_hook),
    )
    workflow.add_node("reviewer", _build_async_node("reviewer", reviewer_agent.run, progress_hook))
    workflow.add_node("route_decider", _build_sync_node("route_decider", _route_decider_node, progress_hook))
    workflow.add_node("reporter", _build_async_node("reporter", reporter_agent.run, progress_hook))

    workflow.set_entry_point("parser")
    workflow.add_edge("parser", "parallel_start")
    workflow.add_edge("clarify", "parallel_start")
    workflow.add_edge("parallel_start", "planner")
    workflow.add_edge("parallel_start", "risk")
    workflow.add_edge("planner", "review_join")
    workflow.add_edge("risk", "review_join")
    workflow.add_edge("review_join", "delivery_planning")
    workflow.add_edge("delivery_planning", "reviewer")
    workflow.add_edge("reviewer", "route_decider")
    workflow.add_conditional_edges("route_decider", _route_next, {"clarify": "clarify", "reporter": "reporter"})
    workflow.add_edge("reporter", END)

    return workflow.compile()
