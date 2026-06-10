#!/usr/bin/env python3
"""PreToolUse hook — FMT-005 debug residue + commented-out code (all languages).

Two teeth, set by the AGENTS precision policy (~1% false-positive bar for hard
blocks):

- **HARD BLOCK (exit 2)** — interactive-debugger forms that are *never* shipped:
  `debugger` (JS/TS), `breakpoint()` / `pdb.set_trace()` / `import pdb` (Python),
  `dd()` / `var_dump()` (PHP/Laravel). Effectively zero false positives — nobody
  commits these on purpose.
- **ADVISORY (exit 0 + stderr)** — print-style residue (`console.log`, `print(`,
  `fmt.Println`, `Console.WriteLine`, `System.out.print`, Kotlin `println`) and
  commented-out code. These have legitimate uses (a CLI prints; a comment explains),
  so the blunt signal warns rather than blocks. Under the review model every
  finding — advisory included — is a violation to confirm or `accept` with a reason.

Debug-residue patterns run on text with strings AND comments stripped (so a string
`"console.log"` or a commented `// console.log(x)` isn't double-counted). The
commented-out-code check runs on RAW lines (it needs the comment text), kept
conservative to limit noise even as an advisory.

Stdlib only. Exit 2 hard-block; exit 0 (with stderr) advisory; exit 0 silent clean.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _hook_run import read_payload, resolve_target  # noqa: E402

JS_EXTS = {".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
PY_EXTS = {".py", ".pyi"}
GO_EXTS = {".go"}
CS_EXTS = {".cs"}
JVM_EXTS = {".java", ".kt", ".kts"}
PHP_EXTS = {".php"}
KT_EXTS = {".kt", ".kts"}
ALL_EXTS = JS_EXTS | PY_EXTS | GO_EXTS | CS_EXTS | JVM_EXTS | PHP_EXTS

# (extension-set, compiled-pattern, label) — HARD BLOCK: debugger/halt forms.
HARD_PATTERNS: list[tuple[set[str], re.Pattern[str], str]] = [
    (JS_EXTS, re.compile(r"\bdebugger\b\s*;?"), "`debugger` statement"),
    (PY_EXTS, re.compile(r"\bbreakpoint\s*\("), "`breakpoint()`"),
    (PY_EXTS, re.compile(r"\b(?:i?pdb)\s*\.\s*set_trace\s*\("), "`pdb.set_trace()`"),
    (PY_EXTS, re.compile(r"^\s*import\s+i?pdb\b"), "`import pdb`/`import ipdb`"),
    (PHP_EXTS, re.compile(r"\bdd\s*\("), "Laravel `dd()` die-and-dump"),
    (PHP_EXTS, re.compile(r"\bvar_dump\s*\("), "`var_dump()`"),
]

# ADVISORY: print-style residue (legitimate in CLIs / loggers — confirm, don't block).
ADVISORY_PATTERNS: list[tuple[set[str], re.Pattern[str], str]] = [
    (JS_EXTS, re.compile(r"\bconsole\s*\.\s*(?:log|debug|info|dir|trace)\s*\("), "`console.log`-style call"),
    (PY_EXTS, re.compile(r"^\s*p?print\s*\("), "`print(`/`pprint(` call"),
    (GO_EXTS, re.compile(r"\bfmt\s*\.\s*Print(?:ln|f)?\s*\("), "`fmt.Print*` call"),
    (CS_EXTS, re.compile(r"\b(?:Console|Debug)\s*\.\s*Write(?:Line)?\s*\("), "`Console.WriteLine`-style call"),
    (JVM_EXTS, re.compile(r"\bSystem\s*\.\s*(?:out|err)\s*\.\s*print(?:ln)?\s*\("), "`System.out.print` call"),
    (KT_EXTS, re.compile(r"\bprintln?\s*\("), "Kotlin `println(`"),
]

# Commented-out code (advisory). Conservative: the comment content must *start*
# like a statement — a declaration keyword, a control keyword followed by `(`, a
# bare closing bracket (a disabled block tail), or an identifier immediately
# followed by `(` or `=` (a call or assignment). This deliberately avoids the
# "ends in `;`" heuristic, which false-positives on wrapped prose ("…(all run;").
# Shebangs and tool-directive comments are exempt.
_COMMENT_CODE = re.compile(
    r"""(?://|\#)\s*
        (?:
            (?:return|const|let|var|func|def|class|import|export|public|private|protected|fn|val|throw|await|yield)\b
          | (?:if|for|while|switch|catch|foreach)\s*\(
          | [}\])]
          | [\w$.]+\s*[(=]
        )
    """,
    re.VERBOSE,
)
_COMMENT_EXEMPT = re.compile(r"^\s*(?:#!|#\s*-\*-|//\s*(?:eslint|@ts-|prettier|biome|noqa|type:))")


def strip_strings_and_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r'"""(?:\\.|[^"\\]|"(?!""))*"""', blank, source, flags=re.DOTALL)
    source = re.sub(r"'''(?:\\.|[^'\\]|'(?!''))*'''", blank, source, flags=re.DOTALL)
    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"`(?:\\.|[^`\\])*`", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"#[^\n]*", blank, source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def collect(new_content: str, file_path: str, ext: str) -> tuple[list[str], list[str]]:
    """Return (hard_block_messages, advisory_messages) for one file."""
    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()
    hard: list[str] = []
    advisory: list[str] = []

    for ext_set, pattern, label in HARD_PATTERNS:
        if ext not in ext_set:
            continue
        for idx, line in enumerate(clean_lines, start=1):
            if pattern.search(line):
                hard.append(f"{file_path}:{idx} — FMT-005: {label} (debug residue — never ship)")

    for ext_set, pattern, label in ADVISORY_PATTERNS:
        if ext not in ext_set:
            continue
        for idx, line in enumerate(clean_lines, start=1):
            if pattern.search(line):
                advisory.append(f"{file_path}:{idx} — FMT-005: {label} (likely debug residue — confirm)")

    for idx, line in enumerate(raw_lines, start=1):
        if _COMMENT_EXEMPT.search(line):
            continue
        if _COMMENT_CODE.search(line):
            advisory.append(f"{file_path}:{idx} — FMT-005: commented-out code; delete it (git remembers)")

    return hard, advisory


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, ALL_EXTS)
    if target is None:
        return 0
    file_path, new_content = target
    hard, advisory = collect(new_content, file_path, Path(file_path).suffix)

    if hard:
        sys.stderr.write(
            "coding-standards hook blocked this write — fix the violations and try again.\n"
            "See skills/coding-standards/references/common/formatting.md (FMT-005).\n"
            + "".join(f"  - {m}\n" for m in hard)
        )
        return 2
    if advisory:
        sys.stderr.write(
            "coding-standards (advisory — not blocked):\n"
            + "".join(f"  - {m}\n" for m in advisory)
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: block-debug-artifacts internal error, skipped ({exc})\n")
        sys.exit(0)
