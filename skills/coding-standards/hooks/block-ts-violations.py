#!/usr/bin/env python3
"""PreToolUse hook — TypeScript / JavaScript content checks.

Hard-blocks Write/Edit/MultiEdit when the new file content violates rules
detectable via regex or AST.

Regex checks (always on — work on any content, including partial Edit snippets):
- `any` type (TS only): `: any`, `<any>`, `as any`, `any[]`, ...
- Hungarian notation (NM-006): `strName`, `arrItems`, ...
- Deep imports past public API (ST-003): `@/foo/bar/baz`
- Parent traversal `../../../` (universal smell)

AST checks (only if `tree-sitter` and grammars are installed; otherwise falls
back to regex):
- FN-001: function body statement count (>20 stmts flagged)
- FN-005: precise positional argument count (including arrows, methods,
  generators; rest params count as 1, destructured params count as 1)
- OD-004: hybrid classes — class has BOTH `get`/`set` accessor methods AND
  non-trivial business methods. Classes with framework-boundary parent names
  (Entity, Model, BaseModel, Repository decorators, etc.) are exempt per OD-005.

Install AST support: `pip install tree-sitter tree-sitter-typescript tree-sitter-javascript`.
Without it, the hook still works — just with regex-only precision.

Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402
from _structure import is_check_enabled  # noqa: E402

# Tree-sitter is optional. Import lazily so the hook works without it.
try:
    import tree_sitter
    import tree_sitter_typescript
    try:
        import tree_sitter_javascript
        _JS_LANGUAGE = tree_sitter.Language(tree_sitter_javascript.language())
    except Exception:
        # ImportError when the grammar isn't installed; TypeError/AttributeError
        # when an installed-but-incompatible version changes the Language() API.
        _JS_LANGUAGE = None
    _TS_LANGUAGE = tree_sitter.Language(tree_sitter_typescript.language_typescript())
    _TSX_LANGUAGE = tree_sitter.Language(tree_sitter_typescript.language_tsx())
    _AST_AVAILABLE = True
except Exception:
    # ImportError when tree-sitter isn't installed; TypeError/AttributeError when
    # a version-skewed binding changes the Language()/Parser() API (the modern
    # `Language(capsule)` form raises on bindings <0.22). Either way, fall back
    # to regex-only checks rather than crashing the hook on every Write/Edit.
    _AST_AVAILABLE = False
    _TS_LANGUAGE = _TSX_LANGUAGE = _JS_LANGUAGE = None

TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}
# Vue SFCs and Svelte components carry TS/JS in `<script>` blocks. The rules
# fire on that script content; templates rarely look like `function f(a,b,c,d)`
# or `from "@/foo/bar/baz"`, so the false-positive rate is acceptably low.
VUE_LIKE_EXTENSIONS = {".vue", ".svelte"}

ANY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r":\s*any\b"), "type annotation `: any`"),
    (re.compile(r"<\s*any\s*[,>]"), "generic argument `<any>`"),
    (re.compile(r"\bas\s+any\b"), "type assertion `as any`"),
    (re.compile(r"\bany\s*\[\]"), "array type `any[]`"),
    (re.compile(r"\bArray\s*<\s*any\s*>"), "array type `Array<any>`"),
    (re.compile(r"\bPromise\s*<\s*any\s*>"), "promise type `Promise<any>`"),
]

# NM-006 — Hungarian notation. Single-char prefixes (b, i, n, o, a) were
# excluded because they false-positive on legitimate names (aUser, iValue).
# The remaining prefixes have effectively no false-positive rate.
HUNGARIAN_PREFIXES = ("str", "arr", "obj", "fn", "sz", "psz", "bln", "lp", "lpsz")
_PREFIX_ALT = "|".join(sorted(HUNGARIAN_PREFIXES, key=len, reverse=True))

HUNGARIAN_DECL = re.compile(
    rf"\b(?:let|const|var|function|async\s+function)\s+"
    rf"(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)"
)
HUNGARIAN_PARAM = re.compile(
    rf"(?P<bound>[(,]\s*)"
    rf"(?P<prefix>{_PREFIX_ALT})(?P<rest>[A-Z][a-z]+\w*)\s*[:?=,)]"
)

# FN-005 — function signature with 4+ positional arguments.
# Catches: function foo(a, b, c, d) / const foo = (a, b, c, d) => ...
# Allows the object-param escape hatch: function foo({ a, b, c, d }).
FUNCTION_ARG_COUNT_PATTERNS = [
    re.compile(
        r"\b(?:function|async\s+function)\s+\w+\s*"
        r"\(\s*(?!\{)[^){]*?,[^){]*?,[^){]*?,[^){]*?\)"
    ),
    re.compile(
        r"\b(?:const|let|var)\s+\w+\s*[:=][^=]*?=\s*"
        r"\(\s*(?!\{)[^){]*?,[^){]*?,[^){]*?,[^){]*?\)\s*=>"
    ),
]

# ST-003 — deep imports past a folder's public entry.
# `@/foo/bar` is fine (capability + use case). `@/foo/bar/baz` reaches past.
DEEP_IMPORT_PATTERN = re.compile(
    r"""from\s+['"]@/[a-z][a-z0-9-]*/[a-z][a-z0-9-]*/[a-z][a-z0-9-]*"""
)

