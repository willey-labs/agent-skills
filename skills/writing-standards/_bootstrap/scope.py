#!/usr/bin/env python3
"""Install-scope detection.

Decides whether the skill is installed globally (`~/.claude`) or in a project
(`<project>/.claude`), based on where this file's symlink lives, and returns the
settings.json to wire. Trimmed copy of coding-standards' scope.py — same anchor
logic, without the ignore-file template.
"""

from __future__ import annotations

import os
from pathlib import Path

from .paths import SCRIPT_PATH, SKILL_DIR


def detect_scope_and_targets() -> tuple[str, Path]:
    """Return (scope, settings_json_path). scope is "global" or "project"."""
    home_claude = Path.home() / ".claude"

    # Global install: the skill's symlink lives under ~/.claude/skills/.
    if str(SCRIPT_PATH).startswith(str(home_claude) + os.sep):
        return "global", home_claude / "settings.json"

    # Project install: walk up for a `.claude` ancestor; its parent is the project.
    for parent in SCRIPT_PATH.parents:
        if parent.name == ".claude":
            return "project", parent / "settings.json"

    # Fallback: invocation path collapsed to its real target (no `.claude` ancestor).
    # If the GLOBAL skills dir points back at where we live, it's a global install.
    # Project scope can't be recovered this way — a shared copy may be symlinked from
    # many projects, so the invocation path is the only disambiguator.
    home_skill = home_claude / "skills" / SKILL_DIR.name
    try:
        if home_skill.exists() and os.path.realpath(home_skill) == os.path.realpath(SKILL_DIR):
            return "global", home_claude / "settings.json"
    except OSError:
        pass  # unreadable symlink — fall through to the refuse-to-guess error below

    raise SystemExit(
        "bootstrap: cannot determine install scope. This script must be invoked\n"
        "through a `.claude/skills/writing-standards/bootstrap.py` symlink (project\n"
        f"or global). Got: {SCRIPT_PATH}\n"
        "Install via `npx skills add willey-labs/agent-skills` and try again."
    )
