"""Sync engine: drains the outbox to the dispatch folder.

The watcher daemon (scripts/dispatch_watcher.py) picks files up from
data/dispatch/ and emails them. Decoupled by design — the CLI demo
works whether or not the watcher is running.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Iterator

from . import db
from .connectivity import is_online

DISPATCH_DIR = Path(__file__).resolve().parents[2] / "data" / "dispatch"


class SyncError(Exception):
    pass


def sync_all() -> Iterator[db.OutboxItem]:
    if not is_online():
        raise SyncError("No connectivity — reconnect to the network first.")

    DISPATCH_DIR.mkdir(parents=True, exist_ok=True)
    pending = db.list_pending()

    for item in pending:
        delay = 0.4 if item.priority == db.Priority.URGENT else 0.9
        time.sleep(delay)

        src = Path(item.file_path)
        if src.exists():
            # Drop into dispatch with a sortable name so the watcher
            # can prioritize urgent items if it wants to.
            prefix = "0_URGENT" if item.priority == db.Priority.URGENT else "1_ROUTINE"
            dest = DISPATCH_DIR / f"{prefix}__{item.id}__{src.name}"
            shutil.copy2(src, dest)

        db.mark_sent(item.id)
        yield item