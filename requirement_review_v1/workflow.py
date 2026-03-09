"""Requirement-review workflow with parser-driven parallel planner/risk fan-out."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from langgraph.graph import END, StateGraph

from .agents import delivery_planning_agent, planner_agent, parser_agent, reporter_agent, reviewer_agent
from .review import decide_review_mode, run_parallel_review_async
from .state import ReviewState, plan_from_state
from .subflows.risk_analysis import run_risk_analysis_from_review_state
from .templates.registry import CLARIFY_PARSER_REVIEW_PROMPT, PARSER_REVIEW_PROMPT
from .utils.trace import trace_start

_MAX_REVISION_ROUNDS = 2
_HIGH_RISK_THRESHOLD = 0.4
_PARALLEL_TRACE_KEY = "planner_risk_parallel"
_PARALLEL_REVIEW_META_KEY = "parallel-review_meta"
_ALLOWED_REVIEW_MODES = {"single_review", "parallel_review"}
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
    clarify_state["parser_prompt_version"] = CLARIFY_PARSER_REVIEW_PROMPT.version
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
        "parser_prompt_version": PARSER_REVIEW_PROMPT.version,
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


async def _reviewer_node(state: ReviewState) -> ReviewState:
    override = str(state.get("review_mode_override", "") or "").strip().lower()
    normalized_override = override if override in _ALLOWED_REVIEW_MODES else ""
    decision = decide_review_mode(str(state.get("requirement_doc", "") or ""))
    selected_mode = normalized_override or decision.mode

    if selected_mode == "parallel_review":
        return await _run_parallel_reviewer(state, decision=decision, override=normalized_override)
    return await _run_single_reviewer(state, decision=decision, override=normalized_override)


async def _run_single_reviewer(state: ReviewState, *, decision: Any, override: str) -> ReviewState:
    update = await reviewer_agent.run(state)
    trace: dict[str, Any] = dict(update.get("trace", state.get("trace", {})) or {})
    review_results = list(update.get("review_results", []) or [])
    review_open_questions = _derive_single_review_open_questions(review_results)
    review_risk_items = _derive_single_review_risk_items(review_results)

    reviewer_trace = trace.get("reviewer") if isinstance(trace.get("reviewer"), dict) else {}
    meta = {
        "default_mode": decision.mode,
        "selected_mode": "single_review",
        "review_mode_override": override,
        "parallel_triggered": False,
        "reviewer_strategy": "single_reviewer",
        "review_mode": "single_review",
        "gating_decision": asdict(decision),
        "reviewer_count": 1,
        "reviewers_completed": ["single_reviewer"],
        "reviewers_failed": [],
        "finding_count": len(review_results),
        "open_questions_count": len(review_open_questions),
        "risk_items_count": len(review_risk_items),
        "input_token_estimate": _estimate_tokens(int(reviewer_trace.get("input_chars", 0) or 0)),
        "output_token_estimate": _estimate_tokens(int(reviewer_trace.get("output_chars", 0) or 0)),
        "duration_ms": int(reviewer_trace.get("duration_ms", 0) or 0),
    }
    trace[_PARALLEL_REVIEW_META_KEY] = meta
    update["trace"] = trace
    update["review_mode"] = "single_review"
    update["review_open_questions"] = review_open_questions
    update["review_risk_items"] = review_risk_items
    update["parallel_review_meta"] = meta
    return update


async def _run_parallel_reviewer(state: ReviewState, *, decision: Any, override: str) -> ReviewState:
    requirement_doc = str(state.get("requirement_doc", "") or "")
    run_dir = str(state.get("run_dir", "") or "")
    trace: dict[str, Any] = dict(state.get("trace", {}))
    span = trace_start("reviewer", model="none", input_chars=len(requirement_doc))
    span.set_attr("review_mode", "parallel_review")
    span.set_attr("reviewer_strategy", "asyncio.gather")
    started = perf_counter()

    parallel_result = await run_parallel_review_async(requirement_doc, run_dir)
    aggregated = parallel_result.aggregated
    aggregated_meta = dict(aggregated.get("meta", {}) or {})
    selected_mode = str(aggregated_meta.get("review_mode", "parallel_review") or "parallel_review")
    reviewers_completed = list(aggregated_meta.get("reviewers_completed", []) or [])
    reviewers_failed = list(aggregated_meta.get("reviewers_failed", []) or [])
    review_results = _build_parallel_review_results(state, aggregated)
    plan_review = _build_parallel_plan_review(aggregated)
    review_open_questions = list(aggregated.get("open_questions", []) or [])
    review_risk_items = list(aggregated.get("risk_items", []) or [])
    findings = list(aggregated.get("findings", []) or [])

    output_chars = len(json.dumps(aggregated, ensure_ascii=False))
    trace["reviewer"] = span.end(status="ok", output_chars=output_chars)
    meta = {
        "default_mode": decision.mode,
        "selected_mode": selected_mode,
        "review_mode_override": override,
        "parallel_triggered": True,
        "reviewer_strategy": "asyncio.gather",
        "review_mode": selected_mode,
        "gating_decision": asdict(decision),
        "reviewer_count": int(aggregated.get("reviewer_count", len(reviewers_completed)) or len(reviewers_completed)),
        "reviewers_completed": reviewers_completed,
        "reviewers_failed": reviewers_failed,
        "finding_count": len(findings),
        "open_questions_count": len(review_open_questions),
        "risk_items_count": len(review_risk_items),
        "input_token_estimate": _estimate_tokens(len(requirement_doc)),
        "output_token_estimate": _estimate_tokens(output_chars),
        "duration_ms": round((perf_counter() - started) * 1000),
        "artifact_paths": dict((aggregated.get("artifacts") or {})),
    }
    trace[_PARALLEL_REVIEW_META_KEY] = meta

    return {
        "review_results": review_results,
        "plan_review": plan_review,
        "high_risk_ratio": _compute_parallel_high_risk_ratio(review_results),
        "trace": trace,
        "review_mode": selected_mode,
        "parallel_review": aggregated,
        "review_open_questions": review_open_questions,
        "review_risk_items": review_risk_items,
        "parallel_review_meta": meta,
    }


def _build_parallel_review_results(state: ReviewState, aggregated: dict[str, Any]) -> list[dict[str, Any]]:
    parsed_items = list(state.get("parsed_items", []) or [])
    findings = list(aggregated.get("findings", []) or [])
    open_questions = list(aggregated.get("open_questions", []) or [])
    risk_items = list(aggregated.get("risk_items", []) or [])

    has_scope_gap = any(
        str(item.get("category", "")).lower() in {"scope", "acceptance"} and str(item.get("severity", "")).lower() == "high"
        for item in findings
    )
    has_testability_gap = any(
        str(item.get("category", "")).lower() == "testability" and str(item.get("severity", "")).lower() == "high"
        for item in findings
    )
    issue_lines = [
        f"{item.get('title', 'Finding')}: {item.get('description', item.get('detail', ''))}".strip()
        for item in findings[:2]
        if str(item.get("title", "") or "").strip()
    ]
    question_lines = [str(item.get("question", "") or "").strip() for item in open_questions[:2] if str(item.get("question", "") or "").strip()]
    suggestions = "; ".join(
        str(item.get("mitigation", "") or item.get("detail", "")).strip()
        for item in risk_items[:2]
        if str(item.get("mitigation", "") or item.get("detail", "")).strip()
    )

    review_results: list[dict[str, Any]] = []
    for item in parsed_items:
        acceptance_criteria = list(item.get("acceptance_criteria", []) or [])
        is_testable = bool(acceptance_criteria) and not has_testability_gap
        is_clear = not has_scope_gap
        is_ambiguous = has_scope_gap and not acceptance_criteria
        issues = issue_lines + (question_lines if is_ambiguous else [])
        review_results.append(
            {
                "id": item.get("id", "unknown"),
                "is_clear": is_clear,
                "is_testable": is_testable,
                "is_ambiguous": is_ambiguous,
                "issues": issues,
                "suggestions": suggestions,
            }
        )
    return review_results


def _build_parallel_plan_review(aggregated: dict[str, Any]) -> dict[str, str]:
    summaries = {
        str(item.get("reviewer", "") or "").strip().lower(): str(item.get("summary", "") or "").strip()
        for item in list(aggregated.get("reviewer_summaries", []) or [])
        if isinstance(item, dict)
    }
    return {
        "coverage": " ".join(part for part in (summaries.get("product", ""), summaries.get("security", "")) if part),
        "milestones": summaries.get("engineering", ""),
        "estimation": summaries.get("qa", ""),
    }


def _compute_parallel_high_risk_ratio(review_results: list[dict[str, Any]]) -> float:
    total = len(review_results)
    if total == 0:
        return 0.0
    high_count = 0
    for item in review_results:
        flags = sum(
            [
                not item.get("is_clear", True),
                not item.get("is_testable", True),
                item.get("is_ambiguous", False),
            ]
        )
        if flags >= 2:
            high_count += 1
    return high_count / total


def _derive_single_review_open_questions(review_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for item in review_results:
        issues = [str(issue).strip() for issue in list(item.get("issues", []) or []) if str(issue).strip()]
        if item.get("is_ambiguous") or issues:
            question = str(item.get("description") or item.get("id") or "Clarify requirement intent").strip()
            if not question:
                question = "Clarify requirement intent"
            questions.append({"question": question, "reviewers": ["single_reviewer"], "issues": issues})
    return questions


def _derive_single_review_risk_items(review_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in review_results:
        flags = sum(
            [
                not item.get("is_clear", True),
                not item.get("is_testable", True),
                item.get("is_ambiguous", False),
            ]
        )
        if flags == 0:
            continue
        severity = "high" if flags >= 2 else "medium"
        issues = [str(issue).strip() for issue in list(item.get("issues", []) or []) if str(issue).strip()]
        items.append(
            {
                "title": str(item.get("id", "Requirement review risk")),
                "detail": "; ".join(issues) or str(item.get("suggestions", "") or "Clarify the requirement before implementation."),
                "severity": severity,
                "category": "review_quality",
                "reviewers": ["single_reviewer"],
            }
        )
    return items


def _estimate_tokens(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, round(char_count / 4))


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
    workflow.add_node("reviewer", _build_async_node("reviewer", _reviewer_node, progress_hook))
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



