#!/usr/bin/env python3
"""Install the `/coding-standards` slash command into the agent's commands dir.

Split out of `settings.py` so each file owns one job (ST-008): settings.py wires
settings.json + permissions; this file installs the command — by symlink where the
platform supports it, by copy where it doesn't (Windows without Developer Mode).
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .paths import SKILL_DIR

# A managed command file carries this line in its body; used to tell our own
# (copied) command from a user's customized file when deciding whether to refresh.
_MANAGED_MARKER = "Apply the coding-standards skill"


def _link_or_copy(source: Path, target: Path) -> bool:
    """Symlink `target` → `source`; if the platform forbids symlinks (Windows
    without Developer Mode / admin), fall back to copying. Returns True when a
    symlink was created, False when copied. Never raises for the symlink refusal —
    that's the point (a crash here used to leave settings.json written but the
    command half-installed)."""
    try:
        target.symlink_to(source)
        return True
    except (OSError, NotImplementedError):
        shutil.copy2(source, target)
        return False


def install_slash_command(commands_dir: Path) -> str:
    """Install the slash command — by symlink where supported, by copy where not.

    Returns the action taken: 'noop', 'created', or 'refreshed'.
    """
    source = (SKILL_DIR / "commands" / "coding-standards.md").resolve()
    if not source.exists():
        return "noop"  # no command file shipped (older skill version)

    commands_dir.mkdir(parents=True, exist_ok=True)
    target = commands_dir / "coding-standards.md"

    if target.is_symlink():
        if target.resolve() == source:
            return "noop"
        target.unlink()
        _link_or_copy(source, target)
        return "refreshed"

    if target.exists():
        # A plain file (not a symlink). On a no-symlink platform this is our own
        # prior copy — refresh if stale, noop if current. A file we did NOT write
        # (different content AND not our managed command) is left alone.
        try:
            existing = target.read_text(encoding="utf-8")
            current = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            existing = current = ""
        if existing == current:
            return "noop"
        if _MANAGED_MARKER in existing:
            shutil.copy2(source, target)  # our managed copy, now stale — refresh
            return "refreshed"
        print(
            f"coding-standards: skipped /coding-standards command — {target} "
            f"exists and is not bootstrap-managed. Remove it manually if you want "
            f"the bundled version."
        )
        return "noop"

    linked = _link_or_copy(source, target)
    if not linked:
        print(
            "coding-standards: this platform doesn't allow symlinks (Windows "
            "without Developer Mode) — copied the /coding-standards command "
            "instead. Re-run bootstrap after a skill update to refresh the copy."
        )
    return "created"
