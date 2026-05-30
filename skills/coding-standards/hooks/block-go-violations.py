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

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
# Shared PreToolUse lifecycle (gate, payload read, block emit) — see _hook_run.
from _hook_run import block, read_payload, resolve_target  # noqa: E402

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

# FN-005 — Go signature with 4+ parameters. Go has three shapes:
#   func Foo(a int, b int, c int, d int)   — named function
#   func Foo(a, b, c, d int)               — grouped-type named function
#   func (r *Recv) Foo(a, b, c, d int)     — method (receiver before the name)
#   func(a, b, c, d int) { ... }           — anonymous function literal
# A method's FIRST paren group is the RECEIVER, not the params — matching the
# first paren after `func` would capture the receiver and miss the real param
# list. So try the method shape first (receiver + name + params, capturing the
# SECOND paren group); fall back to the first-paren shape for named/anonymous
# functions (which have no receiver).
METHOD_PARAM_LINE = re.compile(r"\bfunc\s*\([^)]*\)\s*\w+\s*\(([^)]*)\)")
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
        # Methods carry a receiver in the first paren group; prefer the method
        # pattern (which captures the real param list) before the generic one.
        match = METHOD_PARAM_LINE.search(line) or FUNC_PARAM_LINE.search(line)
        if not match:
            continue
        count = _count_go_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} parameters; "
                f"group them into a request struct"
            )


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, GO_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target

    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_dot_import_violations(raw_lines, file_path))
    violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    return block(violations, "See skills/coding-standards/references/go-http/structure.md and common/.")


if __name__ == "__main__":
    sys.exit(main())
