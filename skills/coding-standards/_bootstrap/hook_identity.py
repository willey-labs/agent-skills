#!/usr/bin/env python3
"""Recognizing this skill's own settings.json entries on a re-run.

An entry belongs to us when every command in it runs one of our scripts. Matching on
basenames rather than a `coding-standards/hooks/` substring matters because a global
install's command path is the RESOLVED canonical install dir, which (when the skill is
symlinked from e.g. an npm cache) may not contain the string `coding-standards` at
all. A recognized entry is replaced on re-run; every unrelated entry is left alone.

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
