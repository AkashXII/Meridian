# Meridian — Multi-Agent Insurance Claims Platform

A multi-agent insurance claims pipeline built with **LangGraph**, combining hybrid retrieval, deterministic fraud and processing rules, PII redaction, and a human-in-the-loop review queue — with distributed tracing and a from-scratch retrieval evaluation across every stage.

[**Watch the walkthrough →**](https://youtu.be/D1JkSALuKb4?si=8HHUmv470CBxqxwy)

![Architecture diagram](assests/meridis.png)

---

A policyholder describes a claim in plain language. The system extracts structured details, retrieves relevant policy clauses, checks fraud/processing rules deterministically, reaches a coverage decision, and escalates to a human reviewer when needed. Every step is traced; every claim is audited; retrieval and faithfulness are both evaluated, not assumed.

---

## Key features

- **LangGraph pipeline:** (check the architecture image)
- **Hybrid retrieval** (vector + BM25 + cross-encoder rerank) over a chunked policy corpus, with clause-boundary chunking and a recursive-splitter fallback
- **Deterministic rules kept out of the LLM entirely:** `fraud_rules.py` (prefix, filing deadline, amount sanity) and `general_rules.py` (documentation/assessment thresholds) — both plain comparisons, no model involved
- **Human-in-the-loop review queue:** fraud-flagged approvals escalate to `needs_review`, never silently auto-decided. The AI's original assessment and the reviewer's final call are stored separately, so neither overwrites the other
- **LLM-as-judge faithfulness checks** using a different model than the one that generates decisions, verified against two hand-planted hallucinations before being trusted
- **Full audit trail** in MySQL, distributed tracing via OpenTelemetry + Jaeger

![Jaeger trace showing parallel coverage_check and fraud_check spans](assests/jaegar1.png)
![Jaeger trace showing parallel coverage_check and fraud_check spans](assests/jaegar2.png)

---

## Tech stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| LLM | Groq (`openai/gpt-oss-120b`) |
| Retrieval | ChromaDB (vector) + BM25 (keyword) + cross-encoder rerank (`BAAI/bge-reranker-base`) |
| Backend | FastAPI, JWT auth, rate limiting |
| Database | MySQL (audit trail, users, review status) |
| Frontend | React |
| Observability | OpenTelemetry + Jaeger |
| PII detection | NER + regex-based redaction, pre-LLM |

---

## Retrieval & faithfulness evaluation

Full methodology and failure-mode analysis in [`RESULTS.md`](./RESULTS.md). Headline numbers:

| | Score |
|---|---|
| Retrieval — labeled set | 0.96 recall@3 |
| Retrieval — blind set (queries written without seeing the corpus) | 0.65 recall@3 / 0.76 recall@5 |
| Faithfulness (LLM-as-judge, different model than the generator) | 17/17 grounded |

The blind/labeled gap is the real finding, check out `RESULTS.md` for the five tested hypotheses and the two failure modes that actually explained it.

---

## Scoping decisions
- No MCP — pipeline doesn't call external tools at decision time
- No Prometheus — Jaeger + the MySQL audit trail already cover observability needs
- Deterministic rules (`fraud_rules.py`, `general_rules.py`) kept out of retrieval — closed-form comparisons, not search
- No life-insurance claim type — a structurally different product, out of scope
- Clause-boundary chunking, not fixed-size — insurance clauses are self-contained units; fixed windows risk cutting one mid-rule

---

## Running it locally

**Startup order matters** — later services depend on earlier ones being up.

```bash
# 1. MySQL
sudo systemctl start mysql

# 2. Jaeger (traces are in-memory and reset on restart)
docker start jaeger
# if it doesn't exist yet:
docker run -d --name jaeger -p 16686:16686 -p 4317:4317 -p 4318:4318 jaegertracing/all-in-one:latest

# 3. Backend
source .venv/bin/activate
uvicorn app.api:app --reload
# → http://localhost:8000/docs

# 4. Frontend
cd frontend
npm run dev
```

**Environment variables** (`.env`):
```
GROQ_API_KEY=your_key_here
GROQ_MODEL=openai/gpt-oss-120b
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=...
DB_PASSWORD=...
DB_NAME=claims_platform
JWT_SECRET=...
HF_HUB_OFFLINE=1
```

First run needs `HF_HUB_OFFLINE=0` once, to download the embedding and reranker models — after that, `1` keeps startup fast and fully offline.

---

## Project structure

```
app/
  nodes.py              
  graph.py              
  chunker.py            
  fraud_rules.py        
  general_rules.py      
  pii.py                 
  audit_store.py          
  api.py / auth.py        
  retrieval/
    vector_store.py
    keyword_store.py
    hybrid_retriever.py
data/
  auto_policy.txt, home_policy.txt, health_policy.txt, general_terms.txt
eval/
  run_eval.py              
  run_blind_chunked.py       
  faithfulness_eval.py         
frontend/
  src/  # Login, SubmitClaim, ClaimResult, ClaimHistory, ReviewQueue
```

---

## Known limitations

- Retrieval underperforms on short, colloquial queries with no clause-specific vocabulary — a structural property of dense retrieval, diagnosed in `RESULTS.md`, not a bug to fix
- No policyholder/declarations-page database — the corpus models policy *terms*, not individual customer records
- Jaeger traces are in-memory and don't survive a restart
- No Docker Compose yet — scoped, not yet built

