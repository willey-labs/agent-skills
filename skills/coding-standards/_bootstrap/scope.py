#!/usr/bin/env python3
"""Install-scope detection and project scaffolding.

Decides whether the skill is installed globally (`~/.claude`) or in a project
(`<project>/.claude`), based on where this file's symlink lives, and seeds the
discoverable `.coding-standards-ignore` template at the project root.
"""

from __future__ import annotations

import os
from pathlib import Path

from .paths import SCRIPT_PATH, SKILL_DIR

# Seeded at the project root on first bootstrap so users DISCOVER the feature —
# an absent file is invisible; people assume the skill can't be told to skip
# anything. Never overwrites an existing file. Patterns here add to the built-in
# defaults in hooks/_exclusions.py (they don't replace them).
IGNORE_FILENAME = ".coding-standards-ignore"
IGNORE_TEMPLATE = """\
# .coding-standards-ignore
#
# Files matched here are skipped by the coding-standards skill — both the
# write-time hooks and review mode. Gitignore-style patterns, one per line.
#
# You usually don't need this file. The skill already excludes node_modules,
# vendored deps, generated code, migrations, build output, and lock files by
# default (see hooks/_exclusions.py -> DEFAULT_EXCLUSIONS). Add a pattern below
# ONLY to skip something project-specific.
#
# Every pattern MUST carry a trailing `# reason: ...` — an exemption silences ALL
# checks for matching paths, so it has to justify itself (the write is blocked
# otherwise). Examples — uncomment and edit:
# src/legacy/**          # reason: pre-existing code you're not ready to clean up
# scripts/one-off-*.ts   # reason: throwaway scripts
# **/*.config.js         # reason: config files you don't want flagged
"""

# Project-root markers — mirror hooks/_exclusions.py:find_project_root so the
# template lands at the same root the hooks resolve. Kept local (bootstrap is
# standalone and must not import from hooks/).
PROJECT_ROOT_MARKERS = {
    ".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "composer.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "requirements.txt", "setup.py", "setup.cfg",
}
PROJECT_ROOT_GLOB_MARKERS = ("*.csproj", "*.sln", "*.fsproj")


def detect_scope_and_targets() -> tuple[str, Path, Path]:
    """Return (scope, settings_json_path, commands_dir_path).

    scope is "global" or "project".
    """
    home_claude = Path.home() / ".claude"
    try:
        # Use the unresolved path — the skill may be symlinked from the
        # canonical install location into ~/.claude/skills/<name>/ or
        # <project>/.claude/skills/<name>/. Both forms still place the
        # symlink itself under one of those `.claude/skills/` parents,
        # which is what we use for scope detection.
        if str(SCRIPT_PATH).startswith(str(home_claude) + os.sep):
            return "global", home_claude / "settings.json", home_claude / "commands"
    except Exception:
        pass

    # Walk up looking for `.claude/skills/<our-skill>/...` — the `.claude`
    # directory's parent is the project root.
    for parent in SCRIPT_PATH.parents:
        if parent.name == ".claude":
            return "project", parent / "settings.json", parent / "commands"

    # Fallback — the invocation path has no `.claude` ancestor (e.g. a symlink
    # install where the path collapsed to its real `.agents/...` target and $PWD
    # couldn't recover the shortcut). If the GLOBAL Claude skills dir points back
    # at where we actually live, it's a global install — wire there. (Project
    # scope can't be recovered this way: a shared real copy may be symlinked from
    # many projects, so the invocation path is the only thing that disambiguates.)
    home_skill = home_claude / "skills" / SKILL_DIR.name
    try:
        if home_skill.exists() and os.path.realpath(home_skill) == os.path.realpath(SKILL_DIR):
            return "global", home_claude / "settings.json", home_claude / "commands"
    except OSError:
        pass

    # No `.claude` ancestor found and no global symlink points back. Refuse to
    # guess — writing to an unexpected location is worse than asking the user to
    # install correctly.
    raise SystemExit(
        f"bootstrap: cannot determine install scope. This script must be invoked\n"
        f"through a `.claude/skills/coding-standards/bootstrap.py` symlink (project\n"
        f"or global). Got: {SCRIPT_PATH}\n"
        f"Install via `npx skills add willey-labs/agent-skills` and try again."
    )


def _find_project_root_from(start: Path) -> Path | None:
    """Walk up from `start` to the first directory holding a project-root marker.

    Used only for GLOBAL-scope installs, where there is no project tied to the
    skill location — so we fall back to the cwd the agent ran bootstrap from.
    Returns None if no marker is found within 20 levels.
    """
    current = start if start.is_dir() else start.parent
    for _ in range(20):
        if any((current / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return current
        if any(next(current.glob(pattern), None) is not None for pattern in PROJECT_ROOT_GLOB_MARKERS):
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def seed_ignore_template(scope: str, settings_path: Path) -> tuple[str, Path | None]:
    """Drop a commented `.coding-standards-ignore` template at the project root.

    Discovery, not enforcement: an absent file is invisible, so users assume the
    skill can't be told to skip anything. Project scope roots at the `.claude`
    parent; global scope falls back to the cwd's project root. Never overwrites
    an existing file. Returns (action, path) with action in
    {'created', 'exists', 'no-project'}.
    """
    if scope == "project":
        project_root: Path | None = settings_path.parent.parent
    else:
        project_root = _find_project_root_from(Path.cwd())
    if project_root is None:
        return "no-project", None
    target = project_root / IGNORE_FILENAME
    if target.exists():
        return "exists", target
    try:
        target.write_text(IGNORE_TEMPLATE, encoding="utf-8")
    except OSError:
        return "no-project", None
    return "created", target
