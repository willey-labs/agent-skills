#!/usr/bin/env python3
"""Regression test — settings.example.json matches the wired hook list (ISS-019).

AGENTS.md mandates keeping the example settings in sync with what bootstrap wires.
This asserts the example's PreToolUse command basenames equal HOOK_FILES exactly
(order included) and that it carries the SessionStart health check.

    python3 hooks/tests/test-config-sync.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent  # skills/coding-standards
sys.path.insert(0, str(SKILL))
from _bootstrap.settings import HOOK_FILES, SESSION_HEALTH_SCRIPT  # noqa: E402


def main() -> int:
    failures: list[str] = []
    example = json.loads((SKILL / "hooks" / "settings.example.json").read_text())
    hooks = example.get("hooks", {})

    pre = hooks.get("PreToolUse", [])
    basenames = [c["command"].split("/")[-1] for c in (pre[0]["hooks"] if pre else [])]
    if basenames != HOOK_FILES:
        failures.append(
            f"settings.example PreToolUse basenames {basenames} != HOOK_FILES {HOOK_FILES}"
        )

    ss = hooks.get("SessionStart", [])
    ss_cmds = [h["command"] for e in ss for h in e.get("hooks", [])]
    if not any(SESSION_HEALTH_SCRIPT in c for c in ss_cmds):
        failures.append("settings.example missing SessionStart health-check command")

    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print(f"ok — settings.example in sync ({len(HOOK_FILES)} hooks + SessionStart)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
