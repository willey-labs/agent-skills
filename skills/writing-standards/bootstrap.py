#!/usr/bin/env python3
"""writing-standards skill — bootstrap entry point.

Wires two hooks that inject the writing-standards reminder — `SessionStart`
(at session boot) and `UserPromptSubmit` (every prompt) — into the right
settings.json (project vs global, auto-detected from the install path). Stdlib
only; the hook it wires is stdlib only too, so there is no dependency install and
no venv (unlike coding-standards).

This file stays at the skill root: SKILL.md Step 0 invokes it by this exact path,
and `_bootstrap/paths` anchors scope detection on this file's location. The work
lives in `_bootstrap/` (paths, scope, settings) — one responsibility each.

Idempotent: re-running replaces our entries with the current ones and leaves
unrelated hooks alone. Safe to run repeatedly.

Flags:
  --verify   Fast read-only check (SKILL.md Step 0 runs this first): exit 0 if both
             hooks are already wired for this scope and the hook script exists on
             disk; non-zero if a full run is needed. Wires nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _bootstrap.paths import HOOKS_DIR
from _bootstrap.scope import detect_scope_and_targets
from _bootstrap.settings import (
    INJECT_SCRIPT,
    build_session_start_entry,
    build_userprompt_entry,
    is_our_entry,
    load_settings,
    merge_entry,
    write_settings,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="writing-standards skill bootstrap — wire the reminder hooks.",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Read-only: exit 0 if already wired for this scope, non-zero if not.",
    )
    return parser.parse_args(argv)


def _section_has_ours(settings: dict, section: str) -> bool:
    hooks_section = settings.get("hooks") if isinstance(settings, dict) else None
    entries = hooks_section.get(section) if isinstance(hooks_section, dict) else None
    if not isinstance(entries, list):
        return False
    return any(isinstance(entry, dict) and is_our_entry(entry) for entry in entries)


def verify_already_set_up() -> int:
    """0 only if both hooks are wired for this scope AND the hook script exists on
    disk (a moved/renamed skill dir leaves wiring intact but the command would exit
    127 — read that as not-ready so a real run rebuilds it). Read-only."""
    if not (HOOKS_DIR / INJECT_SCRIPT).exists():
        return 1
    try:
        scope, settings_path = detect_scope_and_targets()
        settings = load_settings(settings_path)
    except SystemExit:
        return 1
    if _section_has_ours(settings, "SessionStart") and _section_has_ours(settings, "UserPromptSubmit"):
        print(f"writing-standards: already wired ({scope}) — no bootstrap needed.")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    if args.verify:
        return verify_already_set_up()

    scope, settings_path = detect_scope_and_targets()
    settings = load_settings(settings_path)
    session_action = merge_entry(settings, "SessionStart", build_session_start_entry(scope))
    prompt_action = merge_entry(settings, "UserPromptSubmit", build_userprompt_entry(scope))

    if session_action == "noop" and prompt_action == "noop":
        print(f"writing-standards: already installed — {settings_path} ({scope}). No changes.")
        return 0

    write_settings(settings_path, settings)
    print(
        f"writing-standards: wired the reminder hooks into {settings_path} ({scope}).\n"
        f"  SessionStart: {session_action}; UserPromptSubmit: {prompt_action}.\n"
        f"  Hook script: {HOOKS_DIR / INJECT_SCRIPT}\n"
        "  Restart your agent so the hooks activate on the next session/prompt."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
