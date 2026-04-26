"""Smoke test for the RAG pipeline.

Runs three hardcoded queries end-to-end: retrieve from Chroma, generate with
Llama, print the answer with citations. If this prints sane answers, the
AI half of your demo works.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import chromadb
import ollama

ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = ROOT / "data" / "chroma"
COLLECTION_NAME = "army_regs"
EMBED_MODEL = "nomic-embed-text"
GEN_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are an offline assistant for U.S. Army service members. \
Answer questions using ONLY the provided context.

CITATION RULE: Each context block is tagged with a document (e.g., "AR 600-8-10"). \
The block's text contains specific paragraph identifiers like "2-3a." or "10-4a(1)." \
at the start of paragraphs. Cite the MOST SPECIFIC paragraph identifier you can find \
in the chunk text — for example "AR 600-8-10, Para 2-3a(1)" — NOT the chapter number. \
If the chunk text doesn't contain a clear paragraph identifier, cite just the document.

If the context does not contain the answer, say so explicitly. Keep answers under 150 words."""


@dataclass
class RetrievedChunk:
    text: str
    doc_id: str
    paragraph: str
    distance: float

    @property
    def citation(self) -> str:
        if self.paragraph and self.paragraph not in ("n/a", "semantic"):
            return f"{self.doc_id}, Para {self.paragraph}"
        return self.doc_id


def retrieve(query: str, k: int = 4) -> list[RetrievedChunk]:
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_collection(COLLECTION_NAME)

    embedding = ollama.embeddings(model=EMBED_MODEL, prompt=query)["embedding"]
    results = collection.query(query_embeddings=[embedding], n_results=k)

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        chunks.append(
            RetrievedChunk(
                text=doc,
                doc_id=meta.get("doc_id", "unknown"),
                paragraph=meta.get("paragraph", "n/a"),
                distance=dist,
            )
        )
    return chunks


def answer(query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant regulations found."

    context = "\n\n---\n\n".join(f"[{c.citation}]\n{c.text}" for c in chunks)
    user_prompt = (
        f"Context from Army Regulations:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer concisely and cite the most specific paragraph identifier you can find in the context."
    )

    resp = ollama.chat(
        model=GEN_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": 0.2},
    )
    return resp["message"]["content"].strip()


def run_query(query: str) -> None:
    print(f"\n{'='*70}")
    print(f"Q: {query}")
    print(f"{'='*70}")

    chunks = retrieve(query, k=4)
    print(f"\nRetrieved {len(chunks)} chunks:")
    for c in chunks:
        print(f"  • {c.citation}  (distance={c.distance:.3f})")

    print(f"\nAnswer:\n")
    print(answer(query, chunks))


if __name__ == "__main__":
    queries = [
        "How is ordinary leave accrued? How many days per month?",
        "What are the rules for leave extensions?",
        "How many days notice is required to request a leave extension?",
    ]
    for q in queries:
        run_query(q)