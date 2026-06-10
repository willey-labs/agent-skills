#!/usr/bin/env python3
"""Tree-sitter parse + walk for TypeScript / JavaScript (the orchestration half).

Loads the grammars, picks the right one per extension, walks the tree, and feeds
each node to the checks in the sibling `_ts_node_checks.py` (FN-001/FN-005/OD-004
+ the Express / DI / OD-005 carve-outs). Splitting parse-and-walk from the node
predicates keeps each file to one job (ST-008).

tree-sitter is REQUIRED — `bootstrap.py` installs it and refuses to wire the
hooks until it loads. The import guard below stays as a defensive safety net for
the case where this module is imported without the grammars (bootstrap bypassed
or an interpreter mismatch): `iter_ts_ast_violations` then reports `ast_ran=False`
and the caller falls back to its regex checks instead of crashing every write.

`is_express_error_middleware_params` is re-exported here so the regex fallback in
block-ts-violations.py keeps importing it from `_ts_ast` unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

# Be importable however we're loaded — by block-ts (which sets the path) or by a
# test/tool that loads this file directly. Self-insert so the sibling import below
# resolves either way.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ts_node_checks import (  # noqa: E402, F401  (is_express_* re-exported for block-ts)
    TS_FUNCTION_NODE_TYPES,
    check_function_node,
    class_extends_boundary_parent,
    class_has_accessor_and_business_methods,
    function_name,
    is_express_error_middleware_params,
)

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
    # a version-skewed binding changes the Language()/Parser() API. Either way,
    # fall back to regex-only rather than crashing the hook on every write.
    _AST_AVAILABLE = False
    _TS_LANGUAGE = _TSX_LANGUAGE = _JS_LANGUAGE = None


def ast_backend_available() -> bool:
    """True when the tree-sitter grammars loaded — i.e. the AST checks can run."""
    return _AST_AVAILABLE


def _pick_ts_language(ext: str):
    """Pick the grammar for the extension, or None if unsupported / unavailable."""
    if not _AST_AVAILABLE:
        return None
    if ext in (".tsx", ".jsx"):
        return _TSX_LANGUAGE
    if ext in (".ts", ".mts", ".cts"):
        return _TS_LANGUAGE
    if ext in (".js", ".mjs", ".cjs"):
        return _JS_LANGUAGE or _TS_LANGUAGE
    # SFCs (.vue/.svelte) — we don't extract the <script> block yet. Skip AST.
    return None


def _walk(node, predicate):
    """Yield every descendant where predicate(node) is True."""
    if predicate(node):
        yield node
    for child in node.children:
        yield from _walk(child, predicate)


def iter_ts_ast_violations(
    source: str, file_path: str, ext: str
) -> tuple[Iterable[str], bool]:
    """Run AST checks. Returns (violations_iter, ast_ran). ast_ran=False means
    tree-sitter is unavailable, the extension isn't supported, or parsing failed —
    caller falls back to regex."""
    language = _pick_ts_language(ext)
    if language is None:
        return iter([]), False

    parser = tree_sitter.Parser(language)
    source_bytes = source.encode("utf-8", errors="replace")
    try:
        tree = parser.parse(source_bytes)
    except Exception:
        return iter([]), False

    root = tree.root_node
    if not root.children:
        return iter([]), True

    violations: list[str] = []
    for func_node in _walk(root, lambda n: n.type in TS_FUNCTION_NODE_TYPES):
        violations.extend(check_function_node(func_node, file_path))

    for cls in _walk(
        root, lambda n: n.type in ("class_declaration", "abstract_class_declaration")
    ):
        if class_extends_boundary_parent(cls):
            continue
        if class_has_accessor_and_business_methods(cls):
            line = cls.start_point[0] + 1
            cls_name = function_name(cls)
            violations.append(
                f"{file_path}:{line} — OD-004: `{cls_name}` is a hybrid class "
                f"(mixes get/set accessors with business methods); split data "
                f"carrier from behavior owner"
            )

    return iter(violations), True
