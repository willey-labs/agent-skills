#!/usr/bin/env python3
"""Regression test — wired commands survive an install or project path holding a space.

A hook command in shell form is handed to `sh -c` (Git Bash on Windows), which splits an
unquoted argument on whitespace. A `$HOME` such as `/Library/Application Support/...`
therefore arrives as two arguments and every hook dies with "can't open file"; the
SessionStart health check then re-runs bootstrap, which regenerates the same broken
commands, so a hand-repaired settings.json is overwritten within one session.
`${CLAUDE_PROJECT_DIR}` is substituted before the shell sees the string, so a checkout
under a spaced path splits identically and must be quoted too.

Both sides are checked: the builders quote on the way out, and `--verify` parses back in
shell-aware, since a naive split there reports every hook as exiting 127 and triggers the
same destructive re-bootstrap.

Paths are injected into the builders directly, so the check runs on any machine.

    python3 hooks/tests/test-spaced-command-paths.py
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent
WRITING_SKILL = SKILL.parent / "writing-standards"
sys.path.insert(0, str(SKILL))
from _bootstrap import hook_entries  # noqa: E402
from _bootstrap.verify import command_parts  # noqa: E402

SPACED_HOME = "/Library/Application Support/.LocalData/w"
SPACED_HOOKS = f"{SPACED_HOME}/.agents/skills/coding-standards/hooks"
SPACED_PYTHON = f"{SPACED_HOME}/.local/share/coding-standards/venv/bin/python"
PLAIN_HOOKS = "/home/me/.agents/skills/coding-standards/hooks"
SPACED_PROJECT = "/Users/me/My Projects/app"

WRITING_PROBE = (
    "import sys;"
    "sys.path.insert(0, sys.argv[1]);"
    "from _bootstrap import settings;"
    "settings.HOOKS_DIR = sys.argv[2];"
    'print(settings.build_session_start_entry("global")["hooks"][0]["command"])'
)


def _global_commands(hooks_dir: str, interpreter: str) -> list[str]:
    hook_entries.HOOKS_DIR = hooks_dir
    entries = [
        hook_entries.build_hook_entry("global", interpreter),
        hook_entries.build_session_start_entry("global"),
        hook_entries.build_user_prompt_submit_entry("global"),
        hook_entries.build_post_tool_use_entry("global"),
        hook_entries.build_stop_entry("global"),
    ]
    return [hook["command"] for entry in entries for hook in entry["hooks"]]


def check_global_commands() -> list[str]:
    """Every command a spaced global install wires parses back into interpreter + script."""
    out: list[str] = []
    for command in _global_commands(SPACED_HOOKS, SPACED_PYTHON):
        parts = shlex.split(command)
        if len(parts) != 2:
            out.append(f"splits into {len(parts)} parts: {command}")
        elif not parts[1].startswith(f"{SPACED_HOOKS}/"):
            out.append(f"script path lost the spaced install dir: {parts[1]}")
    return out


def check_spaced_interpreter() -> list[str]:
    """A venv interpreter under the spaced home survives as one argument."""
    hook_entries.HOOKS_DIR = SPACED_HOOKS
    commands = [h["command"] for h in hook_entries.build_hook_entry("global", SPACED_PYTHON)["hooks"]]
    wrong = [c for c in commands if shlex.split(c)[0] != SPACED_PYTHON]
    return [f"interpreter lost its spaces: {shlex.split(wrong[0])[0]}"] if wrong else []


def check_project_placeholder() -> list[str]:
    """Project scope quotes the placeholder, so a spaced checkout stays one argument."""
    out: list[str] = []
    for hook in hook_entries.build_hook_entry("project", "python3")["hooks"]:
        command = hook["command"]
        if '"${CLAUDE_PROJECT_DIR}' not in command:
            out.append(f"placeholder not double-quoted: {command}")
        expanded = command.replace("${CLAUDE_PROJECT_DIR}", SPACED_PROJECT)
        if len(shlex.split(expanded)) != 2:
            out.append(f"expanded command splits into {len(shlex.split(expanded))} parts: {expanded}")
    return out


def check_plain_path_unquoted() -> list[str]:
    """An install path with no space gains no quotes, so existing wiring isn't rewritten."""
    quoted = [c for c in _global_commands(PLAIN_HOOKS, "/home/me/.local/share/cs/venv/bin/python") if '"' in c]
    return [f"unspaced command gained quotes: {quoted[0]}"] if quoted else []


def check_verify_parser() -> list[str]:
    """`--verify` reads interpreter and script back out of a quoted command."""
    out: list[str] = []
    script = f"{SPACED_HOOKS}/block-py-violations.py"
    parts = command_parts(f'"{SPACED_PYTHON}" "{script}"')
    if parts != [SPACED_PYTHON, script]:
        out.append(f"command_parts returned {parts}")
    if command_parts('python3 "/unbalanced/quote.py') != ["python3", '"/unbalanced/quote.py']:
        out.append("command_parts should fall back to a naive split on a malformed command")
    return out


def check_writing_standards() -> list[str]:
    """The companion installer quotes its own hook command the same way."""
    probe = subprocess.run(
        [sys.executable, "-c", WRITING_PROBE, str(WRITING_SKILL), SPACED_HOOKS],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        return [f"writing-standards probe failed: {probe.stderr.strip()}"]
    parts = shlex.split(probe.stdout.strip())
    if len(parts) != 2 or not parts[1].startswith(f"{SPACED_HOOKS}/"):
        return [f"writing-standards command does not survive a spaced path: {probe.stdout.strip()}"]
    return []


def main() -> int:
    failures = (
        check_global_commands()
        + check_spaced_interpreter()
        + check_project_placeholder()
        + check_plain_path_unquoted()
        + check_verify_parser()
        + check_writing_standards()
    )
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print("ok — wired commands and --verify survive a space in the install or project path")
    return 0


if __name__ == "__main__":
    sys.exit(main())
