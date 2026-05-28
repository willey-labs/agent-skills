#!/usr/bin/env python3
"""PreToolUse hook — TypeScript / JavaScript content checks.

Hard-blocks Write/Edit/MultiEdit when the new file content violates
high-precision rules that regex can catch reliably:

- `any` type usage (TS only): `: any`, `<any>`, `as any`, `any[]`, ...
- Hungarian notation in declarations: `strName`, `arrItems`, `objUser`, ... (NM-006)
- Function signatures with 4+ positional arguments (FN-005)
- Deep imports past a folder's public API: `@/foo/bar/baz` (ST-003)
- Parent traversal of 3+ levels: `../../../` (universal smell)

Reads the PreToolUse JSON payload from stdin. Exits 2 with a stderr message
to block when violations are found, exits 0 otherwise. Stdlib only.

Return-type checks are deliberately omitted — regex cannot do them with
acceptable precision; rely on `tsc --noEmit` and ESLint's
`@typescript-eslint/explicit-function-return-type` for that.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
# Vue SFCs and Svelte components carry TS/JS in `<script>` blocks. The rules
# fire on that script content; templates rarely look like `function f(a,b,c,d)`
# or `from "@/foo/bar/baz"`, so the false-positive rate is acceptably low.
VUE_LIKE_EXTENSIONS = {".vue", ".svelte"}

ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*any\b(?!\s*\w)"), "type annotation `: any`"),
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


def iter_import_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        if DEEP_IMPORT_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — ST-003: deep import past folder's public API; "
                f"import from the capability's index.ts instead"
            )
        if PARENT_TRAVERSAL_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — parent traversal of 3+ levels; "
                f"use a path alias (e.g. @/) or move the file closer to its caller"
            )


def extract_new_content(tool_name: str, tool_input: dict) -> str:
    if tool_name == "Write":
        return tool_input.get("content", "") or ""
    if tool_name == "Edit":
        return tool_input.get("new_string", "") or ""
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits") or []
        return "\n".join(
            (edit.get("new_string", "") or "") for edit in edits if isinstance(edit, dict)
        )
    return ""


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0

    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    ext = Path(file_path).suffix
    is_ts = ext in TS_EXTENSIONS
    is_js = ext in JS_EXTENSIONS
    is_vue_like = ext in VUE_LIKE_EXTENSIONS
    if not (is_ts or is_js or is_vue_like):
        return 0
    # Treat Vue/Svelte SFCs as TS for the purpose of `any`-type checks —
    # they're typically `<script lang="ts">` in modern setups.
    if is_vue_like:
        is_ts = True

    new_content = extract_new_content(tool_name, tool_input)
    if not new_content.strip():
        return 0

    # Content-token checks run on cleaned text (no strings/comments).
    # Import checks need raw lines — the import path lives inside the
    # quoted module specifier, which the cleaner would have blanked out.
    clean = strip_strings_and_comments(new_content)
    clean_lines = clean.splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    if is_ts:
        violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))
    violations.extend(iter_import_violations(raw_lines, file_path))

    if not violations:
        return 0

    header = (
        "coding-standards hook blocked this write — fix the violations and try again.\n"
        "See skills/coding-standards/references/common/ for cited rules "
        "(FN-005, NM-006, ST-003).\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
