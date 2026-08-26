"""
Document ingestion and chunking.

Splits multi-clause source documents into atomic, retrievable chunks.

Primary strategy: split on paragraph boundaries (blank lines). Each source
document was authored with one self-contained clause per paragraph, so a
paragraph split IS a clause split - no clause gets divided mid-sentence, and
no chunk blends two unrelated rules together. This preserves the same
atomicity that a hand-authored one-clause-per-document corpus has, but starts
from realistic flowing policy documents instead.

Fallback strategy: RecursiveCharacterTextSplitter, used ONLY when a single
paragraph exceeds MAX_CHUNK_CHARS. Fixed-size/recursive splitting is the
standard approach for arbitrary long text, but applying it as the PRIMARY
strategy here would risk splitting a clause mid-rule and blurring its
embedding - exactly the failure mode this pipeline is designed to avoid. It's
kept as a safety net for the case a real author writes an oversized clause,
not as the default.
"""
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_CHUNK_CHARS = 500

_fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHUNK_CHARS,
    chunk_overlap=80,
    separators=["\n\n", ". ", " ", ""],  # prefer sentence boundaries over mid-word
)

TITLE_PATTERN = re.compile(r"^\*\*(.+?)\.\*\*\s*(.*)", re.DOTALL)


def _extract_title(paragraph: str) -> tuple[str, str]:
    """
    Splits a paragraph into (title, body) using the leading **Bold Title.**
    convention. Falls back to a generic title if the pattern isn't found -
    ingestion should degrade gracefully on malformed input, not crash on it.
    """
    match = TITLE_PATTERN.match(paragraph.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Untitled Clause", paragraph.strip()


def chunk_document(text: str, claim_type: str, source_doc: str) -> list[dict]:
    """
    Splits one source document's raw text into chunk dicts matching the same
    shape as the existing hand-authored corpus entries (doc_id, claim_type,
    title, text), so they can be merged into the same retrieval pipeline
    without any changes to vector_store.py, keyword_store.py, or
    hybrid_retriever.py.
    """
    paragraphs = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    chunks = []
    counter = 1

    for para in paragraphs:
        title, body = _extract_title(para)

        if len(para) <= MAX_CHUNK_CHARS:
            chunks.append({
                "doc_id": f"{source_doc}_{counter}",
                "claim_type": claim_type,
                "title": title,
                "text": body,
            })
            counter += 1
        else:
            # Oversized clause - fall back to recursive splitting, but keep
            # the same clause title on every sub-chunk so provenance survives.
            sub_pieces = _fallback_splitter.split_text(body)
            for sub in sub_pieces:
                chunks.append({
                    "doc_id": f"{source_doc}_{counter}",
                    "claim_type": claim_type,
                    "title": f"{title} (part)",
                    "text": sub.strip(),
                })
                counter += 1

    return chunks


def ingest_policy_documents(data_dir: str) -> list[dict]:
    """
    Reads the four source documents and chunks all of them into one flat
    list, matching data/policy_docs.json's existing shape.
    """
    sources = {
        "auto_policy.txt": "auto",
        "home_policy.txt": "home",
        "health_policy.txt": "health",
        "general_terms.txt": "general",
    }

    all_chunks = []
    for filename, claim_type in sources.items():
        path = Path(data_dir) / filename
        text = path.read_text()
        source_doc = filename.replace(".txt", "").replace("_policy", "").replace("_terms", "")
        chunks = chunk_document(text, claim_type, source_doc)
        all_chunks.extend(chunks)

    return all_chunks


if __name__ == "__main__":
    chunks = ingest_policy_documents("data")
    print(f"Total chunks: {len(chunks)}\n")

    from collections import Counter
    print("By claim_type:", Counter(c["claim_type"] for c in chunks))
    print()

    # Verify the fallback actually fired on the deliberately oversized paragraph
    fallback_hits = [c for c in chunks if "(part)" in c["title"]]
    print(f"Fallback-split chunks: {len(fallback_hits)}")
    for c in fallback_hits:
        print(f"  {c['doc_id']} - {c['title']} ({len(c['text'])} chars)")

    print()
    print("Sample chunks:")
    for c in chunks[:3]:
        print(f"  [{c['doc_id']}] {c['title']}: {c['text'][:70]}...")

    # Sanity: no chunk should still exceed the limit after fallback splitting
    oversized = [c for c in chunks if len(c["text"]) > MAX_CHUNK_CHARS + 50]
    print(f"\nChunks still over size limit after fallback: {len(oversized)}")
    assert not oversized, "fallback splitter failed to bring a chunk under the limit"
    print("OK: all chunks within size bounds")