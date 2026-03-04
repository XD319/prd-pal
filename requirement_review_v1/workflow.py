"""Requirement-review workflow with conditional risk-based clarification loop.

Main path:
parser  →  planner  →  risk  →  reviewer  →  route_decider  →  reporter  →  END

Loop path (when quality risk stays high):
route_decider  →  clarify(parser_prompt=v1.1-clarify)  →  planner  →  risk  →  reviewer
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .agents import (
    planner_agent,
    parser_agent,
    risk_agent,
    reporter_agent,
    reviewer_agent,
)
from .state import ReviewState

_MAX_REVISION_ROUNDS = 2
_HIGH_RISK_THRESHOLD = 0.4


async def _clarify_node(state: ReviewState) -> ReviewState:
    """Reuse parser agent with a stricter clarification prompt version."""
    clarify_state: ReviewState = dict(state)
    clarify_state["parser_prompt_version"] = "v1.1-clarify"
    return await parser_agent.run(clarify_state)


def _route_decider_node(state: ReviewState) -> ReviewState:
    """Decide whether to loop for clarification or finish with reporter."""
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
        reason = (
            f"finish: high_risk_ratio={ratio:.3f} <= {_HIGH_RISK_THRESHOLD:.2f}"
        )
    else:
        next_round = revision_round
        reason = (
            f"finish: revision_round={revision_round} reached limit {_MAX_REVISION_ROUNDS}"
        )

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

    update: ReviewState = {
        "revision_round": next_round if should_loop else revision_round,
        "routing_reason": reason,
        "parser_prompt_version": "v1.1",
        "trace": trace,
    }
    return update


def _route_next(state: ReviewState) -> str:
    """Router for conditional edge branching."""
    routing_reason = str(state.get("routing_reason", "") or "")
    if routing_reason.startswith("loop:"):
        return "clarify"
    return "reporter"


def build_review_graph():
    """Build and compile the review graph with conditional loop routing.

    Returns a compiled ``CompiledGraph`` ready for ``await graph.ainvoke()``.
    """
    workflow = StateGraph(ReviewState)

    workflow.add_node("parser", parser_agent.run)
    workflow.add_node("clarify", _clarify_node)
    workflow.add_node("planner", planner_agent.run)
    workflow.add_node("risk", risk_agent.run)
    workflow.add_node("reviewer", reviewer_agent.run)
    workflow.add_node("route_decider", _route_decider_node)
    workflow.add_node("reporter", reporter_agent.run)

    workflow.set_entry_point("parser")
    workflow.add_edge("parser", "planner")
    workflow.add_edge("clarify", "planner")
    workflow.add_edge("planner", "risk")
    workflow.add_edge("risk", "reviewer")
    workflow.add_edge("reviewer", "route_decider")
    workflow.add_conditional_edges(
        "route_decider",
        _route_next,
        {"clarify": "clarify", "reporter": "reporter"},
    )
    workflow.add_edge("reporter", END)

    return workflow.compile()
