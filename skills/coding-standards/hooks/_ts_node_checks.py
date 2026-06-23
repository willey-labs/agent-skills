#!/usr/bin/env python3
"""Node-level TS/JS rule checks + framework carve-outs.

The "what counts as a violation" half of the tree-sitter layer: FN-001 (body
statement count), FN-005 (positional arg count, with the Express-error-middleware
and DI-parameter-property carve-outs), and OD-004 hybrid-class detection (with the
OD-005 framework-boundary carve-out). The parse/walk orchestration that drives
these lives in the sibling `_ts_ast.py` (ST-008: one job per file — this file is
"node predicates", that one is "parse + walk").

Pure node logic: no tree-sitter import here, so it stays importable even when the
grammars are absent.
"""

from __future__ import annotations

import re

FN_001_MAX_STATEMENTS = 20
# TS/JS have no named arguments, so FN-005's line sits at 4 (functions.md:80):
# MAX is the last allowed count, so 3 → a 4th positional arg blocks.
FN_005_MAX_POSITIONAL = 3

# FN-005 carve-out — Express error middleware. Express dispatches error
# middleware BY ARITY: a handler is treated as an error handler only when it
# declares exactly four parameters, so (err, req, res, next) is the framework's
# contract, not an API choice. Matched by param shape; a fifth param breaks the
# match so a genuine 5-arg violation still blocks. Shared by the AST path and the
# regex fallback in block-ts-violations.py so both agree.
EXPRESS_ERROR_MIDDLEWARE_PARAMS = re.compile(
    r"\(\s*"
    r"_*(?:e|err|error)\b[^,()]*,\s*"
    r"_*(?:req|request)\b[^,()]*,\s*"
    r"_*(?:res|response)\b[^,()]*,\s*"
    r"_*next\b[^,()]*"
    r"\)"
)

# FN-005 carve-out — TypeScript parameter properties. A constructor whose params
# all carry an accessibility/readonly modifier (`constructor(private a: A,
# readonly b: B)`) is the dependency-injection shape (NestJS, Angular): the
# container calls it, there is no human call site, and the params ARE the class's
# fields. A constructor with plain (un-modified) params is NOT injection and still
# blocks.
_TS_PARAM_MODIFIER = re.compile(r"^\s*(?:public|private|protected|readonly|override)\b")

# Function-like node types we check.
TS_FUNCTION_NODE_TYPES = {
    "function_declaration",
    "function_expression",
    "function",
    "arrow_function",
    "method_definition",
    "method_signature",
    "generator_function_declaration",
}

# Parent classes / class decorators that mark a class as framework-boundary
# (OD-005 carve-out). If a class extends/decorates any of these, OD-004 is N/A.
OD_005_BOUNDARY_PARENTS = {
    "Entity", "Model", "BaseModel", "BaseEntity", "Repository", "Schema",
    "Document", "Component", "Controller", "Service", "Module", "Resource",
    "Resolver", "Pipe", "Guard", "Interceptor", "Filter", "Middleware",
    "TypeOrmEntity", "MongooseModel", "PrismaModel",
}


def is_express_error_middleware_params(params_text: str) -> bool:
    """True when a parameter list has the Express 4-arg error-middleware shape."""
    return EXPRESS_ERROR_MIDDLEWARE_PARAMS.search(params_text) is not None


def function_name(node) -> str:
    """Best-effort function/method/class name for diagnostics. `type_identifier`
    covers class names (so OD-004 names the class, not `<anonymous>`)."""
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "type_identifier"):
            return child.text.decode("utf-8", errors="replace")
    return "<anonymous>"


def is_ts_di_constructor(func_node, params_node) -> bool:
    """True for a constructor whose params are all parameter-properties (DI)."""
    if func_node.type != "method_definition" or function_name(func_node) != "constructor":
        return False
    params = [c for c in params_node.children if c.type not in {"(", ")", ",", ":"}]
    if not params:
        return False
    return all(
        _TS_PARAM_MODIFIER.match(p.text.decode("utf-8", errors="replace"))
        for p in params
    )


