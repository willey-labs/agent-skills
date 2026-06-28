#!/usr/bin/env python3
"""Wire the reminder hook into settings.json.

Owns the SessionStart + UserPromptSubmit hook entries (build, recognize, merge)
and the settings.json read/write with a rolling backup. Both events run the SAME
script (inject-writing-standards.py), so one `is_our_entry` recognizes our block
in either section without disturbing unrelated hooks the user has configured.

The hook is stdlib-only, so the interpreter is a plain `python3` — no venv, unlike
coding-standards (which needs tree-sitter).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .paths import HOOKS_DIR

INJECT_SCRIPT = "inject-writing-standards.py"
INTERPRETER = "python3"
SESSION_START_MATCHER = "startup"


def _command(scope: str) -> str:
    """The hook command for this scope. Project scope uses `${CLAUDE_PROJECT_DIR}`
    (Claude Code expands it, so the entry survives moving the project); global scope
    uses the resolved hooks dir so the command works from any cwd."""
    if scope == "project":
        prefix = "${CLAUDE_PROJECT_DIR}/.claude/skills/writing-standards/hooks"
    else:
        prefix = str(HOOKS_DIR)
    return f"{INTERPRETER} {prefix}/{INJECT_SCRIPT}"


def build_session_start_entry(scope: str) -> dict:
    """SessionStart entry — matcher `startup` (verified matcher value for a new
    session). stdout → Claude context; the reminder rides in at session boot."""
    return {
        "matcher": SESSION_START_MATCHER,
        "hooks": [{"type": "command", "command": _command(scope)}],
    }


def build_userprompt_entry(scope: str) -> dict:
    """UserPromptSubmit entry — no matcher (the event ignores one; it fires on
    every prompt). stdout → Claude context, so the reminder rides every turn."""
    return {"hooks": [{"type": "command", "command": _command(scope)}]}


def is_our_entry(entry: dict) -> bool:
    """An entry is ours if it has hooks and every command runs our inject script.
    Matches on the script basename (not a fixed dir substring) so a global install
    whose resolved path doesn't contain "writing-standards" is still recognized on
    re-run — otherwise re-runs would append a duplicate block each time."""
    hooks = entry.get("hooks") or []
    if not hooks:
        return False
    return all(INJECT_SCRIPT in (hook or {}).get("command", "") for hook in hooks)


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            f"bootstrap: cannot parse {path} as JSON ({exc}). "
            "Aborting to avoid corrupting your settings — wire the hooks manually."
        )
    if not isinstance(data, dict):
        raise SystemExit(f"bootstrap: {path} is not a JSON object. Aborting.")
    return data


def merge_entry(settings: dict, section: str, new_entry: dict) -> str:
    """Merge `new_entry` into `hooks.<section>` in place (creating `hooks` and the
    section if absent). Replaces our existing entry — dropping any duplicates — or
    appends; unrelated entries are untouched. Returns 'noop'|'added'|'updated'."""
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        hooks_section = {}
        settings["hooks"] = hooks_section
    entries = hooks_section.get(section)
    if not isinstance(entries, list):
        entries = []
        hooks_section[section] = entries

    ours = [i for i, entry in enumerate(entries) if isinstance(entry, dict) and is_our_entry(entry)]
    if ours:
        first = ours[0]
        previous = entries[first]
        entries[first] = new_entry
        for idx in reversed(ours[1:]):  # reverse keeps earlier indexes valid
            del entries[idx]
        return "noop" if previous == new_entry else "updated"
    entries.append(new_entry)
    return "added"


def write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        # Single rolling backup, not one .bak per run.
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
