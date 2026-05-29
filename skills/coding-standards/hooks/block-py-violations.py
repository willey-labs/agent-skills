#!/usr/bin/env python3
"""PreToolUse hook — Python content checks.

Hard-blocks Write/Edit/MultiEdit on `.py` files when the new content
violates rules detectable via regex or AST. Stdlib only.

Regex checks (work on any content, including partial snippets):
- `typing.Any` usage: `: Any`, `-> Any`, `List[Any]`, `Dict[..., Any]`, ...
- Hungarian-style snake_case names: `str_name`, `arr_items`, `obj_user`, ...
- Star imports: `from x import *`

AST checks (only fire if `ast.parse` succeeds — i.e., the content is a
syntactically valid Python module; Edit snippets that are partial syntax
fall back to regex-only):
- FN-001: function body length (>20 statements is flagged; configurable)
- FN-005: precise argument count (>3, excluding self/cls and the *args/**kwargs
  buckets; keyword-only args after `*` ARE counted — they raise mental load too,
  so a `*`-only signature does NOT escape the rule. Use a dataclass/TypedDict.)
- OD-004: hybrid classes (both `@property` getters/setters AND non-trivial
  business methods on the same class). Framework-boundary classes
  (subclasses of Base/Model/Schema/Serializer/Form/View etc.) are exempt
  per OD-005.

AST is preferred over regex where both apply (it's precise). Regex stays
as the fallback so Edit snippets and malformed files still get checked.

Reads PreToolUse JSON from stdin, exits 2 with stderr on block.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402

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
                yield f"{file_path}:{idx} — `Any` is banned ({label})"
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
    for idx, line in enumerate(clean_lines, start=1):
        match = FUNCTION_DEF.search(line)
        if not match:
            continue
        count = _count_py_params(match.group(1))
        if count >= 4:
            yield (
                f"{file_path}:{idx} — FN-005: function takes {count} parameters; "
                f"group them into a dataclass / TypedDict / parameter object"
            )


def iter_star_import_violations(raw_lines: list[str], file_path: str) -> Iterable[str]:
    for idx, line in enumerate(raw_lines, start=1):
        if STAR_IMPORT.search(line):
            yield (
                f"{file_path}:{idx} — star import (`from x import *`) banned; "
                f"name what you import"
            )


# ─────────────────────────────────────────────────────────────────────────────
# AST checks — only run when the new content is a syntactically valid module.
# Partial snippets from Edit/MultiEdit usually won't parse; we skip AST then
# and rely on the regex checks above.
# ─────────────────────────────────────────────────────────────────────────────

# FN-001 — function bodies should be small. Statement count (not line count)
# because Python's blocks compress vertically.
FN_001_MAX_STATEMENTS = 20

# FN-005 — positional arg threshold.
FN_005_MAX_POSITIONAL = 3

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


def _count_ast_positional(args: ast.arguments) -> int:
    """Count positional-capable parameters per FN-005's intent.

    Includes posonly_args + args. Excludes self/cls. Excludes vararg (*args)
    and kwarg (**kwargs) buckets — they're a single bucket each, not n args.
    Keyword-only args (after `*`) are counted because they still raise the
    mental load FN-005 is about.
    """
    positional = list(args.posonlyargs) + list(args.args)
    kwonly = list(args.kwonlyargs)
    # Drop self / cls from instance / classmethod definitions.
    positional = [a for a in positional if a.arg not in ("self", "cls")]
    return len(positional) + len(kwonly)


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
        positional_count = _count_ast_positional(func.args)
        if positional_count > FN_005_MAX_POSITIONAL:
            violations.append(
                f"{file_path}:{func.lineno} — FN-005: `{func.name}` takes "
                f"{positional_count} positional arguments; group them into a "
                f"dataclass / TypedDict / parameter object"
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

    if Path(file_path).suffix not in PY_EXTENSIONS:
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
    violations.extend(iter_hungarian_violations(clean_lines, file_path))
    violations.extend(iter_star_import_violations(raw_lines, file_path))

    # AST checks supersede the regex arg-count check when the file parses.
    # When parse fails (typically partial Edit snippets), fall back to regex.
    ast_iter, ast_ok = iter_ast_violations(new_content, file_path)
    violations.extend(ast_iter)
    if not ast_ok:
        violations.extend(iter_arg_count_violations(clean_lines, file_path))

    if not violations:
        return 0

    # Cite only the rules that actually fired (the `Any` ban carries no code).
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
    sys.exit(main())
