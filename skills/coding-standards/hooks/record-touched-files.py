#!/usr/bin/env python3
"""PostToolUse hook — remember which source files this turn wrote.

The comment judge runs when a turn tries to end and needs the list of files it
should look at. This records each one as it is written, which is cheaper and more
exact than reading the transcript back (the hook docs warn the transcript file lags
the live conversation).

Excluded and generated files are skipped here, so the judge never spends a model
call on code the standard doesn't govern.

Stdlib only. Exit 0 always — a bookkeeping hook must never interrupt a write that
already succeeded.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import has_generation_marker, is_excluded_path  # noqa: E402
from _hook_run import read_payload  # noqa: E402
from _languages import SOURCE_EXTENSIONS  # noqa: E402
from _touched_ledger import record, session_key  # noqa: E402


def target_of(payload: dict) -> str | None:
    """The written source file worth judging, or None."""
    if payload.get("tool_name") not in {"Write", "Edit", "MultiEdit"}:
        return None
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not file_path or Path(file_path).suffix not in SOURCE_EXTENSIONS:
        return None
    excluded, _pattern = is_excluded_path(file_path)
    if excluded:
        return None
    try:
        if has_generation_marker(Path(file_path).read_text(encoding="utf-8")):
            return None
    except (OSError, UnicodeDecodeError):
        return None
    return file_path


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    file_path = target_of(payload)
    if file_path:
        record(session_key(payload), file_path)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: record-touched-files skipped ({exc})\n")
        sys.exit(0)
