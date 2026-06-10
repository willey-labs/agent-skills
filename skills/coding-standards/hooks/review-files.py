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
import shutil
import subprocess
import sys
from pathlib import Path

HOOK_DIR = Path(__file__).resolve().parent
SKILL_DIR = HOOK_DIR.parent


def _imports_tree_sitter(interpreter: str) -> bool:
    try:
        proc = subprocess.run(
            [interpreter, "-c", "import tree_sitter, tree_sitter_typescript"],
            capture_output=True, timeout=20,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def resolve_interpreter() -> tuple[str, bool]:
    """Pick an interpreter that can run the TS/JS AST checks, returning
    (interpreter, has_tree_sitter).

    The write-time hooks are wired to the interpreter tree-sitter was installed
    into (often a dedicated `<skill>/.venv` on PEP-668 hosts). A review launched
    with a bare `python3` that lacks the grammars would silently skip FN-001 /
    OD-004 / precise FN-005 and report the file CLEAN — the exact write-blocks /
    review-passes split this driver exists to prevent. So prefer, in order: the
    launching interpreter, the skill's sibling venv, then PATH python — and use
    the first that actually imports the grammars. If none can, run anyway but
    report the gap as a finding (never silently)."""
    candidates = [sys.executable]
    for name in ("python", "python3"):
        for sub in ("bin", "Scripts"):
            venv_py = SKILL_DIR / ".venv" / sub / name
            if venv_py.exists():
                candidates.append(str(venv_py))
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    seen: set[str] = set()
    for interpreter in candidates:
        if interpreter in seen:
            continue
        seen.add(interpreter)
        if _imports_tree_sitter(interpreter):
            return interpreter, True
    return sys.executable, False


INTERPRETER, HAS_TREE_SITTER = resolve_interpreter()
DEGRADED_FINDING = (
    "[degraded] tree-sitter unavailable to this review — FN-001 (length), OD-004 "
    "(hybrid class) and precise FN-005 were NOT checked on TS/JS files. Run "
    "bootstrap.py to restore them, then re-review."
)

# Every content/path hook that applies to source files. Each self-filters by
# file extension and exits 0 when the file isn't its language — so running them
# all against every file mirrors how they register as PreToolUse hooks (all run;
# each picks its own). All findings are violations to fix (no severity tiers); the
# EXIT CODE only distinguishes a hard block (exit 2) from an advisory (exit 0 +
# stderr, tagged "[advisory]" so the reviewer knows it's the blunt size/flat-folder
# proxy to adjudicate). block-god-file does both — it blocks on too many behavioral
# declarations and advises on raw size / flat folders.
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
    "block-swallowed-errors.py",
    "block-debug-artifacts.py",
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

    Exit 2 → would have blocked at write time. Exit 0 with stderr → advisory,
    tagged "[advisory]" so the reviewer knows it's the blunt size/flat-folder proxy
    to adjudicate. Both are violations to fix — there are no severity tiers."""
    try:
        content = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"{path} — could not read ({exc})"]

    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}
    )
    violations: list[str] = []
    # Surface degraded enforcement instead of letting a TS/JS file report clean
    # when no interpreter could load the grammars (the silent write/review split).
    if not HAS_TREE_SITTER and Path(path).suffix in {
        ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"
    }:
        violations.append(DEGRADED_FINDING)
    for hook in HOOK_FILES:
        proc = subprocess.run(
            [INTERPRETER, str(HOOK_DIR / hook)],
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
