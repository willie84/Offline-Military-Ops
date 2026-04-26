"""Fake connectivity state for the demo.

Real DDIL detection would probe the network. For the hackathon demo,
we toggle a flag file. `oo offline` / `oo online` flip it; the sync
engine reads it before attempting to drain the outbox.
"""

from pathlib import Path

FLAG_FILE = Path(__file__).resolve().parents[2] / "data" / ".offline_mode"


def is_online() -> bool:
    """True if we're currently 'online' (no flag file present)."""
    return not FLAG_FILE.exists()


def go_offline() -> None:
    FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    FLAG_FILE.touch()


def go_online() -> None:
    if FLAG_FILE.exists():
        FLAG_FILE.unlink()