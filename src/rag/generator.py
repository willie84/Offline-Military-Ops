"""Generation step: cited answers from retrieved chunks."""

from __future__ import annotations

import ollama

from .retriever import RetrievedChunk

GEN_MODEL = "llama3.1:8b"

SYSTEM_PROMPT = """You are an offline assistant for U.S. Army service members. \
Answer questions using ONLY the provided context.

CITATION RULE: Each context block is tagged with a document (e.g., "AR 600-8-10"). \
The block's text contains specific paragraph identifiers like "2-3a." or "10-4a(1)." \
at the start of paragraphs. Cite the MOST SPECIFIC paragraph identifier you can find \
in the chunk text — for example "AR 600-8-10, Para 2-3a(1)" — NOT the chapter number. \
If the chunk text doesn't contain a clear paragraph identifier, cite just the document.

If the context does not contain the answer, say so. Keep answers under 150 words."""


def answer(query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant regulations found in the local index."

    context = "\n\n---\n\n".join(f"[{c.citation}]\n{c.text}" for c in chunks)
    user_prompt = (
        f"Context from Army Regulations:\n\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer concisely and cite the most specific paragraph identifier in the context."
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