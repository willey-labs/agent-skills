#!/usr/bin/env python3
"""Filesystem paths shared across the _bootstrap package.

All anchored to the skill ROOT — the directory holding the `bootstrap.py` entry
script (one level ABOVE this package). Uses `.absolute()` not `.resolve()` — the
skill is symlinked from a canonical install location into
`~/.claude/skills/<name>/` or `<project>/.claude/skills/<name>/`. Resolving the
symlink lands on the canonical path, which has no `.claude` ancestor, breaking
scope detection; we need the path as the agent sees it, through the symlink.

CRITICAL: we anchor to the MAIN script's `__file__` (`bootstrap.py`), NOT this
module's own. Python preserves the symlinked path for the main script's
`__file__`, but RESOLVES the symlink for an imported module's `__file__` — which
would land on the canonical install path (no `.claude` ancestor) and break scope
detection. `sys.argv[0]` is the fallback when `__main__.__file__` is absent
(e.g. an embedded interpreter). Both point at `bootstrap.py` as invoked.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _invocation_path() -> Path:
    """The path bootstrap was started with, kept symlink-preserving.

    Scope detection needs the path as invoked — through the `.claude/...`
    shortcut — not its resolved target. We anchor on `sys.argv[0]` (the path
    exactly as typed), NOT `__main__.__file__`: Python sets `__file__` to
    `abspath(argv[0])`, and for a relative arg that goes through the
    symlink-RESOLVED `os.getcwd()`, so `__file__` already points at the real
    `.agents/...` target — useless for preserving the shortcut. Two cases:

    - Full path (`python3 /…/.claude/skills/…/bootstrap.py`): argv[0] is absolute
      and keeps the shortcut name verbatim — use it.
    - Relative (`cd /…/.claude/skills/… && python3 bootstrap.py`): argv[0] is
      just `bootstrap.py`; resolving it via `os.getcwd()` drops the `.claude`
      name, but the shell's logical `$PWD` still holds it — use `$PWD` WHEN it
      points at the same real file (guards a stale $PWD).
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
            pass
    return physical


# The invoked bootstrap.py path, symlink-preserving — the anchor whose parents
# scope detection walks for `.claude`.
SCRIPT_PATH = _invocation_path().absolute()
# The skill root (bootstrap.py's directory), as seen through the install symlink.
SKILL_DIR = SCRIPT_PATH.parent
# Hooks dir resolved to its real location so the command paths in settings.json
# work from any cwd.
HOOKS_DIR = (SKILL_DIR / "hooks").resolve()


def _managed_venv_dir() -> Path:
    """Where the dedicated coding-standards venv lives.

    OUTSIDE the skill dir, deliberately (ISS-006): the venv used to sit at
    `<skill>/.venv`, but `npx skills add` (the documented update path) re-copies
    the whole skill tree and WIPES it — after which every hook command's
    interpreter is missing and the hooks exit 127 silently, never blocking. A
    stable per-user data dir survives skill re-copies. Resolution order:
      1. $CODING_STANDARDS_VENV — explicit override (also used by the test sandbox)
      2. $XDG_DATA_HOME/coding-standards/venv
      3. ~/.local/share/coding-standards/venv
      4. (last resort, HOME undeterminable) the old in-skill location
    """
    override = os.environ.get("CODING_STANDARDS_VENV")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "coding-standards" / "venv"
    try:
        return Path.home() / ".local" / "share" / "coding-standards" / "venv"
    except RuntimeError:
        return HOOKS_DIR.parent / ".venv"


# The dedicated venv: default for GLOBAL installs (so the hooks don't depend on
# whatever python3 is first on PATH) and the fallback when the system Python is
# externally-managed (PEP 668). A wiped venv is rebuilt by the next bootstrap and
# announced by the SessionStart health check, never failing silently.
MANAGED_VENV_DIR = _managed_venv_dir()
