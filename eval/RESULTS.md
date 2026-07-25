# Retrieval Evaluation

Evaluates the actual production retriever (`hybrid_search`: vector + BM25 +
cross-encoder rerank) against a labeled query set, rather than judging
retrieval quality by eye.

## Methodology

- **Corpus:** 35 policy clauses across auto/home/health/general, expanded
  from an original 8. Deliberately includes near-collision pairs — clauses
  that are topically close but require different handling — so the eval
  actually has something to distinguish: flood exclusion vs. burst-pipe
  coverage, theft sublimit vs. jewelry sublimit, filing deadline vs. grace
  period vs. cancellation notice, two different "waiting period" clauses
  (pre-existing conditions vs. maternity).
- **Eval set:** 25 hand-labeled `(query, relevant_doc_ids)` pairs, split
  across three query types:
  - *Lexical* — shares exact wording with the target clause.
  - *Semantic* — paraphrased, minimal word overlap with the target.
  - *Adversarial* — superficially resembles a different clause, testing
    whether retrieval distinguishes near-collisions rather than pattern-matching.
- **k = 3** — matches `top_k` used in the actual `coverage_check` /
  `fraud_check` nodes.
- **Metrics:** precision@3, recall@3, mean reciprocal rank (MRR).

**Limitation, stated up front:** both the corpus and the eval labels were
authored by the same process building the retriever being tested. This
risks the labels quietly matching what the retriever happens to be good
at. Treat these results as a sanity check on a small, controlled corpus,
not as evidence the system generalizes to a large, messy real-world policy
database.

## Results

| Strategy | P@3 | R@3 | MRR |
|---|---|---|---|
| BM25 only | 0.280 | 0.820 | 0.780 |
| Vector only | 0.333 | 0.960 | 0.940 |
| Hybrid + rerank | 0.347 | **1.000** | **0.980** |

**Hybrid earns its keep, but modestly.** Vector search alone already
handles most queries well — it's the stronger of the two individual
methods here, likely because several eval queries are paraphrases with
low lexical overlap, which BM25 isn't built for. BM25 alone is the
weakest, missing ~18% of relevant docs in the top 3. Hybrid + rerank
recovers the gap vector-only leaves open: +4 points recall, +4 points MRR,
closing to a perfect score across all 25 queries. On this corpus, the
reranker's job is less about fixing a broken retriever and more about
cleaning up the last few percent vector search alone doesn't catch.

## Interpretation

**Recall@3 = 1.000 and MRR = 0.980 are the results that matter.** Every
query — including every adversarial near-collision case — found its
correct document within the top 3, and 24 of 25 queries ranked the correct
document first. The hybrid + rerank pipeline correctly separated clauses
that share surface vocabulary but mean different things (e.g. distinguishing
a burst-pipe claim from a flood claim despite both involving water damage).

**Precision@3 = 0.347 is not a meaningful failure — it's an artifact of the
eval design, not the retriever.** 24 of 25 queries have exactly one
relevant document. With `k=3`, the maximum achievable precision@3 for a
single-relevant-document query is 1/3 ≈ 0.333, regardless of retriever
quality — the other two returned slots are "correct misses" by
construction. The observed 0.347 is consistent with near-perfect retrieval
under this eval design, not evidence of noisy results. A fairer precision
comparison would need either a smaller `k` or an eval set with more
multi-relevant queries.

**One concrete near-miss:** *"therapy sessions covered the same as a
regular doctor visit"* (expecting `health_7`, Mental Health Parity) ranked
`health_4` (Emergency Room Coverage) first instead, placing the correct
document at rank 2. Likely cause: the query shares surface vocabulary
("visit", "covered") with `health_4`, while `health_7`'s actual matching
language ("same reimbursement rate as physical health services") doesn't
lexically or semantically echo the query as strongly. This is the single
data point keeping MRR below a perfect 1.0.

## Limitations

- Eval set size (n=25) is too small to support statistical significance
  testing between configurations.
- Single annotator (no inter-rater agreement check on relevance labels).
- Corpus (35 docs) is far smaller than a real policy database; retrieval
  difficulty scales with corpus size and document similarity, so these
  results should not be read as "retrieval is solved."
- No ablation across retrieval strategies (vector-only vs. BM25-only vs.
  hybrid) was run in this pass — this evaluates the production
  configuration only, by design, not a comparison across alternatives.
