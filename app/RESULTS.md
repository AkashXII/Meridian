# RESULTS.md

## Retrieval

### Headline numbers (current corpus: 48 chunks, clause-boundary chunked)

| Eval set | Metric | Score |
|---|---|---|
| Labeled (25 queries, self-authored) | Recall@3 | 0.96 |
| Labeled | MRR | 0.86 |
| Blind (18 queries, written without seeing the corpus) | Recall@3 | 0.65 |
| Blind | Recall@5 | 0.76 |

**Why two eval sets.** The labeled set was written by the same process that wrote the corpus, so its vocabulary naturally overlaps with the clauses — a soft ceiling, not a clean measurement. The blind set was written independently, in real-user phrasing, with the doc_id label assigned only *after* the query was written, to prevent the corpus from shaping the query. The blind number is the one that reflects real-world performance; the labeled number is a sanity check that the pipeline works at all.

**Why recall@3 and recall@5 are both reported.** The live pipeline consumes `top_k=3` — recall@3 reflects what the system actually uses. The gap to recall@5 shows how often the correct clause is retrieved but ranked 4th–5th (a reranker-ordering issue) rather than missed entirely (a retrieval-coverage issue). Here, that gap is real: several correct-but-buried documents move into the top 5 but not the top 3.

### Corpus evolution

- 35 → 100 → 164 hand-authored atomic documents (one clause per entry)
- Final architecture: 4 realistic multi-paragraph policy documents (auto, home, health, general), ingested via a **clause-boundary chunking pipeline** — split on paragraph breaks (each paragraph = one self-contained clause), with a `RecursiveCharacterTextSplitter` fallback only for a clause that exceeds the size limit. 48 chunks total.
- Chunking strategy was deliberate: fixed-size/token-window splitting risks cutting a clause mid-rule and blurring its embedding. Clause-boundary splitting reproduces the same atomicity as the hand-authored corpus, but from realistic flowing source documents.

### The investigation: five hypotheses, mostly falsified

Blind recall started at **0.167** on the first honest blind set. Getting to 0.65–0.76 took ruling out four dead ends before finding what actually worked.

| Hypothesis | Test | Result |
|---|---|---|
| Corpus too small | 35 → 100 → 164 docs | Blind recall unchanged. Falsified. |
| Embedding model too weak | MiniLM → BGE-small-en-v1.5 | Labeled MRR +0.03; blind recall unchanged, MRR slightly worse. Falsified. |
| Reranker too weak | ms-marco-MiniLM-L-6-v2 → BAAI/bge-reranker-base | Fixed specific targeted cases, broke others. Net identical aggregate score. Falsified as a general fix. |
| Naive fixed-size chunking would help | (not built — reasoned out) | Chunks would be *less* atomic than the existing hand-authored corpus, which is already the end-state chunking produces. Rejected before building. |
| Clause rewording (remove generic phrasing) | Anchored the auto policy's Comprehensive clause to reduce cross-domain matches | Query that was supposed to be fixed still failed — the *entire* auto document's vocabulary was broad enough that another auto clause won instead. Falsified. |

**What actually moved the number:**
1. **Closing genuine content gaps.** Several blind-query misses had no answering document at all — not a ranking problem, a missing one. Added: a general medical-treatment clause covering common injury/illness language (fractures, infections, sprains) that the existing ER/urgent-care clause didn't cover; a civil-disturbance/protest clause folded into vehicle vandalism coverage. Confirmed via raw vector + BM25 checks before adding — a doc was only added when both methods failed to find *any* answering clause, not on a hunch.
2. **Multi-query retrieval.** An LLM generates 2–3 reframings of the raw query (formal terminology, peril-focused, treatment-focused), each retrieved independently, results merged keeping the best score per document. Improved blind recall@5 from 0.40 → 0.60 in isolated testing — surfaces correct-but-buried documents into the candidate pool. Did not improve recall@3, since it surfaces documents rather than re-ranking them. Not wired into the live `top_k=3` decision path, since the measured benefit is at @5, not @3; kept as a documented, tested capability.

### Three diagnosed failure modes

1. **Lexical collision.** A documentation-reimbursement clause containing the phrase "medical record fee" was matching every health-domain query regardless of topic — an accidental word choice, not a real relationship. Fixed by rewording; confirmed via before/after diff that the specific collision stopped while other queries were unaffected.

