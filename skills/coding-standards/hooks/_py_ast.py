#!/usr/bin/env python3
"""AST checks for Python — the rules that need a real parse, via stdlib `ast`.

FN-001 (function body statement count), FN-005 (precise positional arg count,
excluding self/cls and the *args/**kwargs buckets), and OD-004 (hybrid classes,
with the OD-005 framework-boundary carve-out).

`iter_ast_violations` returns `ast_succeeded=False` when `ast.parse` fails
(typically a partial Edit snippet); the caller then falls back to its regex
arg-count check instead.
"""

from __future__ import annotations

import ast
from typing import Iterable

# FN-001 — function bodies should be small. Statement count (not line count)
# because Python's blocks compress vertically.
FN_001_MAX_STATEMENTS = 20

# FN-005 — positional arg threshold. Python has named arguments, so per
# functions.md:78 the line sits at 5+ (named langs soften; positional langs hit
# 4). MAX is the last *allowed* count, so 4 → a 5th arg blocks.
FN_005_MAX_POSITIONAL = 4

# FastAPI declares per-request inputs as PARAMETERS bound to these markers
# (`db = Depends(get_db)`, `q: str = Query(...)`). Each is a framework binding,
# not an API-design argument the caller passes — so they don't count toward
# FN-005's mental-load tally. Mirrors the Express error-middleware carve-out.
FASTAPI_PARAM_MARKERS = frozenset({
    "Depends", "Security", "Query", "Path", "Body", "Header", "Cookie",
    "Form", "File", "Form", "Param",
})

# Names that look like framework-boundary class parents — exempt from OD-004
# per OD-005 (Django Model, Pydantic BaseModel, DRF Serializer, Form, View,
# Tortoise Model, SQLAlchemy DeclarativeBase, etc.).
OD_005_FRAMEWORK_BASES = frozenset({
    "Model", "BaseModel", "Schema", "Serializer", "ModelSerializer",
    "Form", "ModelForm", "View", "APIView", "ViewSet", "ModelViewSet",
    "GenericViewSet", "Document", "EmbeddedDocument", "DeclarativeBase",
    "Base", "SQLModel", "TortoiseModel", "BaseSettings", "BaseConfig",
    "Field", "TypedDict", "NamedTuple", "Enum", "IntEnum", "StrEnum",
    "Protocol", "Generic",
})


def _is_fastapi_marker(node: ast.expr | None) -> bool:
    """True when a parameter's default is a FastAPI binding call
    (`Depends(...)`, `Query(...)`, `body: X = Body(...)`, ...)."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in FASTAPI_PARAM_MARKERS
    if isinstance(func, ast.Attribute):
        return func.attr in FASTAPI_PARAM_MARKERS
    return False


def _fastapi_bound_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Parameter names bound to a FastAPI marker default — excluded from the
    FN-005 count. Defaults align to the tail of (posonly+args); kw_defaults
    align 1:1 with kwonlyargs."""
    bound: set[str] = set()
    positional = list(node.args.posonlyargs) + list(node.args.args)
    defaults = list(node.args.defaults)
    if defaults:
        for arg, default in zip(positional[-len(defaults):], defaults):
            if _is_fastapi_marker(default):
                bound.add(arg.arg)
    for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
        if _is_fastapi_marker(default):
            bound.add(arg.arg)
    return bound


