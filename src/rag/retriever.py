"""Offline retrieval over indexed Army regulations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import chromadb
import ollama

CHROMA_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma"
COLLECTION_NAME = "army_regs"
EMBED_MODEL = "nomic-embed-text"


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


class Retriever:
    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = client.get_collection(COLLECTION_NAME)

    def search(self, query: str, k: int = 4) -> list[RetrievedChunk]:
        embedding = ollama.embeddings(model=EMBED_MODEL, prompt=query)["embedding"]
        results = self.collection.query(query_embeddings=[embedding], n_results=k)

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        ):
            chunks.append(RetrievedChunk(
                text=doc,
                doc_id=meta.get("doc_id", "unknown"),
                paragraph=meta.get("paragraph", "n/a"),
                distance=dist,
            ))
        return chunks