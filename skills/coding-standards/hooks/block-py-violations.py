#!/usr/bin/env python3
"""PreToolUse hook — Python content checks.

Hard-blocks Write/Edit/MultiEdit on `.py` files when the new content
violates rules detectable via regex or AST. Stdlib only.

Regex checks (work on any content, including partial snippets):
- `typing.Any` usage: `: Any`, `-> Any`, `List[Any]`, `Dict[..., Any]`, ...
- Hungarian-style snake_case names: `str_name`, `arr_items`, `obj_user`, ...
- Star imports: `from x import *`

AST checks (FN-001 function body length, FN-005 precise argument count, OD-004
hybrid classes with the OD-005 framework-boundary carve-out) live in the
sibling unit `_py_ast.py` and run via stdlib `ast` when the content parses.
This file owns the regex checks and the orchestration; AST is preferred over
regex where both apply (it's precise), and the regex arg-count check stays as
the fallback so partial Edit snippets and malformed files still get checked.

Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
# Shared PreToolUse lifecycle (gate, payload read, block emit) — see _hook_run.
from _hook_run import block, cited_rules, read_payload, resolve_target  # noqa: E402
# AST checks (FN-001/FN-005/OD-004) live in a sibling unit so this file stays
# focused on the regex checks + orchestration (ST-008).
from _py_ast import iter_ast_violations  # noqa: E402

PY_EXTENSIONS = {".py", ".pyi"}

# `typing.Any` and its friends. `: Any`, `-> Any`, generic-arg Any.
ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*Any\b"), "type annotation `: Any`"),
    (re.compile(r"->\s*Any\b"), "return annotation `-> Any`"),
    (re.compile(r"\bList\s*\[\s*Any\s*\]"), "`List[Any]`"),
    (re.compile(r"\bDict\s*\[[^\]]*,\s*Any\s*\]"), "`Dict[..., Any]`"),
    (re.compile(r"\bOptional\s*\[\s*Any\s*\]"), "`Optional[Any]`"),
    (re.compile(r"\bTuple\s*\[[^\]]*Any[^\]]*\]"), "`Tuple[..., Any, ...]`"),
    (re.compile(r"\bUnion\s*\[[^\]]*\bAny\b[^\]]*\]"), "`Union[..., Any]`"),
    (re.compile(r"\bcast\s*\(\s*Any\b"), "`cast(Any, ...)`"),
]

# NM-006 — Hungarian snake_case. Same multi-char prefixes as the TS hook,
# adapted for Python conventions (snake_case with underscore separator).
HUNGARIAN_PREFIXES = ("str", "arr", "obj", "fn", "lst", "dct", "tpl", "bln")
_PREFIX_ALT = "|".join(sorted(HUNGARIAN_PREFIXES, key=len, reverse=True))

# Matches: variable assignment, function/method parameter, walrus.
# `str_name = ...`, `def foo(str_name: ...)`, `(str_name := ...)`
HUNGARIAN_ASSIGN = re.compile(
    rf"\b(?P<prefix>{_PREFIX_ALT})_(?P<rest>[a-z]\w*)\s*[:=]"
)
HUNGARIAN_PARAM = re.compile(
    rf"(?P<bound>[(,]\s*)(?P<prefix>{_PREFIX_ALT})_(?P<rest>[a-z]\w*)\s*[:,=)]"
)

# FN-005 — function with 4+ positional params (excluding self/cls).
# Catches `def foo(a, b, c, d):` and `def foo(a, b, c, d, *, e):`.
# `self` / `cls` are stripped before counting so `def m(self, a, b, c)` is fine.
FUNCTION_DEF = re.compile(r"\bdef\s+\w+\s*\(([^)]*)\)")

STAR_IMPORT = re.compile(r"^\s*from\s+\S+\s+import\s+\*")


def strip_strings_and_comments(source: str) -> str:
    """Blank out string literals and `#` comments so detectors don't fire inside them."""

    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    # Triple-quoted strings first, then `#` comments, then single-line strings.
    source = re.sub(r'"""(?:\\.|[^"\\]|"(?!""))*"""', blank, source, flags=re.DOTALL)
    source = re.sub(r"'''(?:\\.|[^'\\]|'(?!''))*'''", blank, source, flags=re.DOTALL)
    source = re.sub(r"#[^\n]*", blank, source)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def iter_any_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in ANY_RULES:
            if pattern.search(line):
                yield f"{file_path}:{idx} — OD-006: `Any` is banned ({label}); name the type, or use a precise union / generic"
                break


