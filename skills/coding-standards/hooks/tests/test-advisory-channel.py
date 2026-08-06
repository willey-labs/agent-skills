#!/usr/bin/env python3
"""Regression test — an advisory reaches Claude, not the debug log.

Stderr from a hook that exits 0 is written to the debug log and never shown to
Claude, so an advisory sent there corrects nobody: the hook fires, the finding is
right, and the writer never sees it. Every advisory therefore leaves as
`hookSpecificOutput.additionalContext` on stdout, which arrives with the tool result.

This asserts the wire format directly rather than through `_hook_run.advisory_text`,
so an emitter and a reader that agree with each other but not with the hook contract
still fail here.

    python3 hooks/tests/test-advisory-channel.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import report_failures  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent.parent


@dataclass
class AdvisoryCase:
    """A file that must draw an advisory from `hook`, citing `rule`."""

    name: str
    hook: str
    file_path: str
    content: str
    rule: str


CASES = [
    AdvisoryCase(
        "comment slop",
        "advise-comment-slop.py",
        "/tmp/adv/src/notes.ts",
        "// TODO: come back to this\nexport const total = 1;\n",
        "CM-006",
    ),
    AdvisoryCase(
        "print residue",
        "block-debug-artifacts.py",
        "/tmp/adv/src/trace.ts",
        "export function run() {\n  console.log('here');\n}\n",
        "FMT-005",
    ),
    AdvisoryCase(
        "go empty interface",
        "block-go-violations.py",
        "/tmp/adv/src/store.go",
        "package store\n\nfunc Put(value interface{}) {}\n",
        "any",
    ),
    AdvisoryCase(
        "oversized file",
        "block-god-file.py",
        "/tmp/adv/src/wide.ts",
        "".join(f"const value{i} = {i};\n" for i in range(450)),
        "ST-008",
    ),
]


def run(case: AdvisoryCase) -> subprocess.CompletedProcess:
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": case.file_path, "content": case.content}}
    )
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / case.hook)],
        input=payload,
        capture_output=True,
        text=True,
    )


def envelope_failure(case: AdvisoryCase, stdout: str) -> str | None:
    """The ways the emitted context can be malformed, in the order they matter."""
    if not stdout.strip():
        return f"{case.name}: emitted no context at all"
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return f"{case.name}: stdout is not JSON ({exc})"
    specific = payload.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        return f"{case.name}: no hookSpecificOutput object in {payload}"
    if specific.get("hookEventName") != "PreToolUse":
        return f"{case.name}: hookEventName is {specific.get('hookEventName')!r}, want 'PreToolUse'"
    context = specific.get("additionalContext") or ""
    if case.rule not in context:
        return f"{case.name}: context does not cite {case.rule}: {context.strip()!r}"
    return None


def check(case: AdvisoryCase) -> str | None:
    proc = run(case)
    if proc.returncode != 0:
        return f"{case.name}: advisory must exit 0, got {proc.returncode}: {proc.stderr.strip()}"
    if proc.stderr.strip():
        return f"{case.name}: wrote to stderr, where Claude never sees it: {proc.stderr.strip()}"
    return envelope_failure(case, proc.stdout)


def block_keeps_stderr() -> str | None:
    """A hard block still speaks on stderr — that is the channel exit 2 feeds back."""
    case = AdvisoryCase(
        "hard block",
        "block-debug-artifacts.py",
        "/tmp/adv/src/halt.ts",
        "export function run() {\n  debugger;\n}\n",
        "FMT-005",
    )
    proc = run(case)
    if proc.returncode != 2:
        return f"hard block: expected exit 2, got {proc.returncode}"
    if case.rule not in proc.stderr:
        return f"hard block: expected {case.rule} on stderr, got {proc.stderr.strip()!r}"
    return None


def main() -> int:
    failures = [f for f in (check(case) for case in CASES) if f]
    block_failure = block_keeps_stderr()
    if block_failure:
        failures.append(block_failure)
    return report_failures("advisory-channel", failures, len(CASES) + 1)


if __name__ == "__main__":
    sys.exit(main())
