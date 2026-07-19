# Insurance Claims Platform — Phase 1: Skeleton

A minimal but real LangGraph workflow: extract structured fields from a raw
claim, route to either "needs clarification" or "coverage check" based on
what's missing, and produce a decision. No RAG, no guardrails, no MCP, no
observability yet — those come in later phases, layered onto this same
skeleton.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # then add your real GROQ_API_KEY
```

## Run

```bash
# Uses the first sample claim in data/sample_claims.json
python -m app.main

# Or pass your own claim text
python -m app.main "My laptop was stolen from my car on 2026-07-01, policy A-12345, claiming $1500"
```

Try all three sample claims — the second one is missing a clear incident
date on purpose, so you can see the `clarification_needed` branch fire.

## How it's wired

```
intake ──(route_after_intake)──> clarification_needed ──> END
      └─────────────────────────> coverage_check ──> END
```

- `app/state.py` — the shape of data flowing through the graph
- `app/models.py` — Pydantic schemas the LLM is forced to return
- `app/nodes.py` — the actual logic, one function per node
- `app/graph.py` — wires nodes together with LangGraph
- `app/llm.py` — single point of control for which model/provider is used

## Roadmap (not built yet)

- **Phase 2 — Hybrid RAG**: replace the hardcoded `POLICY_RULES` string in
  `nodes.py` with real retrieval (vector + BM25 + re-ranker) over a folder
  of policy documents.
- **Phase 3 — Multi-agent**: split `coverage_check_node` into a couple of
  specialist agents (e.g. coverage checker + fraud-risk flagger) coordinated
  by a router node.
- **Phase 4 — Guardrails**: PII scrubbing before text reaches the LLM,
  output validation after.
- **Phase 5 — MCP tools**: expose a policy-lookup / premium-calculator tool
  over MCP and let the graph call it.
- **Phase 6 — Observability**: OpenTelemetry tracing + Prometheus metrics +
  a Grafana dashboard, once there's a system worth watching.
