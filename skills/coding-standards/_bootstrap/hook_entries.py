#!/usr/bin/env python3
"""Building the settings.json entry for each event this skill wires.

One builder per event. Which scripts go in which entry comes from
`hook_registry.py`; recognizing our own entry on re-run is `hook_identity.py`;
reading, merging and writing settings.json is `settings.py` (ST-008: one job per
file).

Stdlib only.
"""

from __future__ import annotations

from .hook_registry import (
    EVENT_INTERPRETER,
    HOOK_FILES,
    POST_TOOL_USE_FILES,
    SESSION_START_FILES,
    SESSION_START_MATCHER,
    STOP_FILES,
    USER_PROMPT_SUBMIT_FILES,
    WRITE_MATCHER,
)
from .paths import HOOKS_DIR, command_path


def path_prefix(scope: str) -> str:
    """Where wired commands point: a `${CLAUDE_PROJECT_DIR}` path for a project
    install, so the entry survives moving the project (Claude Code expands the
    variable); the resolved hooks dir for a global one."""
    if scope == "project":
        return "${CLAUDE_PROJECT_DIR}/.claude/skills/coding-standards/hooks"
    return command_path(HOOKS_DIR)


def _commands(scope: str, interpreter: str, names: list[str]) -> list[dict]:
    prefix = path_prefix(scope)
    return [{"type": "command", "command": f"{interpreter} {prefix}/{name}"} for name in names]


def build_hook_entry(scope: str, hook_python: str) -> dict:
    """The PreToolUse entry that activates every content and path hook.

    The matcher includes `MultiEdit` for backward compatibility with older Claude
    Code versions that still expose it; on current versions it harmlessly never
    matches.
    """
    return {"matcher": WRITE_MATCHER, "hooks": _commands(scope, hook_python, HOOK_FILES)}


def build_session_start_entry(scope: str) -> dict:
    """The SessionStart entry: the enforcement health check, then the rule reminder.

    Uses the SAME path prefix as the PreToolUse hooks so scope detection inside the
    spawned `bootstrap.py --verify` works. See SessionStart hook docs: stdout →
    Claude context, exit 2 → stderr to user, never blocks.
    """
    return {
        "matcher": SESSION_START_MATCHER,
        "hooks": _commands(scope, EVENT_INTERPRETER, SESSION_START_FILES),
    }


def build_user_prompt_submit_entry(scope: str) -> dict:
    """The UserPromptSubmit entry that re-injects the rule reminder each turn.

    UserPromptSubmit takes no matcher. A non-zero exit here blocks the user's prompt,
    which is why the injected script never returns one.
    """
    return {"hooks": _commands(scope, EVENT_INTERPRETER, USER_PROMPT_SUBMIT_FILES)}


def build_post_tool_use_entry(scope: str) -> dict:
    """The PostToolUse entry that records the source files a turn wrote."""
    return {
        "matcher": WRITE_MATCHER,
        "hooks": _commands(scope, EVENT_INTERPRETER, POST_TOOL_USE_FILES),
    }


def build_stop_entry(scope: str) -> dict:
    """The Stop entry that runs the comment judge.

    Stop takes no matcher: the entry is the bare `hooks` list. Verified against a
    live session — a matcher-shaped entry does not fire.
    """
    return {"hooks": _commands(scope, EVENT_INTERPRETER, STOP_FILES)}
