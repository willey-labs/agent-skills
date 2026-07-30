#!/usr/bin/env python3
"""Reading, merging and writing the agent's settings.json.

Merging is identical for every event: replace our own entry if one is there, drop any
duplicates of it, append if not, and leave every unrelated entry untouched. One
merge function per event names which recognizer identifies ours. Building the entries
is `hook_entries.py`; recognizing them is `hook_identity.py`; the script lists live in
`hook_registry.py`; interpreter choice is `interpreter.py`; the `/coding-standards`
slash-command install is `command.py` (ST-008: one job per file).

The registries and the health-check constants are re-exported here because callers and
tests have long imported them from this module.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .hook_identity import (
    is_our_entry,
    is_our_post_tool_use_entry,
    is_our_session_entry,
    is_our_stop_entry,
)
from .hook_registry import (  # noqa: F401  (re-exported for callers and tests)
    HOOK_FILES,
    POST_TOOL_USE_FILES,
    RETIRED_HOOK_FILES,
    SESSION_HEALTH_SCRIPT,
    SESSION_START_MATCHER,
    STOP_FILES,
)


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"bootstrap: cannot parse {path} as JSON ({e}). "
            f"Aborting to avoid corrupting your settings — paste the hooks block manually."
        )
    if not isinstance(data, dict):
        raise SystemExit(
            f"bootstrap: {path} is not a JSON object. "
            f"Aborting to avoid corrupting your settings."
        )
    return data


def _merge_entry(settings: dict, section: str, new_entry: dict, is_ours) -> str:
    """Merge `new_entry` into `hooks.<section>` in place (creating `hooks` and the
    section if absent). Replaces our existing entry — dropping any duplicates —
    or appends; unrelated entries are untouched. Returns 'noop'|'added'|'updated'.
    Shared by every event so they stay identical (DP-007)."""
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        hooks_section = {}
        settings["hooks"] = hooks_section
    entries = hooks_section.get(section)
    if not isinstance(entries, list):
        entries = []
        hooks_section[section] = entries

    existing_indexes = [
        i for i, entry in enumerate(entries) if isinstance(entry, dict) and is_ours(entry)
    ]
    if existing_indexes:
        first = existing_indexes[0]
        previous = entries[first]
        entries[first] = new_entry
        for idx in reversed(existing_indexes[1:]):  # reverse keeps indexes valid
            del entries[idx]
        return "noop" if previous == new_entry else "updated"
    entries.append(new_entry)
    return "added"


def merge_hook_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our PreToolUse entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "PreToolUse", new_entry, is_our_entry)


def merge_session_start_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our SessionStart entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "SessionStart", new_entry, is_our_session_entry)


def merge_post_tool_use_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our PostToolUse entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "PostToolUse", new_entry, is_our_post_tool_use_entry)


def merge_stop_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our Stop entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "Stop", new_entry, is_our_stop_entry)


def write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # Single rolling backup — overwrite, rather than accumulating one
        # timestamped .bak per run (which grew unbounded across re-installs).
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
