"""
Cross-checks the custom faithfulness eval against RAGAS's Faithfulness metric,
on the same real claims, using the same underlying judge model (via
get_judge_llm()) - so the comparison isolates one variable: same model, same
claims, RAGAS's scoring logic instead of the hand-written judge prompt.

Written against ragas 0.4.3's "collections" API specifically. This version's
Faithfulness metric is scored per-row directly (ascore()), not through the
older batch evaluate() function - evaluate() rejects collections-style metric
objects outright in this release. If you're on a different ragas version,
the import paths / calling convention here may not match; check what's
actually installed rather than assuming this still applies.

Run in a SEPARATE venv from the main project's - see the venv setup notes
below.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# --- workaround for real environment issues, verified end-to-end ---
# ragas declares langchain / langchain-community / langchain-openai as
# dependencies and imports them eagerly at load time, even though this
# project only uses langchain_groq. Installing ragas's real dependency set
# downgrades langchain-core in a way that breaks langgraph outright (verified
# directly - langgraph fails to import after a full ragas install). ragas is
# installed with --no-deps for this reason; everything it imports from the
# langchain family that this project doesn't use is stubbed out below.
import types
def _stub(name, attrs=None):
    m = types.ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m
_Dummy = lambda name: type(name, (), {})
_stub("langchain_community.chat_models.vertexai", {"ChatVertexAI": _Dummy("ChatVertexAI")})
_stub("langchain_community.llms", {"VertexAI": _Dummy("VertexAI")})
_stub("langchain_community.chat_models", {"ChatVertexAI": _Dummy("ChatVertexAI")})
_stub("langchain_community", {})
_stub("langchain", {})
_chat = _stub("langchain_openai.chat_models", {"AzureChatOpenAI": _Dummy("AzureChatOpenAI"), "ChatOpenAI": _Dummy("ChatOpenAI")})
_llms_base = _stub("langchain_openai.llms.base", {"BaseOpenAI": _Dummy("BaseOpenAI")})
_llms = _stub("langchain_openai.llms", {"AzureOpenAI": _Dummy("AzureOpenAI"), "OpenAI": _Dummy("OpenAI"), "base": _llms_base})
_emb = _stub("langchain_openai.embeddings", {"OpenAIEmbeddings": _Dummy("OpenAIEmbeddings")})
_stub("langchain_openai", {
    "ChatOpenAI": _chat.ChatOpenAI, "AzureChatOpenAI": _chat.AzureChatOpenAI,
    "OpenAI": _llms.OpenAI, "AzureOpenAI": _llms.AzureOpenAI,
    "OpenAIEmbeddings": _emb.OpenAIEmbeddings,
    "chat_models": _chat, "llms": _llms, "embeddings": _emb,
})
# --- end workaround ---

import os
import json
import asyncio

from eval.faithfulness_eval import fetch_real_cases, load_doc_texts, TRAP_CASE
from app.llm import get_judge_llm

from ragas.metrics.collections import Faithfulness
from ragas.llms import llm_factory
from openai import AsyncOpenAI


def build_context_list(doc_ids, doc_lookup):
    """Same all-or-nothing resolution as the custom eval, returning a list of
    individual clause texts (RAGAS's expected shape) rather than one joined
    string - passing a single blob instead of real chunks is a documented
    RAGAS pitfall for the context-based metrics."""
    texts = []
    for doc_id in doc_ids:
        doc = doc_lookup.get(doc_id)
        if doc is None:
            return None
        texts.append(doc["text"])
    return texts


def build_judge_llm():
    """
    Wraps the SAME judge model this project's own faithfulness eval already
    uses (get_judge_llm(), a Groq ChatGroq instance) for RAGAS's llm_factory,
    which wants a raw OpenAI-compatible client rather than a LangChain object.
    Groq exposes an OpenAI-compatible endpoint, so this points a real
    AsyncOpenAI client at Groq using the same API key and model name the
    project already uses - not a different/new model choice.
    """
    underlying = get_judge_llm()
    model_name = getattr(underlying, "model_name", None) or getattr(underlying, "model", None)
    if not model_name:
        raise RuntimeError(
            "Could not read a model name off get_judge_llm()'s return value - "
            "check what attribute actually holds it (print(vars(get_judge_llm())) "
            "to inspect) and hardcode it here if needed."
        )

    client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ["GROQ_API_KEY"],
    )
    return llm_factory(model_name, client=client)


import time

async def score_with_retry(metric, user_input, response, retrieved_contexts, max_retries=3):
    """
    instructor's own retry (visible in the traceback as 'Total attempts: 1')
    gave up after a single attempt on an empty-generation response - the same
    flaky-empty-completion behavior this model has shown throughout this
    project (see the faithfulness_eval.py debugging notes). Retrying at this
    level, same pattern as judge_with_retry() in the custom eval, rather than
    relying on instructor's built-in retry count.
    """
    for attempt in range(max_retries):
        try:
            return await metric.ascore(
                user_input=user_input, response=response, retrieved_contexts=retrieved_contexts
            )
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 * (attempt + 1)
            print(f"     (ragas call failed: {type(e).__name__}, retrying in {wait}s...)")
            time.sleep(wait)


async def main():
    doc_lookup = load_doc_texts()
    real_cases = fetch_real_cases()

    if not real_cases:
        print("No claims found. Run some claims through the main pipeline first.")
        return

    rows = []
    skipped = 0
    for row in real_cases:
        if "Overridden to needs_review" in row["coverage_reasoning"]:
            skipped += 1
            continue
        retrieved = json.loads(row["retrieved_docs"])
        doc_ids = [d["doc_id"] for d in retrieved]
        contexts = build_context_list(doc_ids, doc_lookup)
        if contexts is None:
            skipped += 1
            continue
        rows.append({
            "claim_id": row["id"],
            "user_input": row.get("claim_type", "") or "claim",
            "response": row["coverage_reasoning"],
            "retrieved_contexts": contexts,
        })

    trap_contexts = build_context_list(TRAP_CASE["doc_ids"], doc_lookup)
    rows.append({
        "claim_id": "TRAP",
        "user_input": TRAP_CASE["claim_type"],
        "response": TRAP_CASE["reasoning"],
        "retrieved_contexts": trap_contexts,
    })

    print(f"Judging {len(rows)} rows via RAGAS ({skipped} stale/legacy rows skipped, same as custom eval)\n")

    judge_llm = build_judge_llm()
    metric = Faithfulness(llm=judge_llm)

    results = []
    for r in rows:
        try:
            result = await score_with_retry(
                metric,
                user_input=r["user_input"],
                response=r["response"],
                retrieved_contexts=r["retrieved_contexts"],
            )
        except Exception as e:
            print(f"  claim {r['claim_id']:>6}  SKIPPED - failed after retries ({type(e).__name__})")
            continue
        score = result.value
        results.append((r["claim_id"], score))
        print(f"  claim {r['claim_id']:>6}  faithfulness={score:.3f}")

    if not results:
        print("\nNo rows scored successfully.")
        return

    real_scores = [s for cid, s in results if cid != "TRAP"]
    trap_result = next(((cid, s) for cid, s in results if cid == "TRAP"), None)

    print(f"\n--- RAGAS Faithfulness ---")
    if real_scores:
        print(f"Real claims: mean {sum(real_scores)/len(real_scores):.3f} over {len(real_scores)} rows")
    else:
        print("Real claims: none scored successfully.")
    if trap_result:
        trap_score = trap_result[1]
        print(f"Trap case (planted hallucination): {trap_score:.3f} "
              f"({'correctly flagged low' if trap_score < 0.7 else 'MISSED - scored high despite fabrication'})")
    else:
        print("Trap case: failed to score after retries - could not verify.")
    print(f"\n--- For comparison: custom judge result was 17/17 grounded, trap case caught ---")


if __name__ == "__main__":
    asyncio.run(main())