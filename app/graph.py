from langgraph.graph import END, StateGraph

from app.nodes import (
    clarification_node,
    coverage_check_node,
    final_decision_node,
    fraud_check_node,
    intake_node,
    pii_redact_node,
    route_after_intake,
)
from app.state import ClaimState


def build_graph():
    workflow = StateGraph(ClaimState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("clarification_needed", clarification_node)
    workflow.add_node("coverage_check", coverage_check_node)
    workflow.add_node("fraud_check", fraud_check_node)
    workflow.add_node("pii_redact", pii_redact_node)
    workflow.add_node("final_decision", final_decision_node)

    workflow.set_entry_point("pii_redact")
    workflow.add_edge("pii_redact", "intake")

    workflow.add_conditional_edges(
        "intake",
        route_after_intake,
        {
            "clarification_needed": "clarification_needed",
            "coverage_check": "coverage_check",
            "fraud_check": "fraud_check",
        },
    )

    workflow.add_edge("clarification_needed", END)
    workflow.add_edge("coverage_check", "final_decision")
    workflow.add_edge("fraud_check", "final_decision")
    workflow.add_edge("final_decision", END)

    return workflow.compile()