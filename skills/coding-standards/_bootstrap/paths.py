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

import sys
from pathlib import Path

_main = sys.modules.get("__main__")
_anchor = getattr(_main, "__file__", None) or sys.argv[0]
# The invoked bootstrap.py path, symlink-preserving — the anchor whose parents
# we walk for `.claude` during scope detection.
SCRIPT_PATH = Path(_anchor).absolute()
# The skill root (bootstrap.py's directory), as seen through the install symlink.
SKILL_DIR = SCRIPT_PATH.parent
# Hooks dir resolved to its real location so the command paths in settings.json
# work from any cwd.
HOOKS_DIR = (SKILL_DIR / "hooks").resolve()
# The dedicated coding-standards venv lives HERE — beside the hooks. It's the
# default for GLOBAL installs (so the hooks don't depend on whatever python3 is
# first on PATH) and the fallback when the system Python is externally-managed
# (PEP 668). Co-located with the skill: reinstalling the skill and re-running
# bootstrap recreates it.
MANAGED_VENV_DIR = HOOKS_DIR.parent / ".venv"