PARENT_TRAVERSAL_PATTERN = re.compile(r"""from\s+['"](\.\./){3,}""")


def strip_strings_and_comments(source: str) -> str:
    """Blank out strings and comments so detectors don't match inside them.

    Replaces matched ranges with same-length whitespace so line/column
    offsets stay stable.
    """

    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"`(?:\\.|[^`\\])*`", blank, source, flags=re.DOTALL)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def iter_any_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern, label in ANY_RULES:
            if pattern.search(line):
                yield f"{file_path}:{idx} — `any` is banned ({label})"
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
        for match in HUNGARIAN_PARAM.finditer(line):
            prefix = match.group("prefix")
            rest = match.group("rest")
            yield (
                f"{file_path}:{idx} — NM-006: Hungarian notation `{prefix}{rest}` "
                f"(parameter); drop the `{prefix}` prefix"
            )


def iter_arg_count_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        for pattern in FUNCTION_ARG_COUNT_PATTERNS:
            if pattern.search(line):
                yield (
                    f"{file_path}:{idx} — FN-005: function takes 4+ positional arguments; "
                    f"group them into a typed object parameter"
                )
                break


def iter_import_violations(
    clean_lines: list[str], file_path: str, check_deep: bool = True
) -> Iterable[str]:
    for idx, line in enumerate(clean_lines, start=1):
        if check_deep and DEEP_IMPORT_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — ST-003: deep import past folder's public API; "
                f"import from the capability's index.ts instead"
            )
        if PARENT_TRAVERSAL_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — parent traversal of 3+ levels; "
                f"use a path alias (e.g. @/) or move the file closer to its caller"
            )


# ─────────────────────────────────────────────────────────────────────────────
# AST checks via tree-sitter (optional). Only fire when grammars are installed
# AND the new content parses (i.e., a full module, not a partial snippet).
# ─────────────────────────────────────────────────────────────────────────────

FN_001_MAX_STATEMENTS = 20
FN_005_MAX_POSITIONAL = 3

# Tree-sitter node types that represent a function-like declaration we want to check.
TS_FUNCTION_NODE_TYPES = {
    "function_declaration",
    "function_expression",
    "function",  # newer tree-sitter-typescript uses this
    "arrow_function",
    "method_definition",
    "method_signature",
    "generator_function_declaration",
}

# Names of parent classes that flag a class as framework-boundary (OD-005
# carve-out). If a class extends any of these (in any form), OD-004 doesn't
# apply.
OD_005_BOUNDARY_PARENTS = {
    "Entity", "Model", "BaseModel", "BaseEntity", "Repository", "Schema",
    "Document", "Component", "Controller", "Service", "Module", "Resource",
    "Resolver", "Pipe", "Guard", "Interceptor", "Filter", "Middleware",
    "TypeOrmEntity", "MongooseModel", "PrismaModel",
}


def _pick_ts_language(ext: str):
    """Pick the right grammar for the file extension. Returns None if no
    grammar is installed for this extension.
    """
    if not _AST_AVAILABLE:
        return None
    if ext in (".tsx", ".jsx"):
        return _TSX_LANGUAGE
    if ext in (".ts", ".mts", ".cts"):
        return _TS_LANGUAGE
    if ext in (".js", ".mjs", ".cjs"):
        # The TS grammar parses JS as a superset; tree-sitter-javascript is
        # not strictly required but is more precise for JS-only code.
        return _JS_LANGUAGE or _TS_LANGUAGE
    if ext in (".vue", ".svelte"):
        # SFCs — we don't try to extract the <script> block yet. Skip AST.
        return None
    return None


