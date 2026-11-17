"""
Measures the two retrieval changes on the existing labeled + blind sets.

Part 1 - claim-type scope filter (app/retrieval/scope.py)
    Runs every query twice through the production hybrid retriever: once over
    the whole corpus (old behaviour) and once restricted to the claim's policy
    line + general terms (new behaviour). Reports recall@3, recall@5 and MRR
    for both, lists exactly which queries were fixed or broken, and gives an
    exact McNemar p-value for the paired difference.

    The claim type for each query is taken from its gold label (auto_7 ->
    auto). That assumes intake classifies the claim correctly, so this is an
    UPPER BOUND on the benefit: in production a misclassified claim is
    filtered to the wrong policy line. Queries whose answer is a general_*
    clause have no single policy line, so they are run unfiltered in both
    modes (they can't change).

Part 2 - confidence threshold calibration (app/retrieval/confidence.py)
    With the filter on (the production config), records the top-1 rerank
    score of every query and whether the correct clause made the top 3.
    Sweeps thresholds and reports, for each: how many retrieval misses would
    be escalated (good) and how many correct retrievals would be escalated
    anyway (cost: unnecessary human reviews).

    Caveat: 42 queries, and the same queries are used to both pick and
    report the threshold. Treat the result as a starting value to confirm
    on a larger held-out set, not a tuned constant.

Queries are run raw (no "{claim_type} claim: " prefix) so the numbers stay
comparable with run_labeled_chunked.py and run_chunkie_evalss.py.

Run: python -m eval.run_scope_and_confidence_eval
"""
import json
import math
from pathlib import Path

from app.chunker import ingest_policy_documents
from app.retrieval.hybrid_retriever import hybrid_search
from app.retrieval.keyword_store import build_keyword_store
from app.retrieval.scope import DOMAIN_TYPES, retrieval_scope
from app.retrieval.vector_store import build_vector_store

DATA_DIR = Path(__file__).parent.parent / "data"
EVAL_DIR = Path(__file__).parent
EVAL_SETS = [
    ("labeled", EVAL_DIR / "labeled_eval_chunked.json"),
    ("blind", EVAL_DIR / "blind_eval_set_chunked.json"),
]
TOP_K = 5
THRESHOLD_GRID = [0.01, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60]


def oracle_claim_type(relevant_ids):
    """Policy line implied by the gold label, or None for general_* answers."""
    domains = {d.split("_")[0] for d in relevant_ids} & set(DOMAIN_TYPES)
    return domains.pop() if len(domains) == 1 else None


def first_relevant_rank(retrieved_ids, relevant):
    return next((i + 1 for i, d in enumerate(retrieved_ids) if d in relevant), None)


def wilson_interval(hits, n, z=1.96):
    """95% confidence interval for a proportion; honest at small n."""
    if n == 0:
        return 0.0, 0.0
    p = hits / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return centre - half, centre + half


def mcnemar_exact_p(fixed, broken):
    """Two-sided exact McNemar test on the discordant pairs."""
    n = fixed + broken
    if n == 0:
        return 1.0
    k = min(fixed, broken)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarise(rows, mode):
    n = len(rows)
    r3 = sum(1 for r in rows if r[mode] and r[mode] <= 3)
    r5 = sum(1 for r in rows if r[mode] and r[mode] <= 5)
    mrr = sum(1 / r[mode] for r in rows if r[mode]) / n
    lo, hi = wilson_interval(r3, n)
    return f"R@3={r3/n:.3f} [95% CI {lo:.2f}-{hi:.2f}]  R@5={r5/n:.3f}  MRR={mrr:.3f}"


