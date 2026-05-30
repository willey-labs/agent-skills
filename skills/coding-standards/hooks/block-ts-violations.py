#!/usr/bin/env python3
"""PreToolUse hook — TypeScript / JavaScript content checks.

Hard-blocks Write/Edit/MultiEdit when the new file content violates rules
detectable via regex or AST.

Regex checks (always on — work on any content, including partial Edit snippets):
- `any` type (TS only): `: any`, `<any>`, `as any`, `any[]`, ...
- Hungarian notation (NM-006): `strName`, `arrItems`, ...
- Deep imports past public API (ST-003): `@/foo/bar/baz`
- Parent traversal `../../../` (universal smell)

AST checks (REQUIRED — bootstrap.py installs `tree-sitter` and the grammars
and refuses to wire the hooks until they load) live in the sibling unit
`_ts_ast.py` and cover FN-001 (function body length), FN-005 (precise
positional argument count), and OD-004 (hybrid classes, with the OD-005
framework-boundary carve-out). This file owns the regex checks and the
orchestration; it calls `iter_ts_ast_violations` and falls back to its own
regex arg-count check only when the AST didn't run (the defensive path for a
bypassed bootstrap or an interpreter mismatch).

Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _structure import is_check_enabled  # noqa: E402
# Shared PreToolUse lifecycle (gate, payload read, block emit) — see _hook_run.
from _hook_run import block, cited_rules, read_payload, resolve_target  # noqa: E402
# The tree-sitter AST checks (FN-001/FN-005/OD-004) live in a sibling unit so
# this file stays focused on the regex checks + orchestration (ST-008). The
# import never fails: _ts_ast guards its own tree-sitter import and degrades to
# ast_ran=False, which `collect_violations` handles via the regex fallback.
from _ts_ast import iter_ts_ast_violations  # noqa: E402

TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
# Vue SFCs and Svelte components carry TS/JS in `<script>` blocks. The rules
# fire on that script content; templates rarely look like `function f(a,b,c,d)`
# or `from "@/foo/bar/baz"`, so the false-positive rate is acceptably low.
VUE_LIKE_EXTENSIONS = {".vue", ".svelte"}

ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*any\b"), "type annotation `: any`"),
    (re.compile(r"<\s*any\s*[,>]"), "generic argument `<any>`"),
    (re.compile(r"\bas\s+any\b"), "type assertion `as any`"),
    (re.compile(r"\bany\s*\[\]"), "array type `any[]`"),
    (re.compile(r"\bArray\s*<\s*any\s*>"), "array type `Array<any>`"),
    (re.compile(r"\bPromise\s*<\s*any\s*>"), "promise type `Promise<any>`"),
]

# NM-006 — Hungarian notation. Single-char prefixes (b, i, n, o, a) were
# excluded because they false-positive on legitimate names (aUser, iValue).
# The remaining prefixes have effectively no false-positive rate.
HUNGARIAN_PREFIXES = ("str", "arr", "obj", "fn", "sz", "psz", "bln", "lp", "lpsz")
_PREFIX_ALT = "|".join(sorted(HUNGARIAN_PREFIXES, key=len, reverse=True))

HUNGARIAN_DECL = re.compile(
    rf"\b(?:let|const|var|function|async\s+function)\s+"
    rf"(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)"
)
HUNGARIAN_PARAM = re.compile(
    rf"(?P<bound>[(,]\s*)"
    rf"(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)\s*[:?=,)]"
)

# FN-005 — function signature with 4+ positional arguments.
# Catches: function foo(a, b, c, d) / const foo = (a, b, c, d) => ...
# Allows the object-param escape hatch: function foo({ a, b, c, d }).
FUNCTION_ARG_COUNT_PATTERNS = [
    re.compile(
        r"\b(?:function|async\s+function)\s+\w+\s*"
        r"\(\s*(?!\{)[^){]*?,[^){]*?,[^){]*?,[^){]*?\)"
    ),
    re.compile(
        r"\b(?:const|let|var)\s+\w+\s*[:=][^=]*?=\s*"
        r"\(\s*(?!\{)[^){]*?,[^){]*?,[^){]*?,[^){]*?\)\s*=>"
    ),
]

# ST-003 — deep imports past a folder's public entry.
# `@/foo/bar` is fine (capability + use case). `@/foo/bar/baz` reaches past.
DEEP_IMPORT_PATTERN = re.compile(
    r"""from\s+['"]@/[a-z][a-z0-9-]*/[a-z][a-z0-9-]*/[a-z][a-z0-9-]*"""
)