def _count_ts_params(formal_parameters_node) -> int:
    """Count positional parameters in a tree-sitter formal_parameters node.

    Counts every parameter as 1 — including:
    - required_parameter
    - optional_parameter (`x?: T`)
    - rest_pattern (`...args`) — counts as 1 (single bucket)
    - object/array destructured params — count as 1 (single bucket)

    Excludes punctuation children (parens, commas).
    """
    excluded_types = {"(", ")", ",", ":"}
    return sum(
        1
        for child in formal_parameters_node.children
        if child.type not in excluded_types
    )


def _statement_block_stmt_count(body_node) -> int:
    """Count statements in a statement_block node, excluding braces and
    leading docstring-style string literal (rare in TS but possible).
    """
    excluded_types = {"{", "}", "comment"}
    stmts = [c for c in body_node.children if c.type not in excluded_types]
    if (
        stmts
        and stmts[0].type == "expression_statement"
        and len(stmts[0].children) == 1
        and stmts[0].children[0].type == "string"
    ):
        stmts = stmts[1:]
    return len(stmts)


def _function_name(node) -> str:
    """Best-effort function name extraction for diagnostics."""
    for child in node.children:
        if child.type in ("identifier", "property_identifier"):
            return child.text.decode("utf-8", errors="replace")
    return "<anonymous>"


def _class_extends_boundary_parent(class_node) -> bool:
    """OD-005 carve-out — class extends a known framework-boundary parent
    or has decorators that mark it as a framework-boundary class.
    """
    # Look for decorators on the class declaration. In tree-sitter-typescript a
    # class `decorator` node is a CHILD of the class_declaration; older/other
    # grammar versions may place it as a preceding sibling. Check both so the
    # OD-005 carve-out is robust to grammar drift.
    decorators = []
    candidate_nodes = list(class_node.children)
    if class_node.parent:
        candidate_nodes += list(class_node.parent.children)
    for node in candidate_nodes:
        if node.type == "decorator":
            decorators.append(node.text.decode("utf-8", errors="replace"))
    if any(
        d.lstrip("@").split("(")[0] in OD_005_BOUNDARY_PARENTS
        for d in decorators
    ):
        return True

    # Look at the `extends` clause.
    for child in class_node.children:
        if child.type == "class_heritage":
            for c in child.children:
                if c.type == "extends_clause":
                    for e in c.children:
                        if e.type == "identifier":
                            name = e.text.decode("utf-8", errors="replace")
                            if name in OD_005_BOUNDARY_PARENTS:
                                return True
        if child.type == "extends_clause":
            for c in child.children:
                if c.type == "identifier":
                    if c.text.decode("utf-8", errors="replace") in OD_005_BOUNDARY_PARENTS:
                        return True
    return False


def _class_has_accessor_and_business_methods(class_node) -> bool:
    """OD-004 — class has BOTH get/set accessor methods AND non-trivial
    business methods (not constructors, not pure pass-through, not accessors).
    """
    has_accessor = False
    business_methods = 0
    for child in class_node.children:
        if child.type != "class_body":
            continue
        for member in child.children:
            if member.type != "method_definition":
                continue
            # Check if this method has `get` or `set` keyword
            has_get_or_set = any(c.type in ("get", "set") for c in member.children)
            if has_get_or_set:
                has_accessor = True
                continue

            # Method name
            name = _function_name(member)
            if name == "constructor":
                continue

            # Body statement count — trivial methods (<=1 statement) don't
            # count as business logic; they're likely pass-through accessors.
            body = next(
                (c for c in member.children if c.type == "statement_block"), None
            )
            if body is None:
                continue
            if _statement_block_stmt_count(body) <= 1:
                continue
            business_methods += 1
    return has_accessor and business_methods >= 1


def _walk(node, predicate):
    """Yield every descendant where predicate(node) is True."""
    if predicate(node):
        yield node
    for child in node.children:
        yield from _walk(child, predicate)