def main():
    chunks = ingest_policy_documents(str(DATA_DIR))
    vs = build_vector_store(chunks)
    ks = build_keyword_store(chunks)
    print(f"Corpus: {len(chunks)} chunks\n")

    calibration = []  # (set, query, top1_score, hit_at_3)

    print("=" * 78)
    print("PART 1 - claim-type scope filter (oracle claim type = upper bound)")
    print("=" * 78)
    for set_name, path in EVAL_SETS:
        cases = json.loads(path.read_text())
        rows = []
        for case in cases:
            relevant = set(case["relevant_doc_ids"])
            ctype = oracle_claim_type(relevant)
            scope = retrieval_scope(ctype)

            before = hybrid_search(vs, ks, case["query"], top_k=TOP_K)
            after = hybrid_search(vs, ks, case["query"], top_k=TOP_K, claim_types=scope)
            before_ids = [h["doc_id"] for h in before]
            after_ids = [h["doc_id"] for h in after]

            rank_after = first_relevant_rank(after_ids, relevant)
            rows.append({
                "query": case["query"],
                "scope": scope,
                "before": first_relevant_rank(before_ids, relevant),
                "after": rank_after,
                "after_top3": after_ids[:3],
                "relevant": sorted(relevant),
            })
            calibration.append((
                set_name,
                case["query"],
                after[0]["rerank_score"] if after else None,
                bool(rank_after and rank_after <= 3),
            ))

        print(f"\n[{set_name}] {len(rows)} queries")
        print(f"  unfiltered: {summarise(rows, 'before')}")
        print(f"  filtered:   {summarise(rows, 'after')}")

        hit = lambda rank: bool(rank and rank <= 3)
        fixed = [r for r in rows if not hit(r["before"]) and hit(r["after"])]
        broken = [r for r in rows if hit(r["before"]) and not hit(r["after"])]
        print(f"  @3 fixed by filter: {len(fixed)}   broken by filter: {len(broken)}   "
              f"exact McNemar p={mcnemar_exact_p(len(fixed), len(broken)):.3f}")
        for r in fixed:
            print(f"    + {r['query'][:64]}  (rank {r['before']} -> {r['after']})")
        for r in broken:
            print(f"    - {r['query'][:64]}  (rank {r['before']} -> {r['after']})")
        still_missing = [r for r in rows if not hit(r["after"])]
        if still_missing:
            print("  still missing @3 after filter:")
            for r in still_missing:
                print(f"    x {r['query'][:64]}  want {r['relevant']} got {r['after_top3']}")

    print()
    print("=" * 78)
    print("PART 2 - confidence threshold calibration (filter on, both sets pooled)")
    print("=" * 78)
    scored = [c for c in calibration if c[2] is not None]
    hits = [c for c in scored if c[3]]
    misses = [c for c in scored if not c[3]]
    all_scores = [c[2] for c in scored]
    print(f"\n{len(scored)} queries: {len(hits)} correct in top 3, {len(misses)} retrieval misses")
    print(f"top-1 score range: {min(all_scores):.4f} .. {max(all_scores):.4f}")

    print("\nTop-1 rerank score per query (lowest first):")
    for set_name, query, score, ok in sorted(scored, key=lambda c: c[2]):
        print(f"  {score:7.4f}  {'HIT ' if ok else 'MISS'}  [{set_name:7s}] {query[:56]}")

    print("\n threshold | escalated | misses caught | correct ones escalated")
    print(" ----------+-----------+---------------+-----------------------")
    best = None
    for t in THRESHOLD_GRID:
        esc = [c for c in scored if c[2] < t]
        caught = sum(1 for c in esc if not c[3])
        wasted = sum(1 for c in esc if c[3])
        tpr = caught / len(misses) if misses else 0.0
        fpr = wasted / len(hits) if hits else 0.0
        print(f"   {t:5.2f}   | {len(esc):3d}/{len(scored):<3d}   | "
              f"{caught:2d}/{len(misses):<2d} ({tpr:4.0%})   | {wasted:2d}/{len(hits):<2d} ({fpr:4.0%})")
        j = tpr - fpr
        if best is None or j > best[1]:
            best = (t, j, tpr, fpr)

    if misses:
        t, j, tpr, fpr = best
        print(f"\nBest trade-off on this data (max misses-caught minus correct-escalated): "
              f"MIN_RERANK_SCORE={t:.2f} -> catches {tpr:.0%} of misses, "
              f"escalates {fpr:.0%} of correct retrievals.")
        print("If unnecessary reviews are expensive, pick a lower row; if wrong "
              "automated decisions are expensive, pick a higher one. Set it in .env.")
    else:
        print("\nNo retrieval misses with the filter on - nothing to calibrate against.")


if __name__ == "__main__":
    main()
