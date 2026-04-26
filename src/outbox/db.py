"""Local outbox database. Forms queue here while offline, drain when online."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "outbox.db"


class Priority(str, Enum):
    URGENT = "URGENT"      # casualty reports, emergency leave
    ROUTINE = "ROUTINE"    # ordinary leave, training requests
    LOW = "LOW"            # uniform inquiries, general admin


class Status(str, Enum):
    PENDING = "PENDING"    # waiting to sync
    SENT = "SENT"          # successfully synced
    FAILED = "FAILED"      # sync attempted, failed (would retry)


@dataclass
class OutboxItem:
    id: int
    form_type: str         # e.g., "DA-31"
    file_path: str
    summary: str           # one-line description for the queue display
    priority: Priority
    status: Status
    created_at: datetime
    sent_at: datetime | None


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the outbox table if it doesn't exist. Idempotent."""
    with connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                form_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                summary TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                sent_at TEXT
            )
        """)


def enqueue(form_type: str, file_path: str, summary: str,
            priority: Priority = Priority.ROUTINE) -> int:
    """Add a form to the outbox. Returns the new row's id."""
    init_db()
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO outbox (form_type, file_path, summary, priority, status, created_at)
               VALUES (?, ?, ?, ?, 'PENDING', ?)""",
            (form_type, file_path, summary, priority.value, datetime.now().isoformat()),
        )
        return cur.lastrowid


def list_pending() -> list[OutboxItem]:
    """Return pending items, URGENT first, then by creation time."""
    init_db()
    priority_order = "CASE priority WHEN 'URGENT' THEN 0 WHEN 'ROUTINE' THEN 1 ELSE 2 END"
    with connect() as conn:
        rows = conn.execute(
            f"""SELECT * FROM outbox WHERE status = 'PENDING'
                ORDER BY {priority_order}, created_at ASC"""
        ).fetchall()
    return [_row_to_item(r) for r in rows]


def list_all() -> list[OutboxItem]:
    init_db()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM outbox ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_item(r) for r in rows]


def mark_sent(item_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE outbox SET status = 'SENT', sent_at = ? WHERE id = ?",
            (datetime.now().isoformat(), item_id),
        )


def _row_to_item(row: sqlite3.Row) -> OutboxItem:
    return OutboxItem(
        id=row["id"],
        form_type=row["form_type"],
        file_path=row["file_path"],
        summary=row["summary"],
        priority=Priority(row["priority"]),
        status=Status(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        sent_at=datetime.fromisoformat(row["sent_at"]) if row["sent_at"] else None,
    )