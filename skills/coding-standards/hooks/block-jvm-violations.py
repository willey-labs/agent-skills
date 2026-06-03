#!/usr/bin/env python3
"""PreToolUse hook — Java / Kotlin (Spring Boot) content checks.

Hard-blocks Write/Edit/MultiEdit on `.java` and `.kt` files when the new
content violates high-precision rules that regex can catch reliably:

- Star imports: `import com.foo.*;` (Java) or `import com.foo.*` (Kotlin).
- Method signatures with 4+ positional parameters (FN-005).
- Kotlin `Any` type used as a value type annotation.

Stdlib only. Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
# Shared PreToolUse lifecycle (gate, payload read, block emit) — see _hook_run.
from _hook_run import block, read_payload, resolve_target  # noqa: E402

JVM_EXTENSIONS = {".java", ".kt", ".kts"}

# Star imports — bring entire package into scope, hide where a type came from.
STAR_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?[\w.]+\.\*\s*;?\s*$")

# Kotlin `Any` and `Any?` as a declared type — same smell as TS `any`.
# Java's `Object` is too common in legitimate code to flag without noise.
KOTLIN_ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*Any\??\b"), "type annotation `: Any` / `: Any?`"),
    (re.compile(r"\bList\s*<\s*Any\??\s*>"), "`List<Any>`"),
    (re.compile(r"\bMap\s*<[^>]*,\s*Any\??\s*>"), "`Map<K, Any>`"),
]

# Java / Kotlin method signatures.
# Java:  `public ReturnType name(Type a, Type b, Type c, Type d)`
# Kotlin: `fun name(a: Type, b: Type, c: Type, d: Type): Return`
JAVA_METHOD_SIG = re.compile(
    r"\b(?:public|private|protected|static|final|abstract|synchronized|default)"
    r"[\w<>,\s\[\]?]*?\s+\w+\s*\(([^)]*)\)"
)
KOTLIN_FUN_SIG = re.compile(r"\bfun\b[^(]*\(([^)]*)\)")


def strip_strings_and_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    # Kotlin raw strings """..."""
    source = re.sub(r'"""(?:[^"]|"(?!""))*"""', blank, source, flags=re.DOTALL)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def iter_star_import_violations(raw_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(raw_lines, start=1):
        if STAR_IMPORT.search(line):
            yield (
                f"{file_path}:{idx} — star import banned; "
                f"name each type you import"
            )


def iter_kotlin_any_violations(
    clean_lines: list[str], file_path: str, is_kotlin: bool
) -> Iterable[str]:
    if not is_kotlin:
        return
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in KOTLIN_ANY_RULES:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — Kotlin `Any` is banned ({label}); "
                    f"use a concrete type or sealed hierarchy"
                )
                break


def _count_jvm_params(param_list: str) -> int:
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


def iter_arg_count_violations(
    clean_lines: list[str], file_path: str, is_kotlin: bool
) -> Iterable[str]:
    sig_re = KOTLIN_FUN_SIG if is_kotlin else JAVA_METHOD_SIG
    for idx, line in enumerate(clean_lines, start=1):
        match = sig_re.search(line)
        if not match:
            continue
        count = _count_jvm_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} parameters; "
                f"group them into a request/DTO record"
            )


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, JVM_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target
    is_kotlin = Path(file_path).suffix in {".kt", ".kts"}

    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    violations.extend(iter_star_import_violations(raw_lines, file_path))
    violations.extend(iter_kotlin_any_violations(clean_lines, file_path, is_kotlin))
    violations.extend(iter_arg_count_violations(clean_lines, file_path, is_kotlin))

    if not violations:
        return 0

    return block(violations, "See skills/coding-standards/references/spring-boot/structure.md and common/.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-jvm-violations internal error, skipped ({exc})\n")
        sys.exit(0)
