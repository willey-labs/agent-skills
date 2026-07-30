#!/usr/bin/env python3
"""Per-session record of the source files a turn wrote.

`record-touched-files.py` appends to it on every Write/Edit; `judge-comments.py`
drains it when the turn tries to end, so the judge reads exactly the files this
turn touched instead of parsing the transcript (which the hook docs warn lags the
live conversation).

The ledger lives outside every project — a session writes into the user's data dir,
never into the repo under review. A round counter sits beside it so a judge that
keeps disagreeing with the author cannot trap a session in a loop.

Stdlib only.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_SAFE_KEY = re.compile(r"[^A-Za-z0-9_.-]")


def ledger_dir() -> Path:
    """The directory holding every session's ledger."""
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "coding-standards" / "touched"


def session_key(payload: dict) -> str:
    """A filesystem-safe key for this session, from whichever identifier the hook
    event carried."""
    raw = payload.get("session_id") or Path(payload.get("transcript_path") or "").stem or "default"
    return _SAFE_KEY.sub("_", str(raw))[:120]


def _ledger_path(key: str) -> Path:
    return ledger_dir() / f"{key}.paths"


def _rounds_path(key: str) -> Path:
    return ledger_dir() / f"{key}.rounds"


def record(key: str, file_path: str) -> None:
    """Append one written file to this session's ledger."""
    path = _ledger_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{file_path}\n")


def drain(key: str) -> list[str]:
    """Every distinct file recorded this session, clearing the ledger."""
    path = _ledger_path(key)
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    path.unlink(missing_ok=True)
    seen: dict[str, None] = {}
    for line in lines:
        candidate = line.strip()
        if candidate:
            seen.setdefault(candidate, None)
    return list(seen)


def rounds_spent(key: str) -> int:
    """How many times this session has already been held open over comments."""
    path = _rounds_path(key)
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip() or "0")
    except ValueError:
        return 0


def spend_round(key: str) -> int:
    """Count one more hold-open for this session and return the new total."""
    path = _rounds_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    total = rounds_spent(key) + 1
    path.write_text(f"{total}\n", encoding="utf-8")
    return total
