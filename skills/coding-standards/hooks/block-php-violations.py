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

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
# Shared PreToolUse lifecycle (gate, payload read, block emit) — see _hook_run.
from _hook_run import block, join_wrapped_signatures, read_payload, resolve_target  # noqa: E402

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
# FN-005 carve-out — the constructor. Laravel/Symfony inject dependencies through
# `__construct` (often with promoted properties: `private OrdersRepo $orders`):
# the container calls it, not a hot call site. A 4+ dep constructor is grouped
# only when it genuinely hurts. A regular method with 4+ args still blocks.
PHP_CONSTRUCTOR = re.compile(r"\bfunction\s+__construct\s*\(")


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
                    f"{file_path}:{idx} — OD-006: `mixed` is banned ({label}); "
                    f"use a concrete type or a union"
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
    for lineno, text in join_wrapped_signatures(clean_lines):
        match = FUNCTION_SIG.search(text)
        if not match:
            continue
        if PHP_CONSTRUCTOR.search(text):
            continue
        count = _count_php_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{lineno} — FN-005: function takes {count} parameters; "
                f"group them into a DTO / Form Request / data object"
            )


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, PHP_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target

    clean_lines = strip_strings_and_comments(new_content).splitlines()

    violations: list[str] = []
    violations.extend(iter_mixed_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    return block(violations, "See skills/coding-standards/references/laravel/structure.md and common/.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-php-violations internal error, skipped ({exc})\n")
        sys.exit(0)
