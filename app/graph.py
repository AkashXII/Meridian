from langgraph.graph import END, StateGraph

from app.nodes import (
    clarification_node,
    coverage_check_node,
    intake_node,
    route_after_intake,
)
from app.state import ClaimState


def build_graph():
    workflow = StateGraph(ClaimState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("clarification_needed", clarification_node)
    workflow.add_node("coverage_check", coverage_check_node)

    workflow.set_entry_point("intake")

    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "clarification_needed": "clarification_needed",
            "coverage_check": "coverage_check",
        },
    )

    workflow.add_edge("clarification_needed", END)
    workflow.add_edge("coverage_check", END)

    return workflow.compile()
