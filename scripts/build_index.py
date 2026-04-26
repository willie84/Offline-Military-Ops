"""Chunk Army regulations and build the offline vector index.

Tries multiple paragraph numbering patterns. Falls back to sliding-window
chunking when no pattern matches. Hard-caps chunk size so the embedder
never receives input over its context window.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import chromadb
import ollama
from pypdf import PdfReader
from tqdm import tqdm

ROOT = Path(__file__).resolve().parent.parent
REGS_DIR = ROOT / "corpus" / "regs"
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION_NAME = "army_regs"
EMBED_MODEL = "nomic-embed-text"

# Embedder context limit. nomic-embed-text is 8192 tokens; we stay safely under.
MAX_CHARS_PER_CHUNK = 1200  # ~500 tokens, plenty of headroom

# Try patterns in order; first one that produces multiple matches wins.
PARA_PATTERNS = [
    re.compile(r"^(\d+[–-]\d+[a-z](?:\([0-9a-z]+\))?)\.\s", re.MULTILINE),
    re.compile(r"^(\d+[–-]\d+)\.\s", re.MULTILINE),
    re.compile(r"^(\d{1,3})\.\s+[A-Z]", re.MULTILINE),
    re.compile(r"^(Chapter\s+\d+|Section\s+[IVX]+)", re.MULTILINE),
]
# + first-pattern-with-20+-matches wins, not best-overall
# + tighter MAX_CHARS_PER_CHUNK = 1200
# + cosine distance metric


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def split_oversized(chunk: dict) -> list[dict]:
    """If a chunk is over the embedder limit, split it into sub-chunks."""
    text = chunk["text"]
    if len(text) <= MAX_CHARS_PER_CHUNK:
        return [chunk]
    out = []
    for i in range(0, len(text), MAX_CHARS_PER_CHUNK):
        sub = text[i : i + MAX_CHARS_PER_CHUNK].strip()
        if len(sub) >= 50:
            out.append(
                {
                    "text": sub,
                    "paragraph": chunk["paragraph"],
                    "doc_id": chunk["doc_id"],
                }
            )
    return out


def chunk_by_pattern(text: str, doc_id: str) -> list[dict]:
    """Try each paragraph pattern; pick the one that gives the most chunks."""
    best_chunks: list[dict] = []
    for pattern in PARA_PATTERNS:
        matches = list(pattern.finditer(text))
        if len(matches) < 5:  # need a meaningful number of splits
            continue
        chunks = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            if len(body) < 50:
                continue
            chunks.append({"text": body, "paragraph": m.group(1).strip(), "doc_id": doc_id})
        if len(chunks) > len(best_chunks):
            best_chunks = chunks
    return best_chunks


def fallback_chunk(text: str, doc_id: str, size: int = 1200, overlap: int = 150) -> list[dict]:
    """Sliding-window chunker for regs without recognizable paragraph markers."""
    chunks = []
    step = size - overlap
    for i in range(0, len(text), step):
        body = text[i : i + size].strip()
        if len(body) >= 50:
            chunks.append({"text": body, "paragraph": "n/a", "doc_id": doc_id})
    return chunks


def chunk_document(text: str, doc_id: str) -> list[dict]:
    chunks = chunk_by_pattern(text, doc_id)
    if not chunks:
        print(f"  (no paragraph pattern matched, using sliding window)")
        chunks = fallback_chunk(text, doc_id)
    # Enforce embedder context limit
    safe_chunks = []
    for c in chunks:
        safe_chunks.extend(split_oversized(c))
    return safe_chunks


def doc_id_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 2 and parts[0] == "AR":
        return f"AR {parts[1]}"
    if "ar670" in stem.lower():
        return "AR 670-1"
    return stem


def main() -> int:
    pdfs = sorted(REGS_DIR.glob("*.pdf"))
    if not pdfs:
        print("No PDFs in corpus/regs/.", file=sys.stderr)
        return 1

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    total = 0
    for pdf in pdfs:
        doc_id = doc_id_from_filename(pdf.name)
        print(f"\nIndexing {doc_id} ({pdf.name})")
        text = extract_text(pdf)
        print(f"  text length: {len(text):,} chars")
        chunks = chunk_document(text, doc_id)
        print(f"  → {len(chunks)} chunks (avg {sum(len(c['text']) for c in chunks)//max(len(chunks),1)} chars each)")

        for i, chunk in enumerate(tqdm(chunks, desc="  embedding")):
            try:
                resp = ollama.embeddings(model=EMBED_MODEL, prompt=chunk["text"])
            except Exception as e:
                print(f"\n  ⚠ skipped chunk {i} ({len(chunk['text'])} chars): {e}")
                continue
            collection.add(
                ids=[f"{doc_id}::{i}"],
                embeddings=[resp["embedding"]],
                documents=[chunk["text"]],
                metadatas=[{"doc_id": chunk["doc_id"], "paragraph": chunk["paragraph"]}],
            )
        total += len(chunks)

    print(f"\n✓ Indexed {total} chunks across {len(pdfs)} documents.")
    return 0


if __name__ == "__main__":
    sys.exit(main())