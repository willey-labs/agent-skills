#!/usr/bin/env python3
"""PreToolUse hook — PHP / Laravel content checks.

Hard-blocks Write/Edit/MultiEdit on `.php` files when the new content
violates high-precision rules that regex can catch reliably:

- `mixed` type usage (PHP 8+ escape hatch out of the type system).
- Hungarian notation on `$strName`, `$arrItems`, `$objUser`, ...
- Function/method signatures with 4+ positional parameters (FN-005).

Stdlib only. Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

PHP_EXTENSIONS = {".php"}

MIXED_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*mixed\b"), "return type `: mixed`"),
    (re.compile(r"\bmixed\s+\$\w+"), "parameter type `mixed $var`"),
    (re.compile(r"\barray\s*<\s*[^,>]*,\s*mixed\s*>"), "`array<K, mixed>` (PHPDoc)"),
]

# Hungarian — applied to PHP `$variable` form.
HUNGARIAN_PREFIXES = ("str", "arr", "obj", "lst", "fn", "bln")
_PREFIX_ALT = "|".join(sorted(HUNGARIAN_PREFIXES, key=len, reverse=True))

HUNGARIAN_VAR = re.compile(
    rf"\$(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)"
)

# FN-005 — `function foo($a, $b, $c, $d)` / `public function foo(...)`.
FUNCTION_SIG = re.compile(
    r"\bfunction\s+\w+\s*\(([^)]*)\)"
)


def strip_strings_and_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"#[^\n]*", blank, source)  # PHP also accepts `#` comments
    # PHP heredoc/nowdoc — leave alone; rare and complex to strip.
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def iter_mixed_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in MIXED_RULES:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — `mixed` is banned ({label}); "
                    f"use a concrete type or union"
                )
                break


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for match in HUNGARIAN_VAR.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation `${prefix}{rest}`; "
                f"drop the `{prefix}` prefix"
            )


def _count_php_params(param_list: str) -> int:
    s = param_list.strip()
    if not s:
        return 0
    depth = 0
    parts = 1
    for ch in s:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts += 1
    return parts


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        match = FUNCTION_SIG.search(line)
        if not match:
            continue
        count = _count_php_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} parameters; "
                f"group them into a DTO / Form Request / data object"
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

    if Path(file_path).suffix not in PHP_EXTENSIONS:
        return 0

    new_content = extract_new_content(tool_name, tool_input)
    if not new_content.strip():
        return 0

    clean = strip_strings_and_comments(new_content)
    clean_lines = clean.splitlines()

    violations: list[str] = []
    violations.extend(iter_mixed_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    header = (
        "coding-standards hook blocked this write — fix the violations and try again.\n"
        "See skills/coding-standards/references/laravel/structure.md and common/.\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