def iter_hungarian_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for match in HUNGARIAN_ASSIGN.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian-style name `{prefix}_{rest}`; "
                f"drop the `{prefix}_` prefix"
            )
        for match in HUNGARIAN_PARAM.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian-style parameter `{prefix}_{rest}`; "
                f"drop the `{prefix}_` prefix"
            )


def _count_py_params(param_list: str) -> int:
    """Count Python positional parameters, ignoring self/cls and **kwargs marker.

    `self, a, b, c` → 3
    `a, b, c, d` → 4
    `a, b, *, c, d` → 4 (everything before `*` is positional-capable)
    `a: int = 1, b: str = ""` → 2 (default values don't reduce arg count)
    """
    s = param_list.strip()
    if not s:
        return 0
    # Strip nested brackets so generic annotations don't break comma split.
    depth = 0
    flat = []
    for ch in s:
        if ch in "[(<":
            depth += 1
            flat.append(" ")
            continue
        if ch in "])>":
            depth = max(0, depth - 1)
            flat.append(" ")
            continue
        if depth > 0:
            flat.append(" ")
        else:
            flat.append(ch)
    s = "".join(flat)

    parts = [p.strip() for p in s.split(",") if p.strip()]
    # Drop self / cls and the bare `*` marker.
    parts = [p for p in parts if p not in ("self", "cls", "*")]
    # Drop **kwargs entries — they're a single bucket, not n positional args.
    parts = [p for p in parts if not p.startswith("**")]
    return len(parts)


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    # Regex fallback (AST parse failed — partial Edit snippet). Python has named
    # arguments, so the line sits at 5+ (functions.md:78); the precise AST path
    # also drops FastAPI bindings and pytest fixtures, which this coarse pass can't.
    for idx, line in enumerate(clean_lines, start=1):
        match = FUNCTION_DEF.search(line)
        if not match:
            continue
        if re.search(r"\bdef\s+test_", line):
            continue
        count = _count_py_params(match.group(1))
        if count >= 5:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} arguments; "
                f"group them into a dataclass / TypedDict / parameter object"
            )


def iter_star_import_violations(raw_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(raw_lines, start=1):
        if STAR_IMPORT.search(line):
            yield (
                f"{file_path}:{idx} — star import (`from x import *`) banned; "
                f"name what you import"
            )


def collect_violations(new_content: str, file_path: str) -> list[str]:
    """Run every Python check over the new content and return the violation lines."""
    clean_lines = strip_strings_and_comments(new_content).splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_star_import_violations(raw_lines, file_path))

    # AST checks supersede the regex arg-count check when the file parses.
    # When parse fails (typically partial Edit snippets), fall back to regex.
    ast_iter, ast_ok = iter_ast_violations(new_content, file_path)
    violations.extend(ast_iter)
    if not ast_ok:
        violations.extend(iter_arg_count_violations(clean_lines, file_path))
    return violations


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, PY_EXTENSIONS)
    if target is None:
        return 0
    file_path, new_content = target

    violations = collect_violations(new_content, file_path)
    if not violations:
        return 0

    see = f"See skills/coding-standards/references/common/ for cited rules ({cited_rules(violations)})."
    return block(violations, see)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-py-violations internal error, skipped ({exc})\n")
        sys.exit(0)