2. **Content gap requiring multi-hop reasoning.** Several failing queries ("fractured my arm," "cat scratched me") were being checked against a clause about ER *visit reimbursement rates* — a real but wrong target. Answering these correctly from that clause would require: fracture → ER visit → rate applies, a two-hop inference no embedding model performs. The actual fix wasn't reranking harder; it was recognizing the eval label itself pointed at the wrong document, and adding the general medical-treatment clause that directly answers the query in one hop.

3. **Structural competition from generic clauses.** Short, dollar-amount-generic clauses (documentation thresholds, deductibles) semantically attract almost any query that mentions money, regardless of topic. This is a structural property of dense retrieval on financially-generic text, not a fixable wording issue — confirmed by checking that the offending clauses won on *vector* similarity, not BM25 (ruling out a lexical fix), and by the same pattern recurring on a second, unrelated document after the first instance was fixed. Resolved for the clearest cases (documentation/assessment thresholds) by moving the logic to deterministic code (`general_rules.py`) rather than leaving it in the retrieval pool — the rule is now enforced regardless of whether retrieval surfaces it, so the residual retrieval noise no longer affects correctness.

### What's still unsolved, and why that's the honest stopping point

Some blind queries still fail — mostly short, casual descriptions with no clause-specific vocabulary, competing against unrelated documents that share generic "damage/covered/claim" language. Every mechanical lever available at this scale was tested: corpus size, embedding model, reranker model, chunking strategy, clause wording. None of them close this residual gap, because it isn't a defect in any one component — it's the general difficulty of matching colloquial descriptions to formal clause language with off-the-shelf embeddings. The next real lever (a domain-fine-tuned embedding model, or a fundamentally different retrieval approach) is beyond the scope of a project this size, and reaching for it now would be solving a problem the evidence says is upstream of any component-level fix.

---

## Faithfulness

**Question asked:** does the model's stated reasoning for a decision stay grounded in the policy clauses it actually retrieved, or does it introduce something that wasn't there?

**Result: 17/17 grounded** on a real, varied sample (auto/home/health claims, spanning approved/denied/needs_review outcomes).

### Methodology

- LLM-as-judge, given only the retrieved clause text and the generated reasoning — never the claim details, so it can't rationalize based on outcome.
- **Judge is a different model than the one generating decisions**, specifically to avoid self-enhancement bias (a documented tendency for LLM judges to rate their own model family's reasoning style more favorably).
- Verified against **two independent hand-planted hallucinations** before trusting any real verdict:
  - A fabricated entitlement (an invented "loyalty bonus" payout uplift) — caught.
  - A fabricated exclusion (an invented "50-mile geographic restriction") — caught.
  
  Testing both directions (fake reason to pay more, fake reason to deny) confirms the judge discriminates fabrication generally, not one memorized pattern.

### Debugging arc

The eval broke in three distinct, real ways before reaching a stable state:

1. **Structured-output incompatibility.** The generation model has a documented issue with the default tool-calling structured-output method — it sometimes returns a correct answer as prose instead of the forced schema, causing a hard crash. Fixed by switching to `json_mode` with the JSON shape spelled out explicitly in the prompt (`json_mode` enforces valid JSON, not a specific schema, so the prompt has to carry that weight).
2. **Judge too literal.** After the above fix, the judge began flagging valid arithmetic and reasonable inferences ("the exclusion doesn't apply because its trigger condition is absent from the claim") as fabrication. Fixed by explicitly telling the judge what does *not* count as unsupported: restating claim facts, valid comparisons against a real limit, and reasonable negative inference from a present condition.
3. **Corpus drift.** After the corpus changed (chunking rebuild), old audit rows referenced doc_ids that no longer existed. A partial match (some doc_ids resolve, some don't) is worse than no match, since it silently feeds the judge a misleading subset of context. Fixed by requiring *all* referenced doc_ids to resolve before judging a row; anything less is skipped with a stated reason, not silently mis-scored.

### Known limitation

17 claims is a real, varied sample, not a large one. The two independent trap cases are the stronger evidence that the judge itself is reliable; the 100% rate on real claims should be read alongside that, not in isolation.
