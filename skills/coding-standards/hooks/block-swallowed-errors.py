#!/usr/bin/env python3
"""PreToolUse hook — EH-002 swallowed errors (all covered languages).

A silently-dropped failure is EH-002's headline bug and Worker 3's top must-fix:
the failure happened, nobody learns, the bug hides forever. It is also one of the
few judgement-feeling rules that regex catches at near-zero false-positive rate,
because the *shape* is unambiguous:

- **Empty catch block** (`catch (e) {}`, `catch {}`) in brace languages
  (TS/JS, C#, Java, Kotlin, PHP) — and the empty `.catch(() => {})` promise form.
- **Go** — `_ = err` (deliberate discard) and `if err != nil {}` (empty guard).
- **Python** — `except ...: pass` / `except ...: ...` whose suite is *only* a
  bare `pass`/`...`.

The documented EH-002 escape is a comment explaining why ignoring is correct, so
this hook runs on RAW text (comments NOT stripped): a comment inside the catch
body, on the `except` line, or after `_ = err` means the block isn't empty / the
discard is explained → allowed. Truly empty + uncommented → blocked. That keeps
the false-positive rate at essentially zero while forcing the one-line reason the
rule already requires.

Exit 2 with stderr on block, 0 otherwise. Stdlib only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _hook_run import block, read_payload, resolve_target  # noqa: E402

BRACE_EXTS = {
    ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs",
    ".vue", ".svelte", ".cs", ".java", ".kt", ".kts", ".php",
}
GO_EXTS = {".go"}
PY_EXTS = {".py", ".pyi"}
ALL_EXTS = BRACE_EXTS | GO_EXTS | PY_EXTS

# Empty catch — braces with only whitespace between them. A comment inside (the
# documented escape) puts text between the braces, so this won't match → allowed.
EMPTY_CATCH = re.compile(r"\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}")
EMPTY_CATCH_ARROW = re.compile(
    r"\.catch\s*\(\s*(?:\([^)]*\)|[A-Za-z_$][\w$]*)?\s*=>\s*\{\s*\}\s*\)"
)

GO_DISCARD = re.compile(r"(?:^|[^.\w])_\s*=\s*err\b")
GO_EMPTY_IF = re.compile(r"\bif\s+err\s*!=\s*nil\s*\{\s*\}")

# Python — the comment escape lives on the except line or the body line, so both
# patterns end in `\s*$` (nothing, including no `#` comment, may follow).
PY_EXCEPT_ONELINE = re.compile(r"^\s*except\b[^:#]*:\s*(?:pass|\.\.\.)\s*$")
PY_EXCEPT_HEAD = re.compile(r"^\s*except\b[^:#]*:\s*$")
PY_BARE_BODY = re.compile(r"^\s*(?:pass|\.\.\.)\s*$")

_SWALLOW_FIX = (
    "EH-002: swallowed error — handle it, translate it to a domain error, or "
    "re-raise. If ignoring is genuinely correct, log it and add a one-line "
    "comment saying why"
)


def _line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def iter_brace_violations(content: str, file_path: str) -> Iterable[str]:
    for pattern in (EMPTY_CATCH, EMPTY_CATCH_ARROW):
        for match in pattern.finditer(content):
            yield f"{file_path}:{_line_of(content, match.start())} — {_SWALLOW_FIX}"


def iter_go_violations(lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(lines, start=1):
        if "//" in line:  # a comment on the line is the documented escape
            continue
        if GO_DISCARD.search(line) or GO_EMPTY_IF.search(line):
            yield f"{file_path}:{idx} — {_SWALLOW_FIX}"


def iter_python_violations(lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(lines, start=1):
        if PY_EXCEPT_ONELINE.match(line):
            yield f"{file_path}:{idx} — {_SWALLOW_FIX}"
            continue
        if not PY_EXCEPT_HEAD.match(line):
            continue
        # Two-line form: the except suite's first real line is a bare pass/...
        for follow in lines[idx:]:
            if not follow.strip():
                continue
            if PY_BARE_BODY.match(follow):
                yield f"{file_path}:{idx} — {_SWALLOW_FIX}"
            break


def collect_violations(content: str, file_path: str, ext: str) -> list[str]:
    raw_lines = content.splitlines()
    violations: list[str] = []
    if ext in BRACE_EXTS:
        violations.extend(iter_brace_violations(content, file_path))
    if ext in GO_EXTS:
        violations.extend(iter_go_violations(raw_lines, file_path))
    if ext in PY_EXTS:
        violations.extend(iter_python_violations(raw_lines, file_path))
    return violations


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, ALL_EXTS)
    if target is None:
        return 0
    file_path, new_content = target
    violations = collect_violations(new_content, file_path, Path(file_path).suffix)
    if not violations:
        return 0
    return block(violations, "See skills/coding-standards/references/common/error-handling.md (EH-002).")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: block-swallowed-errors internal error, skipped ({exc})\n")
        sys.exit(0)