def iter_ts_ast_violations(
    source: str, file_path: str, ext: str
) -> tuple[Iterable[str], bool]:
    """Run AST checks. Returns (violations_iter, ast_ran).

    ast_ran=False means tree-sitter isn't installed, the extension isn't
    supported, or parsing failed. Caller falls back to regex when False.
    """
    language = _pick_ts_language(ext)
    if language is None:
        return iter([]), False

    parser = tree_sitter.Parser(language)
    source_bytes = source.encode("utf-8", errors="replace")
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return iter([]), False

    # tree-sitter is permissive — it will produce an AST even with errors.
    # We don't try to detect "had errors" because partial snippets may parse
    # mostly-OK and we still want the checks. If the root has no children,
    # nothing to check anyway.
    root = tree.root_node
    if not root.children:
        return iter([]), True

    violations: list[str] = []

    # FN-001 and FN-005 — walk every function-like node
    for fn_node in _walk(root, lambda n: n.type in TS_FUNCTION_NODE_TYPES):
        line = fn_node.start_point[0] + 1
        name = _function_name(fn_node)

        # Find formal_parameters child
        params_node = next(
            (c for c in fn_node.children if c.type == "formal_parameters"), None
        )
        if params_node is not None:
            count = _count_ts_params(params_node)
            if count > FN_005_MAX_POSITIONAL:
                violations.append(
                    f"{file_path}:{line} — FN-005: `{name}` takes {count} "
                    f"positional parameters; group into a typed object"
                )

        # Find statement_block body
        body = next(
            (c for c in fn_node.children if c.type == "statement_block"), None
        )
        if body is not None:
            stmts = _statement_block_stmt_count(body)
            if stmts > FN_001_MAX_STATEMENTS:
                violations.append(
                    f"{file_path}:{line} — FN-001: `{name}` has {stmts} body "
                    f"statements (cap {FN_001_MAX_STATEMENTS}); extract helpers"
                )

    # OD-004 — walk class declarations
    for cls in _walk(root, lambda n: n.type in ("class_declaration", "abstract_class_declaration")):
        if _class_extends_boundary_parent(cls):
            continue
        if _class_has_accessor_and_business_methods(cls):
            line = cls.start_point[0] + 1
            cls_name = _function_name(cls)
            violations.append(
                f"{file_path}:{line} — OD-004: `{cls_name}` is a hybrid class "
                f"(mixes get/set accessors with business methods); split data "
                f"carrier from behavior owner"
            )

    return iter(violations), True


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

    ext = Path(file_path).suffix
    is_ts = ext in TS_EXTENSIONS
    is_js = ext in JS_EXTENSIONS
    is_vue_like = ext in VUE_LIKE_EXTENSIONS
    if not (is_ts or is_js or is_vue_like):
        return 0
    # Treat Vue/Svelte SFCs as TS for the purpose of `any`-type checks —
    # they're typically `<script lang="ts">` in modern setups.
    if is_vue_like:
        is_ts = True

    # Exclusion check by path — shadcn/ui, generated code, vendored, etc.
    excluded, _pattern = is_excluded_path(file_path)
    if excluded:
        return 0

    new_content = extract_new_content(tool_name, tool_input)
    if not new_content.strip():
        return 0

    # Exclusion check by content marker — `@generated`, `DO NOT EDIT`, etc.
    if has_generation_marker(new_content):
        return 0

    # Content-token checks run on cleaned text (no strings/comments).
    # Import checks need raw lines — the import path lives inside the
    # quoted module specifier, which the cleaner would have blanked out.
    clean = strip_strings_and_comments(new_content)
    clean_lines = clean.splitlines()
    raw_lines = new_content.splitlines()

    violations: list[str] = []
    if is_ts:
        violations.extend(iter_any_violations(clean_lines, file_path))
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    # ST-003 deep-import is structure-dependent: a custom project with no barrels
    # turns it off via `.coding-standards-structure`. Parent-traversal stays on.
    violations.extend(
        iter_import_violations(
            raw_lines, file_path, check_deep=is_check_enabled("deep-import", file_path)
        )
    )

    # AST checks supersede regex arg-count when tree-sitter is available
    # and the content parses. Otherwise fall back to regex.
    ast_iter, ast_ran = iter_ts_ast_violations(new_content, file_path, ext)
    violations.extend(ast_iter)
    if not ast_ran:
        violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    # Cite only the rules that actually fired, derived from the violation lines
    # (the `any` ban carries no code, so it just isn't listed).
    cited = sorted({
        match.group(0)
        for v in violations
        for match in re.finditer(r"\b(?:FN|NM|OD|ST|EH|FMT|DP)-\d+\b", v)
    })
    cited_str = ", ".join(cited) if cited else "the rule references"
    header = (
        "coding-standards hook blocked this write — fix the violations and try again.\n"
        f"See skills/coding-standards/references/common/ for cited rules ({cited_str}).\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error (e.g. a tree-sitter API change
        # that slips past the load guard) block a legitimate write. Fail OPEN:
        # exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-ts-violations internal error, skipped ({exc})\n")
        sys.exit(0)
