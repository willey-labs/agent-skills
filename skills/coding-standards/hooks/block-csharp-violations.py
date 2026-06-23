#!/usr/bin/env python3
"""PreToolUse hook — C# / .NET content checks.

Hard-blocks Write/Edit/MultiEdit on `.cs` files when the new content
violates high-precision rules that regex can catch reliably:

- `dynamic` keyword (C#'s escape hatch out of the type system).
- Hungarian notation (`strName`, `iCount`, `oUser`, ...). C# legacy code uses
  this heavily — kept the canonical Hungarian prefix set including m_ for
  member fields.
- Method signatures with 4+ positional parameters (FN-005).

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

CS_EXTENSIONS = {".cs"}

# C#'s "any" escape hatch — `dynamic` bypasses static typing entirely.
DYNAMIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdynamic\s+\w+\s*[=;,)(]"), "`dynamic` variable / parameter"),
    (re.compile(r"\bdynamic\s*\[\s*\]"), "`dynamic[]` array"),
    (re.compile(r"\bas\s+dynamic\b"), "`as dynamic` cast"),
    (re.compile(r"\(\s*dynamic\s*\)"), "`(dynamic)` cast"),
    (re.compile(r"\bList\s*<\s*dynamic\s*>"), "`List<dynamic>`"),
    (re.compile(r"\bIEnumerable\s*<\s*dynamic\s*>"), "`IEnumerable<dynamic>`"),
    (re.compile(r"\bDictionary\s*<[^>]*,\s*dynamic\s*>"), "`Dictionary<K, dynamic>`"),
]

# Hungarian — C# legacy prefixes. m_ for member field is the most common.
HUNGARIAN_PREFIXES = ("str", "arr", "obj", "lst", "dct", "fn", "bln")
_PREFIX_ALT = "|".join(sorted(HUNGARIAN_PREFIXES, key=len, reverse=True))

# Declaration: `string strName = ...`, `var strName = ...`,
# parameter: `(string strName, ...)`
HUNGARIAN_DECL = re.compile(
    rf"\b(?:[A-Z]\w*|var|string|int|bool|long|short|byte|double|float|decimal)"
    rf"\s+(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)\s*[=;,)]"
)
# C# member-field convention `_field` is fine; `m_field` is the smell.
M_PREFIX_FIELD = re.compile(r"\b(?:private|protected|public|internal)\b[^=;]*\bm_[a-z]\w*")

# FN-005 — C# method signature. C# has named arguments, so the line sits at 5+
# (functions.md:78). `public void Foo(int a, int b, int c, int d, int e)`.
METHOD_SIG = re.compile(
    r"\b(?:public|private|protected|internal|static|async|override|virtual|abstract|sealed)"
    r"[\w<>,\s\[\]?]*?\s+\w+\s*\(([^)]*)\)"
)
CS_MAX_PARAMS = 5  # named-arg language → block at 5+

# Tokens that are modifiers/keywords, not a return type or name. Used to tell a
# constructor (`public Foo(...)` — no return type, one core token) from a method
# (`public void Foo(...)` — two core tokens).
CS_MODIFIER_TOKENS = frozenset({
    "public", "private", "protected", "internal", "static", "async", "override",
    "virtual", "abstract", "sealed", "readonly", "partial", "new", "extern",
    "unsafe", "ref", "record", "required", "file", "init",
})


def _cs_signature_kind(head: str) -> str:
    """Classify the text before the param `(` as record | constructor | method.

    Records (DTOs the structure refs mandate) and constructors (DI — the container
    is the caller, not a hot call site) are FN-005-exempt; methods are counted.
    """
    if re.search(r"\brecord\b", head):
        return "record"
    # C# 12 primary constructor: `class Foo(...)` / `struct Foo(...)`. The params
    # are DI dependencies (the container is the caller, not a hot call site) — same
    # exemption as a classic constructor and as records (ISS-008). `class`/`struct`
    # are lowercase keywords, so a method like `ProcessClass(...)` won't match.
    if re.search(r"\b(class|struct)\b", head):
        return "constructor"
    core = [t for t in re.findall(r"[A-Za-z_]\w*", head) if t not in CS_MODIFIER_TOKENS]
    return "constructor" if len(core) <= 1 else "method"


def strip_strings_and_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    # Verbatim strings @"..."
    source = re.sub(r'@"(?:[^"]|"")*"', blank, source, flags=re.DOTALL)
    # Interpolated $"..."
    source = re.sub(r'\$"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    return source


def iter_dynamic_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in DYNAMIC_RULES:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — OD-006: `dynamic` is banned ({label}); "
                    f"use a concrete type, `object` + pattern matching, or a generic"
                )
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
        if M_PREFIX_FIELD.search(line):
            yield (
                f"{file_path}:{idx} — NM-006: `m_field` Hungarian member prefix; "
                f"use `_field` or just the name"
            )


def _count_cs_params(param_list: str) -> int:
    """Count C# method parameters, ignoring commas inside generic brackets."""
    s = param_list.strip()
    if not s:
        return 0
    depth = 0
    parts = 1
    for ch in s:
        if ch == "<" or ch == "(":
            depth += 1
        elif ch == ">" or ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts += 1
    return parts


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for lineno, text in join_wrapped_signatures(clean_lines):
        # The METHOD_SIG regex requires an access/modifier keyword as anchor, so
        # plain invocations don't match.
        match = METHOD_SIG.search(text)
        if not match:
            continue
        head = text[match.start():text.index("(", match.start())]
        if _cs_signature_kind(head) in ("record", "constructor"):
            continue
        count = _count_cs_params(match.group(1))
        if count >= CS_MAX_PARAMS:
            yield (
                f"{file_path}:{lineno} — FN-005: method takes {count} parameters; "
                f"group them into a request/options record"
            )


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, CS_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target

    clean_lines = strip_strings_and_comments(new_content).splitlines()

    violations: list[str] = []
    violations.extend(iter_dynamic_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    return block(violations, "See skills/coding-standards/references/csharp/structure.md and common/.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-csharp-violations internal error, skipped ({exc})\n")
        sys.exit(0)
