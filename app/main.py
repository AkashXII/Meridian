import json
import sys
import time

from opentelemetry import propagate

from app.audit_store import record_decision
from app.graph import build_graph
from app.tracing import shutdown_tracing, tracer


def main():
    graph = build_graph()

    if len(sys.argv) > 1:
        raw_text = " ".join(sys.argv[1:])
    else:
        with open("data/sample_claims.json") as f:
            samples = json.load(f)
        raw_text = samples[0]["text"]

    print(f"Claim input:\n{raw_text}\n{'-' * 50}")

    with tracer.start_as_current_span("claim_pipeline"):
        carrier = {}
        propagate.inject(carrier)

        start = time.time()
        result = graph.invoke(
            {
                "raw_claim_text": raw_text,
                "redacted_claim_text": "",
                "pii_found": [],
                "extracted": None,
                "missing_fields": [],
                "coverage_decision": None,
                "fraud_check": None,
                "retrieved_docs": [],
                "trace_carrier": carrier,
                "input_tokens": 0,
                "output_tokens": 0,
                "estimated_cost_usd": 0.0,
            }
        )
        latency_ms = int((time.time() - start) * 1000)

    print("\nExtracted fields:")
    print(result["extracted"].model_dump_json(indent=2) if result["extracted"] else "None")

    if result.get("coverage_decision"):
        print("\nCoverage decision:")
        print(result["coverage_decision"].model_dump_json(indent=2))
    else:
        print(f"\nStopped for clarification. Missing: {result['missing_fields']}")

    if result.get("fraud_check"):
        print("\nFraud check:")
        print(result["fraud_check"].model_dump_json(indent=2))

    print(
        f"\nTokens: {result['input_tokens']} in / {result['output_tokens']} out "
        f"— est. ${result['estimated_cost_usd']:.6f}"
    )

    record_decision(result, latency_ms)
    print(f"\n[audit] logged decision ({latency_ms}ms)")

    shutdown_tracing()


if __name__ == "__main__":
    main()