#!/usr/bin/env python3
"""PreToolUse hook — Go content checks.

Hard-blocks Write/Edit/MultiEdit on `.go` files when the new content
violates high-precision rules that regex can catch reliably:

- Star/dot imports: `import . "fmt"` — pollutes the package namespace.
- Hungarian notation (NM-006).
- Function signatures with 4+ named positional parameters (FN-005). Go's
  grouped-type syntax (`func F(a, b, c, d int)`) is also caught.

`interface{}` / `any` is an **advisory** (exit 0 + stderr), NOT a hard block.
Go genuinely needs `any` for heterogeneous JSON, reflection, and generic
constraints (`[T any]`, `map[string]any`), so hard-blocking it fights the
language — the GAP-002 corpus measured it firing on ~60% of idiomatic Go files.
It's surfaced so a lazy `any` can still be reconsidered, but it never blocks.

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

GO_EXTENSIONS = {".go"}

# Go's `any` type (alias for `interface{}` since 1.18). Both forms are the
# same smell as TS `any` / Python `Any` — escape hatch out of the type system.
ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\binterface\s*\{\s*\}"), "`interface{}`"),
    # Go param shape: `name any` (no colon). Match `<ident> any` after `(` or `,`.
    (re.compile(r"[(,]\s*\w+\s+any\b"), "parameter `name any`"),
    # Go return shape: `) any {` or `) any\n`
    (re.compile(r"\)\s*any\b"), "return type `any`"),
    # `any` as a member of a parenthesised return/param tuple: `(any, error)`,
    # `(x, any)`. The `[,)]` boundary keeps it off identifiers like `anyVar` (ISS-014).
    (re.compile(r"[(,]\s*any\s*[,)]"), "`any` in a return/param tuple"),
    # Go var/const decl: `var x any = ...`
    (re.compile(r"\b(?:var|const)\s+\w+\s+any\b"), "var/const `any` type"),
    (re.compile(r"\bmap\s*\[\s*\w+\s*\]\s*any\b"), "`map[K]any`"),
    (re.compile(r"\bmap\s*\[\s*any\s*\]"), "`map[any]V` (any key)"),  # ISS-014
    (re.compile(r"\bmap\s*\[\s*\w+\s*\]\s*interface\s*\{\s*\}"), "`map[K]interface{}`"),
    (re.compile(r"\[\s*\]\s*any\b"), "`[]any`"),
    (re.compile(r"\[\s*\]\s*interface\s*\{\s*\}"), "`[]interface{}`"),
]

# NM-006 — Hungarian notation (ISS-018). Same multi-char prefix policy as C#/TS:
# single-char prefixes are NOT matched (too many false positives), and the
# `[A-Z][a-z]+` after the prefix guards legit names (`strings`, `strconv`,
# `strategy` never match — the char after the prefix is lowercase). Three
# unambiguous decl shapes: short var (`strName :=`), var/const, and param/field
# (`(strName string`). Bare usage sites are intentionally NOT matched.
GO_HUNGARIAN_PREFIXES = ("str", "arr", "obj", "lst", "dct", "fn", "bln")
_GO_HG = "|".join(sorted(GO_HUNGARIAN_PREFIXES, key=len, reverse=True))
GO_HUNGARIAN_PATTERNS = [
    re.compile(rf"\b(?P<prefix>{_GO_HG})(?P<rest>[A-Z][a-z]+\w*)\s*:="),
    re.compile(rf"\b(?:var|const)\s+(?P<prefix>{_GO_HG})(?P<rest>[A-Z][a-z]+\w*)\b"),
    re.compile(rf"[(,]\s*(?P<prefix>{_GO_HG})(?P<rest>[A-Z][a-z]+\w*)\s"),
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

# FN-005 carve-out — Go constructor functions. `func NewService(deps...)` is the
# idiomatic dependency-wiring shape (the go-http reference mandates hand-wired
# constructors); the caller is main.go's wiring, not a hot call site. A 4+ dep
# constructor is grouped by introducing a Module/Config struct only when wiring
# genuinely hurts — that's the reference's guidance, not a hard block.
GO_CONSTRUCTOR = re.compile(r"\bfunc\s+New\w*\s*\(")


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
                    f"{file_path}:{idx} — OD-006: `any`/`interface{{}}` ({label}); idiomatic in Go "
                    f"for JSON, generics and reflection — prefer a named type or type parameter "
                    f"where one exists (advisory, not blocked)"
                )
                break


def iter_dot_import_violations(raw_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(raw_lines, start=1):
        if DOT_IMPORT.search(line):
            yield (
                f"{file_path}:{idx} — dot import banned; "
                f"use a qualified import (`import \"fmt\"`)"
            )


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern in GO_HUNGARIAN_PATTERNS:
            for match in pattern.finditer(line):
                yield (
                    f"{file_path}:{idx} — NM-006: Hungarian notation "
                    f"`{match.group('prefix')}{match.group('rest')}`; drop the `{match.group('prefix')}` prefix"
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
    # join_wrapped_signatures merges a signature split across lines so a wrapped
    # param list can't evade the count.
    for lineno, text in join_wrapped_signatures(clean_lines):
        # Methods carry a receiver in the first paren group; prefer the method
        # pattern (which captures the real param list) before the generic one.
        match = METHOD_PARAM_LINE.search(text) or FUNC_PARAM_LINE.search(text)
        if not match:
            continue
        if GO_CONSTRUCTOR.search(text):
            continue
        count = _count_go_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{lineno} — FN-005: function takes {count} parameters; "
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

    hard: list[str] = []
    hard.extend(iter_dot_import_violations(raw_lines, file_path))
    hard.extend(iter_hungarian_violations(clean_lines, file_path))
    hard.extend(iter_arg_count_violations(clean_lines, file_path))

    if hard:
        # Hard block wins; the `any` advisory resurfaces on the clean rewrite.
        return block(hard, "See skills/coding-standards/references/go-http/structure.md and common/.")

    advisory = list(iter_any_violations(clean_lines, file_path))
    if advisory:
        sys.stderr.write(
            "coding-standards (advisory: not hard-blocked, but each is still a "
            "must-fix violation — fix it or record it accepted with a reason):\n"
            + "".join(f"  - {m}\n" for m in advisory)
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-go-violations internal error, skipped ({exc})\n")
        sys.exit(0)
