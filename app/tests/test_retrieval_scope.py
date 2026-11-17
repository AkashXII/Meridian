import app.retrieval.hybrid_retriever as hr
from app.retrieval.confidence import assess_retrieval
from app.retrieval.keyword_store import build_keyword_store, query_keyword_store
from app.retrieval.scope import retrieval_scope

DOCS = [
    {"doc_id": "auto_1", "claim_type": "auto", "title": "Comprehensive", "text": "vehicle damage from a falling tree branch"},
    {"doc_id": "home_1", "claim_type": "home", "title": "Dwelling", "text": "tree branch falling on the house roof damage"},
    {"doc_id": "health_1", "claim_type": "health", "title": "ER", "text": "emergency room visit after an injury"},
    {"doc_id": "general_1", "claim_type": "general", "title": "Deadline", "text": "claims must be filed within sixty days of damage"},
]


# --- scope ------------------------------------------------------------------

def test_scope_for_each_policy_line_includes_general_terms():
    assert retrieval_scope("auto") == ["auto", "general"]
    assert retrieval_scope("home") == ["home", "general"]
    assert retrieval_scope("health") == ["health", "general"]


def test_scope_is_unfiltered_without_a_reliable_type():
    assert retrieval_scope("other") is None
    assert retrieval_scope(None) is None


# --- keyword store filter -----------------------------------------------------

def test_keyword_filter_keeps_only_allowed_types():
    store = build_keyword_store(DOCS)
    hits = query_keyword_store(store, "tree branch damage", k=5, claim_types=["home", "general"])
    assert hits and {h["claim_type"] for h in hits} <= {"home", "general"}
    assert hits[0]["doc_id"] == "home_1"


def test_keyword_without_filter_searches_everything():
    store = build_keyword_store(DOCS)
    hits = query_keyword_store(store, "tree branch damage", k=5)
    assert {h["doc_id"] for h in hits} == {d["doc_id"] for d in DOCS}


# --- hybrid passes the scope through and survives an empty pool ---------------

def test_hybrid_passes_scope_to_both_retrievers(monkeypatch):
    seen = {}

    def fake_vector(store, query, k=3, claim_types=None):
        seen["vector"] = claim_types
        return [{"doc_id": "home_1", "text": "t", "claim_type": "home", "title": "x", "score": 0.5}]

    def fake_keyword(store, query, k=3, claim_types=None):
        seen["keyword"] = claim_types
        return []

    class FakeReranker:
        def predict(self, pairs):
            return [0.8 for _ in pairs]

    monkeypatch.setattr(hr, "query_vector_store", fake_vector)
    monkeypatch.setattr(hr, "query_keyword_store", fake_keyword)
    monkeypatch.setattr(hr, "get_reranker", lambda: FakeReranker())

    out = hr.hybrid_search(None, None, "q", top_k=3, claim_types=["home", "general"])
    assert seen == {"vector": ["home", "general"], "keyword": ["home", "general"]}
    assert out[0]["rerank_score"] == 0.8


def test_hybrid_returns_empty_without_calling_reranker(monkeypatch):
    monkeypatch.setattr(hr, "query_vector_store", lambda *a, **kw: [])
    monkeypatch.setattr(hr, "query_keyword_store", lambda *a, **kw: [])

    def boom():
        raise AssertionError("reranker should not be called on an empty pool")

    monkeypatch.setattr(hr, "get_reranker", boom)
    assert hr.hybrid_search(None, None, "q", claim_types=["auto", "general"]) == []


# --- confidence ---------------------------------------------------------------

def test_nothing_retrieved_is_low_confidence():
    assert assess_retrieval([], threshold=0.1) == (None, True)


def test_top_score_below_threshold_is_low_confidence():
    assert assess_retrieval([{"rerank_score": 0.05}], threshold=0.1) == (0.05, True)


def test_top_score_at_or_above_threshold_is_confident():
    assert assess_retrieval([{"rerank_score": 0.1}], threshold=0.1) == (0.1, False)
    assert assess_retrieval([{"rerank_score": 0.9}, {"rerank_score": 0.01}], threshold=0.1) == (0.9, False)


def test_missing_rerank_score_is_low_confidence():
    assert assess_retrieval([{"doc_id": "auto_1"}], threshold=0.1) == (None, True)
