"""
Tests for route_after_intake — the function whose return type (a single
string vs. a list) is the entire fan-out mechanism in the graph.

Note: this imports app.nodes, which builds the vector + keyword retrieval
stores at module load time (see Phase 2 decisions). That means this test
file pays that startup cost too, even though route_after_intake itself has
zero dependency on retrieval. Cheap now that HF_HUB_OFFLINE=1 is set — a
couple seconds, not the ~9s it used to be — but worth knowing why a "pure
logic" test isn't instant.
"""
from app.nodes import route_after_intake


def test_routes_to_clarification_when_fields_missing():
    state = {"missing_fields": ["incident_date"]}
    assert route_after_intake(state) == "clarification_needed"


def test_routes_to_clarification_with_multiple_missing_fields():
    state = {"missing_fields": ["incident_date", "policy_number"]}
    assert route_after_intake(state) == "clarification_needed"


def test_routes_to_parallel_branch_when_nothing_missing():
    state = {"missing_fields": []}
    result = route_after_intake(state)
    assert set(result) == {"coverage_check", "fraud_check"}


def test_parallel_branch_returns_a_list_not_a_string():
    """The fan-out mechanism depends entirely on this being a list, not a
    string — LangGraph treats the two return shapes completely differently."""
    state = {"missing_fields": []}
    result = route_after_intake(state)
    assert isinstance(result, list)