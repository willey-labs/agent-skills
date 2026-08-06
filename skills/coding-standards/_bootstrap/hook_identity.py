#!/usr/bin/env python3
"""Recognizing this skill's own settings.json entries, and what the wiring is missing.

An entry belongs to us when every command in it runs one of our scripts. Matching on
basenames rather than a `coding-standards/hooks/` substring matters because a global
install's command path is the RESOLVED canonical install dir, which (when the skill is
symlinked from e.g. an npm cache) may not contain the string `coding-standards` at
all. A recognized entry is replaced on re-run; every unrelated entry is left alone.

Completeness is the other question, and it is asked against the registry rather than
against our entries: a settings.json wired by an older version satisfies every
recognizer while running none of the scripts added since, so an install that is
merely stale looks identical to one that is current.

Stdlib only.
"""

from __future__ import annotations

from .hook_registry import (
    HOOK_FILES,
    POST_TOOL_USE_FILES,
    RETIRED_HOOK_FILES,
    SESSION_START_FILES,
    STOP_FILES,
    USER_PROMPT_SUBMIT_FILES,
)

HOOK_FILES_BY_EVENT = {
    "PreToolUse": HOOK_FILES,
    "PostToolUse": POST_TOOL_USE_FILES,
    "Stop": STOP_FILES,
    "SessionStart": SESSION_START_FILES,
    "UserPromptSubmit": USER_PROMPT_SUBMIT_FILES,
}


def _runs_only(entry: dict, names: list[str]) -> bool:
    """True when every command in `entry` runs one of `names`."""
    hooks = entry.get("hooks") or []
    if not hooks:
        return False
    return all(any(name in (hook or {}).get("command", "") for name in names) for hook in hooks)


def is_our_entry(entry: dict) -> bool:
    """A PreToolUse entry of ours — retired basenames included, so an upgrade
    replaces an older block instead of appending a duplicate."""
    return _runs_only(entry, HOOK_FILES + RETIRED_HOOK_FILES)


def is_our_session_entry(entry: dict) -> bool:
    """A SessionStart entry of ours: every command runs the health check or the
    reminder. An entry wired before the reminder shipped carries only the health check
    and is still recognized, so an upgrade replaces it instead of appending a copy."""
    return _runs_only(entry, SESSION_START_FILES)


def is_our_user_prompt_submit_entry(entry: dict) -> bool:
    """A UserPromptSubmit entry of ours: every command runs the reminder."""
    return _runs_only(entry, USER_PROMPT_SUBMIT_FILES)


def is_our_post_tool_use_entry(entry: dict) -> bool:
    """A PostToolUse entry of ours: every command runs the recorder."""
    return _runs_only(entry, POST_TOOL_USE_FILES)


def is_our_stop_entry(entry: dict) -> bool:
    """A Stop entry of ours: every command runs the comment judge."""
    return _runs_only(entry, STOP_FILES)


def _commands_under(entries: object) -> list[str]:
    """Every hook command wired under one event, whoever's entry it sits in."""
    if not isinstance(entries, list):
        return []
    return [
        (hook or {}).get("command", "")
        for entry in entries
        if isinstance(entry, dict)
        for hook in entry.get("hooks") or []
    ]


def missing_wired_scripts(settings: dict) -> list[str]:
    """Registry scripts that no command in `settings` runs, as `event: script`."""
    hooks = settings.get("hooks") if isinstance(settings, dict) else None
    absent: list[str] = []
    for event, names in HOOK_FILES_BY_EVENT.items():
        commands = _commands_under(hooks.get(event) if isinstance(hooks, dict) else None)
        absent.extend(
            f"{event}: {name}"
            for name in names
            if not any(name in command for command in commands)
        )
    return absent
