"""Extract a structured LeaveRequest from natural language using local LLM."""

from __future__ import annotations

import json
from datetime import date

import ollama
from pydantic import ValidationError

from .schema import LeaveRequest

GEN_MODEL = "llama3.1:8b"

EXTRACTION_PROMPT = """You convert natural-language Army leave requests into structured JSON.

Output ONLY a JSON object matching this schema (no markdown, no commentary):

{{
  "name": "LAST, FIRST MI",
  "rank": "SPC",
  "ssn": "XXX-XX-XXXX",
  "org_station": "Unit, station, phone",
  "leave_address": "address during leave",
  "leave_type": "ORDINARY",
  "days_requested": 10,
  "days_accrued": 15.0,
  "date_from": "YYYY-MM-DD",
  "date_to": "YYYY-MM-DD",
  "control_number": ""
}}

Rules:
- Today is {today}. Resolve relative dates against today.
- leave_type must be one of: ORDINARY, EMERGENCY, PERMISSIVE_TDY, OTHER. Default ORDINARY.
- If days_requested is given but date_to is not, set date_to = date_from + (days_requested - 1).
- Convert names like "John Smith" to "SMITH, JOHN".
- Use realistic placeholders if fields aren't specified."""


def extract(natural_language: str, soldier_defaults: dict | None = None) -> LeaveRequest:
    defaults = soldier_defaults or {}
    today = date.today().isoformat()

    system = EXTRACTION_PROMPT.format(today=today)
    user = (
        f"Soldier defaults (use unless overridden): {json.dumps(defaults)}\n\n"
        f"Leave request: {natural_language}\n\n"
        f"Output the JSON object now."
    )

    resp = ollama.chat(
        model=GEN_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        format="json",
        options={"temperature": 0.1},
    )

    raw = resp["message"]["content"].strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON:\n{raw}\n\nError: {e}")

    try:
        return LeaveRequest(**data)
    except ValidationError as e:
        raise ValueError(f"LLM JSON failed validation:\n{json.dumps(data, indent=2)}\n\n{e}")