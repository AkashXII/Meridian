
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

MAX_CHUNK_CHARS = 500

_fallback_splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHUNK_CHARS,
    chunk_overlap=80,
    separators=["\n\n", ". ", " ", ""],  
)

TITLE_PATTERN = re.compile(r"^\*\*(.+?)\.\*\*\s*(.*)", re.DOTALL)


def _extract_title(paragraph: str) -> tuple[str, str]:
    match = TITLE_PATTERN.match(paragraph.strip())
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "Untitled Clause", paragraph.strip()


def chunk_document(text: str, claim_type: str, source_doc: str) -> list[dict]:
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
    fallback_hits = [c for c in chunks if "(part)" in c["title"]]
    print(f"Fallback-split chunks: {len(fallback_hits)}")
    for c in fallback_hits:
        print(f"  {c['doc_id']} - {c['title']} ({len(c['text'])} chars)")

    print()
    print("Sample chunks:")
    for c in chunks[:3]:
        print(f"  [{c['doc_id']}] {c['title']}: {c['text'][:70]}...")
    oversized = [c for c in chunks if len(c["text"]) > MAX_CHUNK_CHARS + 50]
    print(f"\nChunks still over size limit after fallback: {len(oversized)}")
    assert not oversized, "fallback splitter failed to bring a chunk under the limit"
    print("OK: all chunks within size bounds")