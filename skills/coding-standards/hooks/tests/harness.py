#!/usr/bin/env python3
"""Shared test harness for the hook regression suite.

Every `test-*.py` file declares a list of payload cases and hands them to
`run_cases`. A case feeds a synthetic PreToolUse JSON payload to one hook via
stdin (the real enforcement entry point) and asserts the exit code and, when
given, that the cited rule code appears in the message the hook emitted.

Stdlib only, no test framework. Import from a sibling test file:

    from harness import Case, run_cases
    FAILURES = run_cases([Case("name", "block-py-violations.py", "/tmp/a.py", "...", block=True, rule="OD-006")])
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(HOOKS_DIR))
from _hook_run import advisory_text  # noqa: E402


@dataclass
class Case:
    """One regression case. `block=True` expects exit 2; `rule` (optional) must
    appear in the message so a block fired for the *right* reason, not by accident."""

    name: str
    hook: str
    file_path: str
    content: str
    block: bool
    rule: str | None = None


def run_hook(hook: str, file_path: str, content: str) -> tuple[int, str]:
    """Run one hook against a Write payload, return (exit_code, message).

    The message is whatever the hook told the writer, from whichever channel it used:
    stderr for a block, the stdout context envelope for an advisory.
    """
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}
    )
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / hook)],
        input=payload,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr + advisory_text(proc.stdout)


def run_cases(cases: list[Case]) -> list[str]:
    """Run every case, return a list of human-readable failure descriptions."""
    failures: list[str] = []
    for case in cases:
        code, message = run_hook(case.hook, case.file_path, case.content)
        blocked = code == 2
        if blocked != case.block:
            failures.append(
                f"{case.name}: expected {'block' if case.block else 'pass'}, "
                f"got exit {code}: {message.strip()}"
            )
            continue
        if case.block and case.rule and case.rule not in message:
            failures.append(
                f"{case.name}: blocked but missing rule {case.rule} in message: {message.strip()}"
            )
    return failures


def report_failures(suite_name: str, failures: list[str], case_count: int) -> int:
    """Print one line per failure, or the ok line, and return a process exit code.

    Split out for the suites that assert something other than the exit code — an
    advisory's stderr, a post-edit file state — and so run their own cases.
    """
    for failure in failures:
        sys.stderr.write(f"FAIL {failure}\n")
    if failures:
        return 1
    print(f"ok — {case_count} {suite_name} cases hold")
    return 0


def report(suite_name: str, cases: list[Case]) -> int:
    """Run cases, print one line per failure, return a process exit code."""
    return report_failures(suite_name, run_cases(cases), len(cases))
