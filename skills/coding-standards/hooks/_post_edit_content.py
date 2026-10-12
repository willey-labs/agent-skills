#!/usr/bin/env python3
"""The whole file as it will read after a Write, Edit or MultiEdit lands.

An Edit payload carries only the diff, so a whole-file check applies it to the file
on disk. When an `old_string` is missing the diff cannot be applied, and the caller
gets the on-disk content flagged as pre-edit rather than a guess.

Stdlib only.
"""

from __future__ import annotations

from pathlib import Path


def apply_edits(base: str, tool_input: dict[str, object]) -> tuple[str, bool]:
    """(post-edit text, True) — or False in place of True when any `old_string` was not found."""
    multi = tool_input.get("edits")
    edits = multi if isinstance(multi, list) else [tool_input]
    text = base
    applied = True
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        old = edit.get("old_string", "")
        new = edit.get("new_string", "")
        if not isinstance(old, str) or not isinstance(new, str) or old == "" or old not in text:
            applied = False
            continue
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text, applied


def resolve_content(payload: dict[str, object], file_path: str) -> tuple[str | None, bool]:
    """(content to check, whether it is the post-edit file); (None, False) when the file can't be read."""
    tool_input = payload.get("tool_input") or {}
    content = tool_input.get("content")
    if isinstance(content, str):
        return content, True
    try:
        base = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, False
    return apply_edits(base, tool_input)
