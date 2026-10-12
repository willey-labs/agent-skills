#!/usr/bin/env python3
"""PreToolUse hook — FMT-005 debug residue + commented-out code (all languages).

Two teeth, set by the AGENTS precision policy (~1% false-positive bar for hard
blocks):

- **HARD BLOCK (exit 2)** — interactive-debugger forms that are *never* shipped:
  `debugger` (JS/TS), `breakpoint()` / `pdb.set_trace()` / `import pdb` (Python),
  `dd()` / `var_dump()` (PHP/Laravel). Effectively zero false positives — nobody
  commits these on purpose.
- **ADVISORY (exit 0, emitted as tool-result context)** — print-style residue (`console.log`, `print(`,
  `fmt.Println`, `Console.WriteLine`, `System.out.print`, Kotlin `println`) and
  commented-out code. These have legitimate uses (a CLI prints; a comment explains),
  so the blunt signal warns rather than blocks. Print-style calls are skipped in a
  program entry point (shebang, `__main__` guard, `main` function), where they are
  the program's output. Under the review model every
  finding — advisory included — is a violation to confirm or `accept` with a reason.

Debug-residue patterns run on text with strings AND comments stripped (so a string
`"console.log"` or a commented `// console.log(x)` isn't double-counted). The
commented-out-code check runs on text with only strings and docstrings blanked (it
needs the comment text), reads `#` as a comment only in Python and PHP, and is kept
conservative to limit noise even as an advisory.

Stdlib only. Exit 2 hard-block (stderr); exit 0 advisory (stdout context); exit 0 silent clean.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _comment_scan import HASH_COMMENT_EXTS, blank_strings  # noqa: E402
from _hook_run import advise, advisory_message, read_payload, resolve_target  # noqa: E402

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
# A call form allows NO space before its paren: `foo(x)` is code, while
# `recognizes (and replaces)` is an English parenthetical, which prose uses
# constantly. An assignment keeps the optional space (`x = 1` is code either way).
# Shebangs and tool-directive comments are exempt.
_CODE_START = r"""\s*
        (?:
            (?:return|const|let|var|func|def|class|import|export|public|private|protected|fn|val|throw|await|yield)\b
          | (?:if|for|while|switch|catch|foreach)\s*\(
          | [}\])]+[;,]?\s*$
          | [\w$.]+(?:\(|\s*=)
        )
    """
_SLASH_COMMENT_CODE = re.compile(r"//" + _CODE_START, re.VERBOSE)
_SLASH_OR_HASH_COMMENT_CODE = re.compile(r"(?://|\#)" + _CODE_START, re.VERBOSE)
_COMMENT_EXEMPT = re.compile(r"^\s*(?:#!|#\s*-\*-|//\s*(?:eslint|@ts-|prettier|biome|noqa|type:))")

_PROGRAM_ENTRY = re.compile(
    r"\A#!"
    r"|^if\s+__name__\s*==\s*['\"]__main__['\"]"
    r"|^func\s+main\s*\(\s*\)"
    r"|^fun\s+main\s*\("
    r"|\bstatic\s+void\s+main\s*\(\s*String"
    r"|\bstatic\s+(?:async\s+)?(?:void|int|Task(?:<int>)?)\s+Main\s*\(",
    re.MULTILINE,
)


def is_program_entry(file_path: str, new_content: str) -> bool:
    """True when the file is a program entry point, where print-style calls are the output."""
    if _PROGRAM_ENTRY.search(new_content):
        return True
    try:
        on_disk = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return bool(_PROGRAM_ENTRY.search(on_disk))


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
    hard: list[str] = []
    advisory: list[str] = []

    for ext_set, pattern, label in HARD_PATTERNS:
        if ext not in ext_set:
            continue
        for idx, line in enumerate(clean_lines, start=1):
            if pattern.search(line):
                hard.append(f"{file_path}:{idx} — FMT-005: {label} (debug residue — never ship)")

    prints_are_output = is_program_entry(file_path, new_content)
    for ext_set, pattern, label in ADVISORY_PATTERNS:
        if ext not in ext_set or prints_are_output:
            continue
        for idx, line in enumerate(clean_lines, start=1):
            if pattern.search(line):
                advisory.append(f"{file_path}:{idx} — FMT-005: {label} (likely debug residue — confirm)")

    comment_code = _SLASH_OR_HASH_COMMENT_CODE if ext in HASH_COMMENT_EXTS else _SLASH_COMMENT_CODE
    for idx, line in enumerate(blank_strings(new_content).splitlines(), start=1):
        if _COMMENT_EXEMPT.search(line):
            continue
        if comment_code.search(line):
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
        return advise(advisory_message(advisory))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: block-debug-artifacts internal error, skipped ({exc})\n")
        sys.exit(0)
