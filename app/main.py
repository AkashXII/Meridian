import json
import sys

from app.graph import build_graph


def main():
    graph = build_graph()

    if len(sys.argv) > 1:
        raw_text = " ".join(sys.argv[1:])
    else:
        with open("data/sample_claims.json") as f:
            samples = json.load(f)
        raw_text = samples[0]["text"]

    print(f"Claim input:\n{raw_text}\n{'-' * 50}")

    result = graph.invoke(
        {
            "raw_claim_text": raw_text,
            "extracted": None,
            "missing_fields": [],
            "coverage_decision": None,
        }
    )

    print("\nExtracted fields:")
    print(result["extracted"].model_dump_json(indent=2) if result["extracted"] else "None")

    if result.get("coverage_decision"):
        print("\nCoverage decision:")
        print(result["coverage_decision"].model_dump_json(indent=2))
    else:
        print(f"\nStopped for clarification. Missing: {result['missing_fields']}")


if __name__ == "__main__":
    main()
