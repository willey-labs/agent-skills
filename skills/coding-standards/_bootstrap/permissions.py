#!/usr/bin/env python3
"""Skill permission grants — and WHERE they get written.

Pre-approving the skill's file reads and script runs needs machine-absolute paths
(the resolved skill dir). Those are fine in a per-machine `~/.claude/settings.json`
(global scope) but must NOT land in a committed project `settings.json`: teammates
check out at different paths, so the rules would be inert for them and every
teammate's bootstrap would append their own — unbounded churn in a shared file
(ISS-012). On project scope they go to the git-ignored `settings.local.json`
instead, and `additionalDirectories` is skipped entirely (the skill lives inside
the project, already readable).

Split out of settings.py (ST-008): settings.py owns the hook entries + file I/O;
this owns the permission grants and their placement.
"""

from __future__ import annotations

from pathlib import Path

from .paths import SKILL_DIR
from .settings import load_settings, write_settings


def ensure_skill_permissions(settings: dict, include_dirs: bool = True) -> bool:
    """Pre-approve reading the skill's own files and running its scripts.

    Without this, the agent hits a Claude Code permission prompt for every
    reference file it loads and for each `bootstrap.py` / `hooks/review-files.py`
    run. Adds narrow Bash allow-rules for the skill's Python scripts and (when
    `include_dirs`) the skill dir to `permissions.additionalDirectories`.
    Idempotent; preserves existing entries. Returns True if anything changed.
    """
    perms = settings.get("permissions")
    if not isinstance(perms, dict):
        perms = {}
        settings["permissions"] = perms
    changed = False

    if include_dirs:
        # Read access to the skill's files (global scope: the skill dir sits
        # outside the user's project). Grant both the symlink path and its
        # resolved target, in case Claude Code resolves before the access check.
        dirs = perms.get("additionalDirectories")
        if not isinstance(dirs, list):
            dirs = []
            perms["additionalDirectories"] = dirs
        for candidate in (str(SKILL_DIR), str(SKILL_DIR.resolve())):
            if candidate not in dirs:
                dirs.append(candidate)
                changed = True

    # Run the skill's own scripts without a Bash prompt (cover python3 + python).
    allow = perms.get("allow")
    if not isinstance(allow, list):
        allow = []
        perms["allow"] = allow
    for py in ("python3", "python"):
        for script in ("bootstrap.py", "hooks/review-files.py"):
            rule = f"Bash({py} {SKILL_DIR}/{script}*)"
            if rule not in allow:
                allow.append(rule)
                changed = True

    return changed


def _ensure_gitignored(project_root: Path, entry: str) -> None:
    """Append `entry` to the project's `.gitignore` if it isn't already covered.

    settings.local.json carries machine-absolute paths (ISS-012); committing it
    would leak them and churn a shared file. Bootstrap can't rely on the user
    having gitignored it, so it ensures the line itself — best-effort, idempotent
    (a missing .gitignore is created)."""
    gitignore = project_root / ".gitignore"
    try:
        existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
        present = {line.strip() for line in existing.splitlines()}
        if entry in present or entry.lstrip("/") in present:
            return
        prefix = "" if existing == "" or existing.endswith("\n") else "\n"
        with gitignore.open("a", encoding="utf-8") as handle:
            handle.write(f"{prefix}{entry}\n")
    except OSError:
        pass  # best-effort: a missing/unwritable .gitignore must not fail bootstrap


def wire_skill_permissions(scope: str, settings_path: Path, committed_settings: dict) -> bool:
    """Grant the skill's permissions in the RIGHT file, return whether anything
    changed. Global: mutate the committed_settings dict (caller writes it).
    Project: write the machine-absolute rules to the git-ignored settings.local.json
    and skip additionalDirectories — keeping the committed settings.json portable.
    """
    if scope == "global":
        return ensure_skill_permissions(committed_settings, include_dirs=True)
    local_path = Path(settings_path).parent / "settings.local.json"
    local = load_settings(local_path)
    changed = ensure_skill_permissions(local, include_dirs=False)
    if changed:
        write_settings(local_path, local)
    # Keep the machine-local perms file out of git (ISS-012) — whether we just
    # wrote it or a prior run did.
    if local_path.exists():
        _ensure_gitignored(Path(settings_path).parent.parent, ".claude/settings.local.json")
    return changed
