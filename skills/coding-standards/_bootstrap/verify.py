#!/usr/bin/env python3
"""Answering whether the skill is genuinely wired. Read-only — touches no files.

SKILL.md Step 0 runs this first and skips the install when it passes, so a false pass
costs a whole session of unchecked writes. Four things fail open silently and are each
checked: an interpreter below the floor; a wiring that predates scripts the registry
has since added; an interpreter the wired hooks run under that cannot load the required
packages (every hook exits 127 and blocks nothing); and a wired script path that no
longer exists because the skill directory moved.

A wired command path still holding an unexpanded `${VAR}` is skipped rather than judged
missing — project scope leaves it unexpanded when the variable isn't set in this
process, and a false negative there would force a needless re-bootstrap every run.

Every failure prints the command that repairs it: a reader who has to go look one up is
a reader who proceeds unwired.

Stdlib only.
"""

from __future__ import annotations

import os
from pathlib import Path

from .dependencies import MIN_PYTHON, interpreter_has_packages
from .hook_identity import is_our_entry, missing_wired_scripts
from .paths import SCRIPT_PATH, command_path
from .readiness import readiness_report
from .scope import detect_scope_and_targets
from .settings import load_settings


def _wired_hook_interpreter(pre_tool_use: list) -> str | None:
    """The interpreter our wired commands run under, or None when none are wired."""
    for entry in pre_tool_use:
        if not (isinstance(entry, dict) and is_our_entry(entry)):
            continue
        for hook in entry.get("hooks") or []:
            command = (hook or {}).get("command", "")
            parts = command.split()
            if parts:
                return parts[0]
    return None


def _wired_hook_scripts(pre_tool_use: list) -> list[str]:
    """The hook script paths of every wired command of ours."""
    scripts: list[str] = []
    for entry in pre_tool_use:
        if not (isinstance(entry, dict) and is_our_entry(entry)):
            continue
        for hook in entry.get("hooks") or []:
            command = (hook or {}).get("command", "")
            parts = command.split()
            if len(parts) >= 2:
                scripts.append(parts[1])
    return scripts


def _all_wired_scripts_exist(scripts: list[str]) -> bool:
    """True unless a resolvable wired script path is missing from disk (ISS-015)."""
    for script in scripts:
        expanded = os.path.expandvars(script)
        if "${" in expanded:
            continue
        if not Path(expanded).exists():
            return False
    return True


def not_ready(reason: str) -> int:
    """Report why the skill isn't wired, name the command that fixes it, and fail."""
    print(
        f"coding-standards: {reason}\n"
        f"  Run this now:\n    python3 {command_path(SCRIPT_PATH)} --auto-install"
    )
    return 1


def already_set_up() -> int:
    """`--verify`: 0 when the wiring is complete and live, non-zero when it isn't."""
    if not readiness_report()["python_version_ok"]:
        return not_ready(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; this interpreter is older"
        )
    try:
        scope, settings_path, _commands = detect_scope_and_targets()
        settings = load_settings(settings_path)
    except SystemExit:
        return not_ready("cannot determine the install scope from this location")

    hooks_section = settings.get("hooks") if isinstance(settings, dict) else None
    pre_tool_use = hooks_section.get("PreToolUse") if isinstance(hooks_section, dict) else None
    pre_tool_use = pre_tool_use if isinstance(pre_tool_use, list) else []

    absent = missing_wired_scripts(settings)
    if absent:
        listed = "".join(f"    - {name}\n" for name in absent).rstrip("\n")
        return not_ready(f"{len(absent)} registered hook(s) not wired ({scope}):\n{listed}")

    interpreter = _wired_hook_interpreter(pre_tool_use)
    if interpreter is None:
        return not_ready(f"no enforcement hooks wired ({scope})")
    if not interpreter_has_packages(interpreter):
        return not_ready(
            f"the wired hooks run under `{interpreter}`, which cannot load the required "
            "packages — every hook would exit 127 and block nothing"
        )
    if not _all_wired_scripts_exist(_wired_hook_scripts(pre_tool_use)):
        return not_ready(f"a wired hook script is missing from disk ({scope}) — the skill moved")

    print(f"coding-standards: already set up ({scope}) — no bootstrap needed.")
    return 0
