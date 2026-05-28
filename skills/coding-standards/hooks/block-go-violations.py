#!/usr/bin/env python3
"""PreToolUse hook — Go content checks.

Hard-blocks Write/Edit/MultiEdit on `.go` files when the new content
violates high-precision rules that regex can catch reliably:

- `interface{}` and bare `any` usage in declarations (Go's "any" type — same
  smell as TS `any` / Python `Any`).
- Star/dot imports: `import . "fmt"` — pollutes the package namespace.
- Function signatures with 4+ named positional parameters (FN-005). Go's
  grouped-type syntax (`func F(a, b, c, d int)`) is also caught.

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

GO_EXTENSIONS = {".go"}

# Go's `any` type (alias for `interface{}` since 1.18). Both forms are the
# same smell as TS `any` / Python `Any` — escape hatch out of the type system.
ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\binterface\s*\{\s*\}"), "`interface{}`"),
    # Go param shape: `name any` (no colon). Match `<ident> any` after `(` or `,`.
    (re.compile(r"[(,]\s*\w+\s+any\b"), "parameter `name any`"),
    # Go return shape: `) any {` or `) any\n`
    (re.compile(r"\)\s*any\b"), "return type `any`"),
    # Go var/const decl: `var x any = ...`
    (re.compile(r"\b(?:var|const)\s+\w+\s+any\b"), "var/const `any` type"),
    (re.compile(r"\bmap\s*\[\s*\w+\s*\]\s*any\b"), "`map[K]any`"),
    (re.compile(r"\bmap\s*\[\s*\w+\s*\]\s*interface\s*\{\s*\}"), "`map[K]interface{}`"),
    (re.compile(r"\[\s*\]\s*any\b"), "`[]any`"),
    (re.compile(r"\[\s*\]\s*interface\s*\{\s*\}"), "`[]interface{}`"),
]

# Dot/star import — `import . "fmt"` brings every name into local scope.
DOT_IMPORT = re.compile(r'^\s*(?:import\s+)?\.\s+"[^"]+"\s*$')

# FN-005 — Go signature with 4+ parameters. Go has two shapes:
#   func Foo(a int, b int, c int, d int)
#   func Foo(a, b, c, d int)
# Both should trigger. Count commas inside the outermost parens of the func sig.
FUNC_PARAM_LINE = re.compile(r"\bfunc\b[^(]*\(([^)]*)\)")


def strip_strings_and_comments(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"`[^`]*`", blank, source, flags=re.DOTALL)  # raw strings
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    return source


def iter_any_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in ANY_RULES:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — `interface{{}}` / `any` is banned ({label}); "
                    f"use a named type or type parameter"
                )
                break


def iter_dot_import_violations(raw_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(raw_lines, start=1):
        if DOT_IMPORT.search(line):
            yield (
                f"{file_path}:{idx} — dot import banned; "
                f"use a qualified import (`import \"fmt\"`)"
            )


def _count_go_params(param_list: str) -> int:
    """Count Go function parameters. Handles both grouped (`a, b int`) and
    individually-typed forms. Returns the number of *names*, not groups.

    `a int, b int` → 2
    `a, b int` → 2
    `a, b, c, d int` → 4
    `ctx context.Context, req *Request` → 2
    """
    s = param_list.strip()
    if not s:
        return 0
    # Strip nested parens (channel directions, func types) — replace with @
    # so the comma split is preserved without inner commas leaking.
    depth = 0
    flat = []
    for ch in s:
        if ch == "(":
            depth += 1
            flat.append("@")
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            flat.append("@")
            continue
        if depth > 0:
            flat.append("@")
        else:
            flat.append(ch)
    s = "".join(flat)

    # Each top-level comma separates either a name (`a, b int`) or a
    # full `name type` pair. Counting commas + 1 gives the param-name count.
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return len(parts)


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        match = FUNC_PARAM_LINE.search(line)
        if not match:
            continue
        count = _count_go_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} parameters; "
                f"group them into a request struct"
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

    if Path(file_path).suffix not in GO_EXTENSIONS:
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
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_dot_import_violations(raw_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    header = (
        "coding-standards hook blocked this write — fix the violations and try again.\n"
        "See skills/coding-standards/references/go-http/structure.md and common/.\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