PARENT_TRAVERSAL_PATTERN = re.compile(r"""from\s+['"](\.\./){3,}""")


def strip_strings_and_comments(source: str) -> str:
    """Blank out strings and comments so detectors don't match inside them.

    Replaces matched ranges with same-length whitespace so line/column
    offsets stay stable.
    """

    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"`(?:\\.|[^`\\])*`", blank, source, flags=re.DOTALL)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def iter_any_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in ANY_RULES:
            if pattern.search(line):
                yield f"{file_path}:{idx} — `any` is banned ({label})"
                break


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for match in HUNGARIAN_DECL.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation `{prefix}{rest}`; "
                f"drop the `{prefix}` prefix"
            )
        for match in HUNGARIAN_PARAM.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation `{prefix}{rest}` "
                f"(parameter); drop the `{prefix}` prefix"
            )


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern in FUNCTION_ARG_COUNT_PATTERNS:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — FN-005: function takes 4+ positional arguments; "
                    f"group them into a typed object parameter"
                )
                break


def iter_import_violations(
    clean_lines: list[str], file_path: str, check_deep: bool = True
) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        if check_deep and DEEP_IMPORT_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — ST-003: deep import past folder's public API; "
                f"import from the capability's index.ts instead"
            )
        if PARENT_TRAVERSAL_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — parent traversal of 3+ levels; "
                f"use a path alias (e.g. @/) or move the file closer to its caller"
            )


def collect_violations(new_content: str, file_path: str, ext: str) -> list[str]:
    """Run every TS/JS check over the new content and return the violation lines."""
    # Treat Vue/Svelte SFCs as TS for the `any`-type checks — they're typically
    # `<script lang="ts">` in modern setups.
    is_ts = ext in TS_EXTENSIONS or ext in VUE_LIKE_EXTENSIONS
    # Content-token checks run on cleaned text (no strings/comments). Import
    # checks need raw lines — the import path lives inside the quoted module
    # specifier, which the cleaner would have blanked out.
    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    if is_ts:
        violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    # ST-003 deep-import is structure-dependent: a custom project with no barrels
    # turns it off via `.coding-standards-structure`. Parent-traversal stays on.
    violations.extend(
        iter_import_violations(
            raw_lines, file_path, check_deep=is_check_enabled("deep-import", file_path)
        )
    )
    # AST checks supersede regex arg-count when tree-sitter is available and the
    # content parses. Otherwise fall back to regex.
    ast_iter, ast_ran = iter_ts_ast_violations(new_content, file_path, ext)
    violations.extend(ast_iter)
    if not ast_ran:
        violations.extend(iter_arg_count_violations(clean_lines, file_path))
    return violations


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, TS_EXTENSIONS | JS_EXTENSIONS | VUE_LIKE_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target

    violations = collect_violations(new_content, file_path, Path(file_path).suffix)
    if not violations:
        return 0

    see = f"See skills/coding-standards/references/common/ for cited rules ({cited_rules(violations)})."
    return block(violations, see)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error (e.g. a tree-sitter API change
        # that slips past the load guard) block a legitimate write. Fail OPEN:
        # exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-ts-violations internal error, skipped ({exc})\n")
        sys.exit(0)
