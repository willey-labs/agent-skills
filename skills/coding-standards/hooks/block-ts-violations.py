#!/usr/bin/env python3
"""PreToolUse hook — TypeScript / JavaScript content checks (regex + orchestration).

Hard-blocks Write/Edit/MultiEdit when the new content violates rules detectable
without a full parse, and orchestrates the AST and import layers:

- `any` (OD-006, TS only): `: any`, `<any>`, `as any`, `any[]`, ...
- Hungarian notation (NM-006): `strName`, `arrItems`, ...
- FN-005 arg count — regex fallback only (the precise AST count is preferred).

The import / ST-003 checks live in `_ts_imports.py`, the tree-sitter AST checks
(FN-001/FN-005/OD-004) in `_ts_ast.py` (node logic in `_ts_node_checks.py`). One
job per file (ST-008): this file is the regex checks + the dispatch.

Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _hook_run import block, cited_rules, read_payload, resolve_target  # noqa: E402
from _ts_imports import iter_import_violations  # noqa: E402
# _ts_ast guards its own tree-sitter import and degrades to ast_ran=False, which
# collect_violations handles via the regex fallback. is_express_error_middleware_params
# is shared so the AST path and this file's regex fallback agree on FN-005.
from _ts_ast import (  # noqa: E402
    ast_backend_available,
    is_express_error_middleware_params,
    iter_ts_ast_violations,
)

from _languages import (  # noqa: E402  (shared so extension sets can't drift — ISS-010)
    JS_EXTENSIONS,
    TS_EXTENSIONS,
    VUE_LIKE_EXTENSIONS,
)

# OD-006 — `any` is banned in every position. `\bany\b`-style bounds keep these
# off identifiers that merely contain the letters (company, anyhow, manyItems).
# The generic-argument rule is position-agnostic: it matches `any` led by `<` OR
# `,` and trailed by `,` OR `>`, so `Record<string, any>`, `Map<K, any>` and
# `Promise<Map<K, any>>` are caught — not just leading `<any>` (ISS-002). It
# subsumes the old Array<any>/Promise<any> special cases.
ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*any\b"), "type annotation `: any`"),
    (re.compile(r"\bas\s+any\b"), "type assertion `as any`"),
    (re.compile(r"\bsatisfies\s+any\b"), "`satisfies any`"),
    (re.compile(r"\bany\s*\[\]"), "array type `any[]`"),
    (re.compile(r"[<,]\s*any\s*[,>]"), "generic argument `any` (e.g. Record<string, any>)"),
    (re.compile(r"\btype\s+\w+\s*(?:<[^>=]*>)?\s*=\s*any\b"), "type alias laundering `type X = any`"),
    (re.compile(r"\bextends\s+any\b"), "type constraint `extends any`"),
]

# NM-006 — Hungarian notation. Single-char prefixes (b, i, n, o, a) were
# excluded because they false-positive on legitimate names (aUser, iValue).
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
# Class fields, interface members, object properties — `private strName: T`,
# `strHost: string` (interface), `{ strData: x }`. Anchored at line start, after a
# member modifier, or after `;`/`{`, and requires a trailing `:` so it's a typed
# member/property (ISS-013). The `[A-Z][a-z]+` after the prefix is the same FP
# guard the other shapes use — `strategy`/`strengthScore` never match.
HUNGARIAN_MEMBER = re.compile(
    rf"(?:^\s*|[;{{]\s*|\b(?:public|private|protected|readonly|static)\s+)"
    rf"(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)\s*[?!]?\s*:"
)

# FN-005 regex fallback — used only when the AST didn't run (bypassed bootstrap /
# interpreter mismatch / unparseable snippet). The Express error-middleware shape
# (err, req, res, next) is exempt — same carve-out as the AST path. The precise
# DI-constructor / record carve-outs are AST-only; this coarse fallback can't see them.
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


def strip_strings_and_comments(source: str) -> str:
    """Blank out strings and comments so detectors don't match inside them.
    Replaces matched ranges with same-length whitespace so offsets stay stable."""

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
                yield f"{file_path}:{idx} — OD-006: `any` is banned ({label}); name the type, or use `unknown` + narrowing / a generic"
                break


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for match in HUNGARIAN_DECL.finditer(line):
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation "
                f"`{match.group('prefix')}{match.group('rest')}`; drop the `{match.group('prefix')}` prefix"
            )
        for match in HUNGARIAN_PARAM.finditer(line):
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation "
                f"`{match.group('prefix')}{match.group('rest')}` (parameter); drop the `{match.group('prefix')}` prefix"
            )
        for match in HUNGARIAN_MEMBER.finditer(line):
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation "
                f"`{match.group('prefix')}{match.group('rest')}` (member/property); drop the `{match.group('prefix')}` prefix"
            )


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        if not any(pattern.search(line) for pattern in FUNCTION_ARG_COUNT_PATTERNS):
            continue
        if is_express_error_middleware_params(line):
            continue
        yield (
            f"{file_path}:{idx} — FN-005: function takes 4+ positional arguments; "
            f"group them into a typed object parameter"
        )


def collect_violations(new_content: str, file_path: str, ext: str) -> list[str]:
    """Run every TS/JS check over the new content and return the violation lines."""
    is_ts = ext in TS_EXTENSIONS or ext in VUE_LIKE_EXTENSIONS
    # Content-token checks run on cleaned text; import checks need raw lines (the
    # path lives inside the quoted specifier, which the cleaner would blank out).
    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    if is_ts:
        violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_import_violations(raw_lines, file_path))
    # AST checks supersede regex arg-count when tree-sitter ran; else fall back.
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
    ext = Path(file_path).suffix

    # Surface degraded enforcement: FN-001/OD-004 are AST-only, so without
    # tree-sitter they silently no-op while regex checks still run. Fires only on
    # a broken/bypassed bootstrap. Covers .vue/.svelte too — their `<script>`
    # blocks now run the AST path (ISS-010), so they degrade with everything else.
    if not ast_backend_available() and ext in (TS_EXTENSIONS | JS_EXTENSIONS | VUE_LIKE_EXTENSIONS):
        sys.stderr.write(
            "coding-standards: tree-sitter unavailable — FN-001/OD-004 AST checks "
            "skipped for this write (regex checks still ran); re-run bootstrap.py "
            "to restore them.\n"
        )

    violations = collect_violations(new_content, file_path, ext)
    if not violations:
        return 0

    see = f"See skills/coding-standards/references/common/ for cited rules ({cited_rules(violations)})."
    return block(violations, see)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-ts-violations internal error, skipped ({exc})\n")
        sys.exit(0)
