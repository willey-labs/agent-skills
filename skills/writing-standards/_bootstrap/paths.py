#!/usr/bin/env python3
"""Filesystem paths shared across the _bootstrap package, anchored to the skill ROOT (one level above this package, the dir holding bootstrap.py).

Uses `.absolute()`, not `.resolve()`, and anchors to the MAIN script's invocation path rather than this module's own `__file__`: Python resolves symlinks for an imported module's `__file__` but preserves them for the main script's, and the skill is symlinked into `~/.claude/skills/<name>/` or `<project>/.claude/skills/<name>/` — resolving the symlink lands on the canonical install path, which has no `.claude` ancestor, and breaks scope detection. (Same constraint as coding-standards' _bootstrap/paths.py; this copy omits the venv helpers.)

Every path that reaches a settings.json hook command goes through `command_path` first: forward slashes avoid Git Bash on Windows mangling backslash-escaped paths, and `shell_quote` wraps any part containing a space or a `${...}` placeholder so the shell doesn't split it into two arguments.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _invocation_path() -> Path:
    """The path bootstrap was started with, kept symlink-preserving.

    Anchors on `sys.argv[0]` (the path as typed), falling back to
    `__main__.__file__`. Absolute arg → use it verbatim. Relative arg → resolving
    via `os.getcwd()` drops the `.claude` shortcut, so prefer the shell's logical
    `$PWD` when it points at the same real file (guards a stale $PWD).
    """
    main = sys.modules.get("__main__")
    raw = sys.argv[0] or getattr(main, "__file__", None) or "bootstrap.py"
    path = Path(raw)
    if path.is_absolute():
        return path
    physical = Path(os.getcwd()) / raw
    pwd = os.environ.get("PWD")
    if pwd:
        logical = Path(pwd) / raw
        try:
            if logical.exists() and os.path.realpath(logical) == os.path.realpath(physical):
                return logical
        except OSError:
            return physical  # stale/unreadable $PWD — fall through to the physical path
    return physical


# The invoked bootstrap.py path, symlink-preserving — the anchor whose parents
# scope detection walks for `.claude`.
SCRIPT_PATH = _invocation_path().absolute()
# The skill root (bootstrap.py's directory), as seen through the install symlink.
SKILL_DIR = SCRIPT_PATH.parent
# Hooks dir resolved to its real location so settings.json command paths work from any cwd.
HOOKS_DIR = (SKILL_DIR / "hooks").resolve()


def command_path(path: Path | str) -> str:
    """A path bound for a shell command string — forward slashes only."""
    return str(path).replace("\\", "/")


def shell_quote(part: str) -> str:
    """Double quotes, never single: a `${...}` inside the part must still expand."""
    return f'"{part}"' if " " in part or "${" in part else part
