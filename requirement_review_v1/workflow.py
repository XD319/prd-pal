"""Requirement-review workflow — a linear LangGraph pipeline.

parser  →  reviewer  →  reporter  →  END
"""

from langgraph.graph import END, StateGraph

from .agents import parser_agent, reviewer_agent, reporter_agent
from .state import ReviewState


def build_review_graph():
    """Build and compile the three-node review graph.

    Returns a compiled ``CompiledGraph`` ready for ``await graph.ainvoke()``.
    """
    workflow = StateGraph(ReviewState)

    workflow.add_node("parser", parser_agent.run)
    workflow.add_node("reviewer", reviewer_agent.run)
    workflow.add_node("reporter", reporter_agent.run)

    workflow.set_entry_point("parser")
    workflow.add_edge("parser", "reviewer")
    workflow.add_edge("reviewer", "reporter")
    workflow.add_edge("reporter", END)

    return workflow.compile()