def _count_ts_params(formal_parameters_node) -> int:
    """Count positional parameters; rest/destructured each count as 1 bucket."""
    excluded_types = {"(", ")", ",", ":"}
    return sum(
        1 for child in formal_parameters_node.children
        if child.type not in excluded_types
    )


def statement_block_stmt_count(body_node) -> int:
    """Count statements in a statement_block, excluding braces/comments and a
    leading docstring-style string literal."""
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


def class_extends_boundary_parent(class_node) -> bool:
    """OD-005 carve-out — class extends a known framework-boundary parent or
    carries a framework-boundary class decorator."""
    decorators = []
    candidate_nodes = list(class_node.children)
    if class_node.parent:
        candidate_nodes += list(class_node.parent.children)
    for node in candidate_nodes:
        if node.type == "decorator":
            decorators.append(node.text.decode("utf-8", errors="replace"))
    if any(d.lstrip("@").split("(")[0] in OD_005_BOUNDARY_PARENTS for d in decorators):
        return True

    for child in class_node.children:
        if child.type == "class_heritage":
            for c in child.children:
                if c.type == "extends_clause":
                    for e in c.children:
                        if e.type == "identifier" and e.text.decode(
                            "utf-8", errors="replace"
                        ) in OD_005_BOUNDARY_PARENTS:
                            return True
        if child.type == "extends_clause":
            for c in child.children:
                if c.type == "identifier" and c.text.decode(
                    "utf-8", errors="replace"
                ) in OD_005_BOUNDARY_PARENTS:
                    return True
    return False


# OD-004 fires only when data is exposed through ≥2 get/set accessors alongside
# business methods. One accessor next to one real method is ordinary OOP, not the
# data-exposing hybrid OD-004 targets (counting one over-fired on plain classes).
# Precision over recall: a borderline single-accessor case is left to review (Worker 1).
OD_004_MIN_ACCESSORS = 2


def class_has_accessor_and_business_methods(class_node) -> bool:
    """OD-004 — class exposes data through ≥2 get/set accessors AND owns non-trivial
    business methods (not constructors, not <=1-statement pass-throughs)."""
    accessor_count = 0
    business_methods = 0
    for child in class_node.children:
        if child.type != "class_body":
            continue
        for member in child.children:
            if member.type != "method_definition":
                continue
            if any(c.type in ("get", "set") for c in member.children):
                accessor_count += 1
                continue
            if function_name(member) == "constructor":
                continue
            body = next((c for c in member.children if c.type == "statement_block"), None)
            if body is None or statement_block_stmt_count(body) <= 1:
                continue
            business_methods += 1
    return accessor_count >= OD_004_MIN_ACCESSORS and business_methods >= 1


def check_function_node(func_node, file_path: str) -> list[str]:
    """FN-005 (arg count) + FN-001 (body length) for one function-like node."""
    line = func_node.start_point[0] + 1
    name = function_name(func_node)
    violations: list[str] = []

    params_node = next(
        (c for c in func_node.children if c.type == "formal_parameters"), None
    )
    if params_node is not None:
        count = _count_ts_params(params_node)
        params_text = params_node.text.decode("utf-8", errors="replace")
        exempt = is_express_error_middleware_params(params_text) or is_ts_di_constructor(
            func_node, params_node
        )
        if count > FN_005_MAX_POSITIONAL and not exempt:
            violations.append(
                f"{file_path}:{line} — FN-005: `{name}` takes {count} "
                f"positional parameters (cap {FN_005_MAX_POSITIONAL}); group into a typed object"
            )

    body = next((c for c in func_node.children if c.type == "statement_block"), None)
    if body is not None:
        stmts = statement_block_stmt_count(body)
        if stmts > FN_001_MAX_STATEMENTS:
            violations.append(
                f"{file_path}:{line} — FN-001: `{name}` has {stmts} body "
                f"statements (cap {FN_001_MAX_STATEMENTS}); extract helpers"
            )
    return violations
