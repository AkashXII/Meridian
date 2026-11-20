import re
from collections import Counter
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

POLICY_FILE = "arogya_sanjeevani_icici.pdf"
CLAIM_TYPE = "health"
MAX_CHUNK_CHARS = 1000

SECTION_HEADING = re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Z &/-]+)$")
CLAUSE_HEADING = re.compile(r"^(\d{1,2}(?:\.\d{1,2})+)\.?\s*([A-Z“\"].*)$")
LIST_HEADING = re.compile(r"^List (I{1,3}|IV) – (.+)$")

splitter = RecursiveCharacterTextSplitter(
    chunk_size=MAX_CHUNK_CHARS,
    chunk_overlap=100,
    separators=["\n", ". ", " "],
)


def read_clean_lines(pdf_path):
    pages = [page.extract_text() for page in PdfReader(pdf_path).pages]
    pages_containing = Counter(
        line for page in pages for line in {l.strip() for l in page.splitlines()}
    )
    lines = []
    for page in pages:
        for line in page.splitlines():
            line = line.strip()
            if not line or line.isdigit() or pages_containing[line] >= len(pages) / 2:
                continue
            lines.append(line)
    return lines


def split_regions(lines):
    wording_end = lines.index("TABLE OF BENEFITS")
    annexure_start = lines.index("Annexure A")
    annexure_end = lines.index("Annexure A", annexure_start + 1)
    return lines[:wording_end], lines[annexure_start + 1:annexure_end]


def make_title(text):
    return re.split(r":| means ", text, maxsplit=1)[0].strip()[:80]


def group_clauses(lines):
    clauses = []
    section_title = None
    for line in lines:
        section = SECTION_HEADING.match(line)
        clause = CLAUSE_HEADING.match(line)
        if section:
            section_title = section.group(2).title()
            clauses.append({"id": section.group(1), "section": section_title,
                            "title": section_title, "lines": []})
        elif clause and section_title:
            clauses.append({"id": clause.group(1), "section": section_title,
                            "title": make_title(clause.group(2)), "lines": [line]})
        elif clauses:
            clauses[-1]["lines"].append(line)
    return clauses


def group_annexure(lines):
    lists = []
    for line in lines:
        heading = LIST_HEADING.match(line)
        if heading:
            lists.append({"id": f"A-{heading.group(1)}", "section": "Annexure A",
                          "title": f"List {heading.group(1)}: {heading.group(2)}", "lines": []})
        elif lists:
            lists[-1]["lines"].append(line)
    return lists


def to_chunks(clause):
    header = f"{clause['section']} | {clause['id']} {clause['title']}"
    body = "\n".join(clause["lines"])
    pieces = [body] if len(body) <= MAX_CHUNK_CHARS else splitter.split_text(body)
    chunks = []
    for number, piece in enumerate(pieces, start=1):
        doc_id = f"{CLAIM_TYPE}_{clause['id']}"
        if len(pieces) > 1:
            doc_id += f"_p{number}"
        chunks.append({
            "doc_id": doc_id,
            "claim_type": CLAIM_TYPE,
            "title": clause["title"],
            "text": f"{header}\n{piece}",
        })
    return chunks


def ingest_policy_documents(data_dir):
    lines = read_clean_lines(Path(data_dir) / POLICY_FILE)
    wording, annexure = split_regions(lines)
    clauses = [c for c in group_clauses(wording) + group_annexure(annexure) if c["lines"]]
    return [chunk for clause in clauses for chunk in to_chunks(clause)]


if __name__ == "__main__":
    chunks = ingest_policy_documents("data")
    ids = [c["doc_id"] for c in chunks]
    sizes = [len(c["text"]) for c in chunks]
    print(f"{len(chunks)} chunks, {len(set(ids))} unique ids, "
          f"chars min {min(sizes)} / avg {sum(sizes) // len(sizes)} / max {max(sizes)}")
    for chunk in chunks:
        print(f"{chunk['doc_id']:<16} {len(chunk['text']):>5}  {chunk['title']}")
