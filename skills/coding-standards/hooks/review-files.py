#!/usr/bin/env python3
"""Run the coding-standards hooks against EXISTING files (review mode).

The `block-*.py` hooks are PreToolUse hooks: they fire only when Claude Code is
about to Write/Edit a file. In Review mode nothing is written, so the hooks
never fire on their own — yet a review should still benefit from their
deterministic checks (`any`/`Any`/`dynamic`/`mixed`, Hungarian notation, 4+
argument functions, junk-drawer paths, deep imports, and the TS/Python AST
checks).

This driver feeds each file's CURRENT content to every `block-*.py` hook as a
synthetic `Write` payload — the exact contract the hooks use at write time — so
review findings match write-time blocking byte-for-byte. Excluded files
(node_modules, generated code, migrations, lock files, ...) are skipped by the
hooks themselves, exactly as they are at write time.

Usage:
    python3 review-files.py <file> [<file> ...]
    python3 review-files.py --json <file> ...      # machine-readable output
    git diff --name-only | python3 review-files.py --stdin

Exit code is always 0 — this is a reporter, not a gate. Findings go to stdout.
Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent

# Every content/path hook that applies to source files. Each self-filters by
# file extension and exits 0 when the file isn't its language — so running them
# all against every file mirrors how they register as PreToolUse hooks (all run;
# each picks its own). Severity is read from the EXIT CODE per run, not from a
# fixed list: a hook may block (exit 2 → must-fix) on one signal and advise
# (exit 0 + stderr → should-fix) on another. block-god-file does both — it blocks
# on too many behavioral declarations and advises on raw size / flat folders.
# block-structure-file-violations is omitted: it guards the config file, not source.
HOOK_FILES = (
    "block-junk-paths.py",
    "block-ts-violations.py",
    "block-py-violations.py",
    "block-go-violations.py",
    "block-csharp-violations.py",
    "block-php-violations.py",
    "block-jvm-violations.py",
    "block-god-file.py",
)


def _bullets(stderr: str) -> list[str]:
    """The `- ` bullet lines of a hook's stderr, headers dropped."""
    out = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
    return out


def check_file(path: str) -> list[str]:
    """Return the hook-level violations for one existing file (empty if clean).

    Exit 2 → would have blocked at write time → must-fix. Exit 0 with stderr →
    advisory → tagged "[advisory]" so the merge step files it as should-fix."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path} — could not read ({exc})"]

    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}
    )
    violations: list[str] = []
    for hook in HOOK_FILES:
        proc = subprocess.run(
            [sys.executable, str(HOOK_DIR / hook)],
            input=payload,
            capture_output=True,
            text=True,
        )
        if not proc.stderr.strip():
            continue
        if proc.returncode == 2:
            violations.extend(_bullets(proc.stderr))
        else:
            violations.extend("[advisory] " + b for b in _bullets(proc.stderr))
    return violations


def collect_paths(argv: list[str]) -> list[str]:
    """Gather file paths from argv and (if --stdin) from stdin, one per line."""
    paths = [arg for arg in argv if not arg.startswith("--")]
    if "--stdin" in argv:
        paths += [line.strip() for line in sys.stdin.read().splitlines() if line.strip()]
    return paths


def print_report(results: dict[str, list[str]]) -> None:
    total = 0
    for path, violations in results.items():
        if violations:
            total += len(violations)
            noun = "finding" if len(violations) == 1 else "findings"
            print(f"\n{path}  ({len(violations)} {noun}):")
            for violation in violations:
                print(f"  - {violation}")
        else:
            print(f"\n{path}  — clean (no hook-level violations)")
    print(f"\nTotal hook-level violations: {total}")


def main(argv: list[str]) -> int:
    paths = collect_paths(argv)
    if not paths:
        print(
            "usage: review-files.py <file> [<file> ...] | --stdin | --json",
            file=sys.stderr,
        )
        return 0
    results = {path: check_file(path) for path in paths}
    if "--json" in argv:
        print(json.dumps(results, indent=2))
    else:
        print_report(results)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
