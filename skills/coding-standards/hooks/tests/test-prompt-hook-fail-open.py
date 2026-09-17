#!/usr/bin/env python3
"""Regression test — a broken reminder hook costs the reminder, never the prompt.

UserPromptSubmit is the one event where exit 2 erases what the user typed, and a
command the shell cannot start returns exactly 2: an interpreter missing from PATH, a
skill dir that moved, an install path holding a space wired by an older bootstrap. The
script itself never exits non-zero, which protects nothing, because the failure happens
before it runs. So the guard lives in the wired command.

Both installers are checked, on both scopes, and the guard is run through a real shell
against a path that does not exist — a guard asserted only as a string is a guard
nobody has seen work. The events that MUST keep their exit codes are checked too:
PreToolUse fails closed by design, and the Stop judge holds the turn open with exit 2.

    python3 hooks/tests/test-prompt-hook-fail-open.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent
WRITING_SKILL = SKILL.parent / "writing-standards"
sys.path.insert(0, str(SKILL))
from _bootstrap import hook_entries  # noqa: E402
from _bootstrap.hook_identity import is_our_user_prompt_submit_entry  # noqa: E402

MISSING_SCRIPT = "/nonexistent dir/inject.py"

WRITING_PROBE = (
    "import sys;"
    "sys.path.insert(0, sys.argv[1]);"
    "from _bootstrap import settings;"
    'print(settings.build_userprompt_entry(sys.argv[2])["hooks"][0]["command"])'
)


def _commands(entry: dict) -> list[str]:
    return [hook["command"] for hook in entry["hooks"]]


def check_guard_present() -> list[str]:
    """Both scopes wire the reminder with the fail-open guard."""
    out: list[str] = []
    for scope in ("project", "global"):
        for command in _commands(hook_entries.build_user_prompt_submit_entry(scope)):
            if not command.endswith(hook_entries.FAIL_OPEN):
                out.append(f"{scope} UserPromptSubmit command unguarded: {command}")
    return out


def check_other_events_unguarded() -> list[str]:
    """Events whose exit code carries meaning keep it."""
    entries = {
        "PreToolUse": hook_entries.build_hook_entry("global", "python3"),
        "SessionStart": hook_entries.build_session_start_entry("global"),
        "PostToolUse": hook_entries.build_post_tool_use_entry("global"),
        "Stop": hook_entries.build_stop_entry("global"),
    }
    return [
        f"{event} command carries the fail-open guard: {command}"
        for event, entry in entries.items()
        for command in _commands(entry)
        if command.endswith(hook_entries.FAIL_OPEN)
    ]


def check_guard_recognized() -> list[str]:
    """A guarded entry is still ours, so a re-run replaces it instead of duplicating."""
    entry = hook_entries.build_user_prompt_submit_entry("global")
    return [] if is_our_user_prompt_submit_entry(entry) else ["guarded entry no longer recognized"]


def check_guard_runs() -> list[str]:
    """Through a real shell, the guard turns a failed launch into exit 0."""
    shell = shutil.which("sh")
    if not shell:
        return []
    bare = f'python3 "{MISSING_SCRIPT}"'
    unguarded = subprocess.run([shell, "-c", bare], capture_output=True, text=True)
    if unguarded.returncode == 0:
        return ["a missing script already exits 0 — this test proves nothing here"]
    guarded = subprocess.run(
        [shell, "-c", f"{bare}{hook_entries.FAIL_OPEN}"], capture_output=True, text=True
    )
    if guarded.returncode != 0:
        return [f"guarded command still exited {guarded.returncode}"]
    return []


def check_writing_standards() -> list[str]:
    """The companion installer guards its own reminder the same way."""
    out: list[str] = []
    for scope in ("project", "global"):
        probe = subprocess.run(
            [sys.executable, "-c", WRITING_PROBE, str(WRITING_SKILL), scope],
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            out.append(f"writing-standards probe failed: {probe.stderr.strip()}")
        elif not probe.stdout.strip().endswith(hook_entries.FAIL_OPEN):
            out.append(f"writing-standards {scope} command unguarded: {probe.stdout.strip()}")
    return out


def main() -> int:
    failures = (
        check_guard_present()
        + check_other_events_unguarded()
        + check_guard_recognized()
        + check_guard_runs()
        + check_writing_standards()
    )
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print("ok — a reminder hook that cannot start exits 0 and leaves the prompt alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
