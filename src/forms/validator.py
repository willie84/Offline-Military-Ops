"""Regulation-aware compliance validation for leave requests.

Runs RAG against the indexed Army regs to find the rules governing
the request, then asks the LLM to judge compliance. Returns a
structured ValidationResult so the CLI can show approve/warn/deny
with a regulation citation.
"""

from __future__ import annotations

import json
from typing import Literal

import ollama
from pydantic import BaseModel, Field, ValidationError

from src.rag.retriever import Retriever
from .schema import LeaveRequest

GEN_MODEL = "llama3.1:8b"

Verdict = Literal["APPROVE", "WARN", "DENY"]


class ValidationResult(BaseModel):
    verdict: Verdict
    reason: str = Field(..., description="Plain-English explanation, 1-2 sentences max")
    citation: str = Field(default="", description="Specific paragraph cited, e.g. 'AR 600-8-10, Para 2-3a(1)'")


VALIDATION_PROMPT = """You are a compliance checker for U.S. Army leave requests.

A soldier has submitted this leave request:
{request_summary}

The relevant Army regulation excerpts are below. Cite them by their exact paragraph identifiers \
when explaining your verdict.
{context}

Decide one verdict:
- APPROVE: the request is fully compliant with the rules in the context.
- WARN: the request is technically allowed but unusual or close to a limit (e.g., uses most of accrued balance).
- DENY: the request violates a rule in the context (e.g., requests more days than accrued without invoking advance leave).

Output ONLY a JSON object:

{{
  "verdict": "APPROVE" | "WARN" | "DENY",
  "reason": "1-2 sentence plain English explanation",
  "citation": "AR XXX-X-XX, Para X-Xa"
}}

Be strict. If a rule is violated, DENY. If you can't find the relevant rule in the context, APPROVE \
with a note that no relevant constraint was found.
"""


def _summarize_request(req: LeaveRequest) -> str:
    """Human-readable summary the LLM can reason about."""
    return (
        f"Soldier: {req.name} ({req.rank})\n"
        f"Type: {req.leave_type}\n"
        f"Days requested: {req.days_requested}\n"
        f"Days currently accrued: {req.days_accrued}\n"
        f"Dates: {req.date_from} to {req.date_to}\n"
    )


def _build_query(req: LeaveRequest) -> str:
    """Query the regs for the rules most likely to apply to this request."""
    parts = [f"{req.leave_type.lower()} leave accrual"]
    if req.days_requested > req.days_accrued:
        parts.append("advance leave authorization")
    if req.leave_type == "EMERGENCY":
        parts.append("emergency leave rules")
    if req.days_requested > 30:
        parts.append("excess leave maximum")
    return " ".join(parts)


def validate(req: LeaveRequest, retriever: Retriever | None = None) -> ValidationResult:
    """Validate a leave request against the indexed regulations."""
    retriever = retriever or Retriever()

    # Pull the rules most relevant to this request
    chunks = retriever.search(_build_query(req), k=4)
    if not chunks:
        return ValidationResult(
            verdict="APPROVE",
            reason="No relevant regulation excerpt found; defaulting to approve.",
            citation="",
        )

    context = "\n\n---\n\n".join(f"[{c.citation}]\n{c.text}" for c in chunks)
    prompt = VALIDATION_PROMPT.format(
        request_summary=_summarize_request(req),
        context=context,
    )

    resp = ollama.chat(
        model=GEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
        format="json",
        options={"temperature": 0.1},
    )

    raw = resp["message"]["content"].strip()
    try:
        data = json.loads(raw)
        return ValidationResult(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        # Fail open with a clear note rather than crashing the demo
        return ValidationResult(
            verdict="WARN",
            reason=f"Validator could not parse a verdict; defaulting to warn. ({e})",
            citation="",
        )