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

import json
import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402

CS_EXTENSIONS = {".cs"}

# C#'s "any" escape hatch — `dynamic` bypasses static typing entirely.
DYNAMIC_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bdynamic\s+\w+\s*[=;,)(]"), "`dynamic` variable / parameter"),
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

# FN-005 — C# method signature with 4+ params. C# uses commas to separate
# typed params: `public void Foo(int a, int b, int c, int d)`.
METHOD_SIG = re.compile(
    r"\b(?:public|private|protected|internal|static|async|override|virtual|abstract|sealed)"
    r"[\w<>,\s\[\]?]*?\s+\w+\s*\(([^)]*)\)"
)


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
                    f"{file_path}:{idx} — `dynamic` is banned ({label}); "
                    f"use a concrete type or generic"
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
    for idx, line in enumerate(clean_lines, start=1):
        # Skip lines that look like method *invocations* (no return type before the
        # name). The METHOD_SIG regex requires an access/modifier keyword as anchor.
        match = METHOD_SIG.search(line)
        if not match:
            continue
        count = _count_cs_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: method takes {count} parameters; "
                f"group them into a request/options record"
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

    if Path(file_path).suffix not in CS_EXTENSIONS:
        return 0

    excluded, _pattern = is_excluded_path(file_path)
    if excluded:
        return 0

    new_content = extract_new_content(tool_name, tool_input)
    if not new_content.strip():
        return 0

    if has_generation_marker(new_content):
        return 0

    clean = strip_strings_and_comments(new_content)
    clean_lines = clean.splitlines()

    violations: list[str] = []
    violations.extend(iter_dynamic_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    header = (
        "coding-standards hook blocked this write — fix the violations and try again.\n"
        "See skills/coding-standards/references/csharp/structure.md and common/.\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
