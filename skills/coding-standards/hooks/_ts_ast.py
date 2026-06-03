#!/usr/bin/env python3
"""Tree-sitter AST checks for TypeScript / JavaScript.

The structural rules that need a real parse (not regex): FN-001 function body
statement count, FN-005 precise positional argument count, OD-004 hybrid-class
detection (with the OD-005 framework-boundary carve-out).

tree-sitter is REQUIRED — `bootstrap.py` installs it and refuses to wire the
hooks until it loads. The import guard below stays as a defensive safety net for
the case where this module is somehow imported without the grammars (bootstrap
bypassed, or an interpreter mismatch): `iter_ts_ast_violations` then reports
`ast_ran=False` and the caller falls back to its regex checks instead of
crashing every Write/Edit.
"""

from __future__ import annotations

import re
from typing import Iterable

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

FN_001_MAX_STATEMENTS = 20
FN_005_MAX_POSITIONAL = 3

# FN-005 carve-out — Express error middleware. Express dispatches error
# middleware BY ARITY: a handler registered with app.use() is treated as an
# error handler only when it declares exactly four parameters, so the
# (err, req, res, next) signature is the framework's contract, not an API
# choice — and the node-express structure reference mandates exactly one such
# handler per app. Grouping the params into an object would silently turn the
# middleware into a regular request handler. Matched by param shape: exactly
# four params named (e|err|error, req|request, res|response, next), each
# allowing leading underscores for intentionally-unused params and inline
# type annotations / defaults without commas or parens. A fifth param breaks
# the match, so a genuine 5-arg violation still blocks. Shared by the AST
# path here and the regex fallback in block-ts-violations.py so both paths
# agree.
EXPRESS_ERROR_MIDDLEWARE_PARAMS = re.compile(
    r"\(\s*"
    r"_*(?:e|err|error)\b[^,()]*,\s*"
    r"_*(?:req|request)\b[^,()]*,\s*"
    r"_*(?:res|response)\b[^,()]*,\s*"
    r"_*next\b[^,()]*"
    r"\)"
)


def is_express_error_middleware_params(params_text: str) -> bool:
    """True when a parameter list has the Express 4-arg error-middleware shape."""
    return EXPRESS_ERROR_MIDDLEWARE_PARAMS.search(params_text) is not None

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


def ast_backend_available() -> bool:
    """True when the tree-sitter grammars loaded — i.e. the AST checks (FN-001,
    OD-004, precise FN-005) can run. False means tree-sitter is missing, so those
    AST-only checks silently no-op and only the regex checks run."""
    return _AST_AVAILABLE


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


def _check_function_node(func_node, file_path: str) -> list[str]:
    """FN-005 (arg count) + FN-001 (body length) for one function-like node."""
    line = func_node.start_point[0] + 1
    name = _function_name(func_node)
    violations: list[str] = []

    params_node = next(
        (c for c in func_node.children if c.type == "formal_parameters"), None
    )
    if params_node is not None:
        count = _count_ts_params(params_node)
        params_text = params_node.text.decode("utf-8", errors="replace")
        if count > FN_005_MAX_POSITIONAL and not is_express_error_middleware_params(
            params_text
        ):
            violations.append(
                f"{file_path}:{line} — FN-005: `{name}` takes {count} "
                f"positional parameters; group into a typed object"
            )

    body = next(
        (c for c in func_node.children if c.type == "statement_block"), None
    )
    if body is not None:
        stmts = _statement_block_stmt_count(body)
        if stmts > FN_001_MAX_STATEMENTS:
            violations.append(
                f"{file_path}:{line} — FN-001: `{name}` has {stmts} body "
                f"statements (cap {FN_001_MAX_STATEMENTS}); extract helpers"
            )
    return violations


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
    for func_node in _walk(root, lambda n: n.type in TS_FUNCTION_NODE_TYPES):
        violations.extend(_check_function_node(func_node, file_path))

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