def _count_ast_positional(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count positional-capable parameters per FN-005's intent.

    Includes posonly_args + args. Excludes self/cls, the vararg (*args) and
    kwarg (**kwargs) buckets (one bucket each, not n args), and FastAPI
    framework-binding parameters. Keyword-only args (after `*`) are counted
    because they still raise the mental load FN-005 is about.
    """
    bound = _fastapi_bound_names(node)
    positional = list(node.args.posonlyargs) + list(node.args.args)
    kwonly = list(node.args.kwonlyargs)
    names = [a.arg for a in positional + kwonly]
    return sum(1 for n in names if n not in ("self", "cls") and n not in bound)


def _function_body_statement_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count statements in the body, skipping docstrings."""
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    return len(body)


def _iter_functions(tree: ast.AST) -> Iterable[ast.FunctionDef | ast.AsyncFunctionDef]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node


def _iter_classes(tree: ast.AST) -> Iterable[ast.ClassDef]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            yield node


def _class_extends_framework_base(node: ast.ClassDef) -> bool:
    """Heuristic OD-005 carve-out — class inherits from a known framework base."""
    for base in node.bases:
        # Handle `Model`, `models.Model`, `pydantic.BaseModel`, etc.
        if isinstance(base, ast.Name) and base.id in OD_005_FRAMEWORK_BASES:
            return True
        if isinstance(base, ast.Attribute) and base.attr in OD_005_FRAMEWORK_BASES:
            return True
        if isinstance(base, ast.Subscript) and isinstance(base.value, ast.Name):
            if base.value.id in OD_005_FRAMEWORK_BASES:
                return True
    return False


def _class_has_property_and_business_methods(node: ast.ClassDef) -> bool:
    """OD-004 detection — class has BOTH @property getters/setters AND
    non-trivial business methods (not dunders, not pure pass-through).
    """
    has_property = False
    business_methods: list[str] = []
    for item in node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decorator_names = []
            for dec in item.decorator_list:
                if isinstance(dec, ast.Name):
                    decorator_names.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorator_names.append(dec.attr)
            if "property" in decorator_names:
                has_property = True
                continue
            # `<name>.setter` decorator counts as property machinery too.
            if any(d.endswith("setter") for d in decorator_names):
                has_property = True
                continue
            # Dunder methods (__init__, __repr__, ...) aren't business methods.
            if item.name.startswith("__") and item.name.endswith("__"):
                continue
            # Trivial pass-through / one-statement methods aren't business
            # logic — likely getters/setters in disguise.
            if _function_body_statement_count(item) <= 1:
                continue
            business_methods.append(item.name)
    return has_property and len(business_methods) >= 1


def iter_ast_violations(source: str, file_path: str) -> tuple[Iterable[str], bool]:
    """Run AST checks. Returns (violations_iter, ast_succeeded).

    Caller uses `ast_succeeded` to decide whether to fall back to the
    regex arg-count check (which is less precise but works on snippets).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return iter([]), False

    violations: list[str] = []

    # FN-005 (precise) + FN-001 (statement count)
    for func in _iter_functions(tree):
        # pytest test functions take fixtures by name (the fixture system, not a
        # caller, supplies them) — exempt, same spirit as the FastAPI carve-out.
        if func.name.startswith("test_"):
            arg_count = -1
        else:
            arg_count = _count_ast_positional(func)
        if arg_count > FN_005_MAX_POSITIONAL:
            violations.append(
                f"{file_path}:{func.lineno} — FN-005: `{func.name}` takes "
                f"{arg_count} arguments (cap {FN_005_MAX_POSITIONAL}); group them "
                f"into a dataclass / TypedDict / parameter object"
            )
        body_stmts = _function_body_statement_count(func)
        if body_stmts > FN_001_MAX_STATEMENTS:
            violations.append(
                f"{file_path}:{func.lineno} — FN-001: `{func.name}` has "
                f"{body_stmts} body statements (cap is {FN_001_MAX_STATEMENTS}); "
                f"extract helpers"
            )

    # OD-004 — hybrid classes (excluding framework-boundary carve-out).
    for cls in _iter_classes(tree):
        if _class_extends_framework_base(cls):
            continue
        if _class_has_property_and_business_methods(cls):
            violations.append(
                f"{file_path}:{cls.lineno} — OD-004: `{cls.name}` is a hybrid "
                f"class (mixes `@property` data accessors with business methods); "
                f"split data carrier from behavior owner"
            )

    return iter(violations), True
