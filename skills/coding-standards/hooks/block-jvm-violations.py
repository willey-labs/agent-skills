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
from _hook_run import block, join_wrapped_signatures, read_payload, resolve_target  # noqa: E402

JVM_EXTENSIONS = {".java", ".kt", ".kts"}

# Star imports — bring entire package into scope, hide where a type came from.
STAR_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?[\w.]+\.\*\s*;?\s*$")

# NM-006 — Hungarian notation (ISS-018). Same multi-char prefix policy as C#/TS;
# the `[A-Z][a-z]+` after the prefix guards legit names (`strategy`, `name`).
# Three shapes cover both languages: Java `Type strName` (decl/field/param),
# Kotlin `val/var strName`, and Kotlin param/property `strName: Type`.
JVM_HUNGARIAN_PREFIXES = ("str", "arr", "obj", "lst", "dct", "fn", "bln")
_JVM_HG = "|".join(sorted(JVM_HUNGARIAN_PREFIXES, key=len, reverse=True))
JVM_HUNGARIAN_PATTERNS = [
    re.compile(
        rf"\b(?:[A-Z]\w*|int|long|short|byte|double|float|boolean|char|var)"
        rf"(?:<[^>]*>)?(?:\[\])?\s+(?P<prefix>{_JVM_HG})(?P<rest>[A-Z][a-z]+\w*)\s*[=;,)]"
    ),
    re.compile(rf"\b(?:val|var)\s+(?P<prefix>{_JVM_HG})(?P<rest>[A-Z][a-z]+\w*)\b"),
    re.compile(rf"[(,]\s*(?P<prefix>{_JVM_HG})(?P<rest>[A-Z][a-z]+\w*)\s*:"),
]

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

# Java has no named arguments → line at 4 (functions.md:80). Kotlin does → 5.
# (Kotlin primary constructors / data classes aren't `fun`, so KOTLIN_FUN_SIG
# never sees them; only Kotlin methods are counted.)
JAVA_MAX_PARAMS = 4
KOTLIN_MAX_PARAMS = 5

JAVA_MODIFIER_TOKENS = frozenset({
    "public", "private", "protected", "static", "final", "abstract",
    "synchronized", "default", "native", "strictfp", "record", "sealed",
    "non", "transient", "volatile",
})


def _java_signature_kind(head: str) -> str:
    """record | constructor | method. Records are mandated DTO carriers; a
    constructor (one core token, no return type) is DI — both FN-005-exempt."""
    if re.search(r"\brecord\b", head):
        return "record"
    core = [t for t in re.findall(r"[A-Za-z_]\w*", head) if t not in JAVA_MODIFIER_TOKENS]
    return "constructor" if len(core) <= 1 else "method"


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
                    f"{file_path}:{idx} — OD-006: Kotlin `Any` is banned ({label}); "
                    f"use a concrete type or a sealed hierarchy"
                )
                break


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern in JVM_HUNGARIAN_PATTERNS:
            for match in pattern.finditer(line):
                yield (
                    f"{file_path}:{idx} — NM-006: Hungarian notation "
                    f"`{match.group('prefix')}{match.group('rest')}`; drop the `{match.group('prefix')}` prefix"
                )


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
    threshold = KOTLIN_MAX_PARAMS if is_kotlin else JAVA_MAX_PARAMS
    for lineno, text in join_wrapped_signatures(clean_lines):
        match = sig_re.search(text)
        if not match:
            continue
        if not is_kotlin:
            head = text[match.start():text.index("(", match.start())]
            if _java_signature_kind(head) in ("record", "constructor"):
                continue
        count = _count_jvm_params(match.group(1))
        if count >= threshold:
            yield (
                f"{file_path}:{lineno} — FN-005: function takes {count} parameters; "
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
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
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
