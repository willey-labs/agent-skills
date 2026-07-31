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
from _bootstrap.settings import (  # noqa: E402
    HOOK_FILES,
    POST_TOOL_USE_FILES,
    SESSION_START_FILES,
    STOP_FILES,
    USER_PROMPT_SUBMIT_FILES,
)


def _basenames(entries: list) -> list[str]:
    return [h["command"].split("/")[-1] for e in entries for h in e.get("hooks", [])]


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

    post = _basenames(hooks.get("PostToolUse", []))
    if post != POST_TOOL_USE_FILES:
        failures.append(f"settings.example PostToolUse {post} != {POST_TOOL_USE_FILES}")

    stop_entries = hooks.get("Stop", [])
    if any("matcher" in e for e in stop_entries):
        failures.append("settings.example Stop entry carries a matcher (Stop takes none)")
    stop = _basenames(stop_entries)
    if stop != STOP_FILES:
        failures.append(f"settings.example Stop {stop} != {STOP_FILES}")

    session = _basenames(hooks.get("SessionStart", []))
    if session != SESSION_START_FILES:
        failures.append(f"settings.example SessionStart {session} != {SESSION_START_FILES}")

    prompt_entries = hooks.get("UserPromptSubmit", [])
    if any("matcher" in e for e in prompt_entries):
        failures.append("settings.example UserPromptSubmit carries a matcher (it takes none)")
    prompt = _basenames(prompt_entries)
    if prompt != USER_PROMPT_SUBMIT_FILES:
        failures.append(f"settings.example UserPromptSubmit {prompt} != {USER_PROMPT_SUBMIT_FILES}")

    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print(f"ok — settings.example in sync ({len(HOOK_FILES)} hooks + SessionStart)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
