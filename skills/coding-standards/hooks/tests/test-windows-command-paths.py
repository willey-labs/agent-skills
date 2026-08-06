#!/usr/bin/env python3
"""Regression test — wired command paths carry forward slashes on every platform.

A settings.json hook command is run through a shell; on Windows that shell is Git
Bash, which consumes each backslash of a native path as an escape and leaves the
command pointing at a mangled filename. Every hook then exits 127, and a dead
UserPromptSubmit hook blocks the prompt outright. Both installers must therefore
render interpreter, script and permission-rule paths with forward slashes.

Windows-shaped paths are injected into the builders directly, so the check runs on
any platform.

    python3 hooks/tests/test-windows-command-paths.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent  # skills/coding-standards
WRITING_SKILL = SKILL.parent / "writing-standards"
sys.path.insert(0, str(SKILL))
from _bootstrap import hook_entries, permissions  # noqa: E402
from _bootstrap.interpreter import hook_interpreter  # noqa: E402
from _bootstrap.paths import command_path  # noqa: E402

WIN_HOOKS = r"C:\Users\me\.agents\skills\coding-standards\hooks"
WIN_SKILL_DIR = r"C:\Users\me\.agents\skills\coding-standards"
WIN_PYTHON = r"C:\Users\me\.local\share\coding-standards\venv\Scripts\python.exe"
POSIX_HOOKS = "C:/Users/me/.agents/skills/coding-standards/hooks"

# writing-standards ships its own _bootstrap package under the same module name, so
# it is probed in a separate interpreter rather than imported alongside this one.
WRITING_PROBE = (
    "import sys;"
    "sys.path.insert(0, sys.argv[1]);"
    "from _bootstrap import settings;"
    "settings.HOOKS_DIR = sys.argv[2];"
    'print(settings.build_session_start_entry("global")["hooks"][0]["command"])'
)


def check_renderer() -> list[str]:
    """command_path swaps separators and leaves a POSIX path alone."""
    out: list[str] = []
    if command_path(WIN_HOOKS) != POSIX_HOOKS:
        out.append(f"command_path({WIN_HOOKS!r}) -> {command_path(WIN_HOOKS)!r}")
    if command_path("/home/me/skills/coding-standards/hooks") != "/home/me/skills/coding-standards/hooks":
        out.append("command_path mangled a POSIX path")
    return out


def check_wired_commands() -> list[str]:
    """Every command in every event entry a global install wires is backslash-free."""
    hook_entries.HOOKS_DIR = WIN_HOOKS
    interpreter = hook_interpreter("global", "python3", Path(WIN_PYTHON))
    entries = [
        hook_entries.build_hook_entry("global", interpreter),
        hook_entries.build_session_start_entry("global"),
        hook_entries.build_user_prompt_submit_entry("global"),
        hook_entries.build_post_tool_use_entry("global"),
        hook_entries.build_stop_entry("global"),
    ]
    commands = [hook["command"] for entry in entries for hook in entry["hooks"]]
    out = [f"backslash in wired command: {c}" for c in commands if "\\" in c]
    if not any(c.startswith(f"{command_path(WIN_PYTHON)} {POSIX_HOOKS}/") for c in commands):
        out.append("venv interpreter and hooks dir not rendered as a POSIX command")
    return out


def check_system_interpreter() -> list[str]:
    """A global install with no managed venv pins the running interpreter POSIX-style."""
    original = sys.executable
    sys.executable = WIN_PYTHON
    try:
        rendered = hook_interpreter("global", "python3", None)
    finally:
        sys.executable = original
    if "\\" in rendered:
        return [f"backslash in pinned interpreter: {rendered}"]
    return []


def check_permission_rules() -> list[str]:
    """The Bash allow-rules match a forward-slash command line."""
    permissions.SKILL_DIR = WIN_SKILL_DIR
    settings: dict = {}
    permissions.ensure_skill_permissions(settings, include_dirs=False)
    rules = settings["permissions"]["allow"]
    return [f"backslash in permission rule: {r}" for r in rules if "\\" in r]


def check_writing_standards() -> list[str]:
    """The companion installer renders its own hook command the same way."""
    probe = subprocess.run(
        [sys.executable, "-c", WRITING_PROBE, str(WRITING_SKILL), WIN_HOOKS],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return [f"writing-standards probe failed: {probe.stderr.strip()}"]
    command = probe.stdout.strip()
    if "\\" in command:
        return [f"backslash in writing-standards command: {command}"]
    if not command.endswith("/inject-writing-standards.py"):
        return [f"writing-standards command lost its script path: {command}"]
    return []


def main() -> int:
    failures = (
        check_renderer()
        + check_wired_commands()
        + check_system_interpreter()
        + check_permission_rules()
        + check_writing_standards()
    )
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print("ok — hook commands, interpreters and permission rules render POSIX paths")
    return 0


if __name__ == "__main__":
    sys.exit(main())
