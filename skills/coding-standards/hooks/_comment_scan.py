#!/usr/bin/env python3
"""Comment and docstring extraction, shared by the comment hooks.

`advise-comment-slop.py` (regex tells) and `judge-comments.py` (model judgement)
both need the same answer to "which lines of this file are comment prose, and
where do they start" — so the extraction lives here once (DP-007).

Strings, comments and docstrings are read in one left-to-right pass, so whichever
opens first owns the text: a `#` or `/*` inside a string is never a comment, and a
quote inside a comment never opens a string. Python docstrings count as comments; a
triple-quoted block only counts when it opens a statement, which keeps prompt
templates, SQL blobs and string arguments out. `#` and `//` count as comment
markers only where the language says so — elsewhere `#` introduces a private field,
a preprocessor directive or a PHP attribute, and `//` is Python's floor division.

Stdlib only.
"""

from __future__ import annotations

import re
from functools import lru_cache

HASH_COMMENT_EXTS = {".py", ".pyi", ".rb", ".php"}
HASH_ONLY_EXTS = {".py", ".pyi", ".rb"}
DOCSTRING_EXTS = {".py", ".pyi"}
_OPEN_EXPRESSION_ENDINGS = ("(", "[", "{", ",", "=", "+", "\\")

_TRIPLE_QUOTED_SOURCE = r'"""(?:\\.|[^"\\]|"(?!""))*"""' r"|'''(?:\\.|[^'\\]|'(?!''))*'''"
_TRIPLE_QUOTED = re.compile(_TRIPLE_QUOTED_SOURCE, re.DOTALL)
_QUOTED = re.compile(r"`(?:\\.|[^`\\])*`" r'|"(?:\\.|[^"\\])*"' r"|'(?:\\.|[^'\\])*'")
_ONE_LINE_QUOTED_SOURCE = r"`(?:\\.|[^`\\])*`" r'|"(?:\\.|[^"\\\n])*"' r"|'(?:\\.|[^'\\\n])*'"
_BLOCK_COMMENT_SOURCE = r"/\*.*?\*/"
_SLASH_COMMENT_SOURCE = r"//[^\n]*"
_HASH_COMMENT_SOURCE = r"#[^\n]*"
_PHP_HASH_COMMENT_SOURCE = r"#(?!\[)[^\n]*"
_LEADING_MARKERS = re.compile(r"^(?://+|#+)")
_MARKER_NOISE = re.compile(r"^[\s*/]+|[\s*/]+$")

# Machine directives and encoding/shebang lines are not prose — never judged.
_DIRECTIVE = re.compile(
    r"^\s*(?:!|-\*-|%%|@?(?:eslint|ts-|prettier|biome|noqa|type:|pylint|mypy|ruff|pragma|"
    r"region|endregion|nolint|coverage|fmt:|SPDX|Copyright|codegen|istanbul|jscpd))",
    re.IGNORECASE,
)


def is_directive(raw: str) -> bool:
    """True for a machine directive — a linter pragma, shebang, encoding or SPDX line.

    Matched against the prose as well as the raw line: a pragma written in block-comment
    syntax carries its marker on the same line, and the anchored pattern would miss it.
    """
    return bool(_DIRECTIVE.search(raw) or _DIRECTIVE.search(strip_marker(raw)))


def strip_marker(raw: str) -> str:
    """The comment's prose, with comment punctuation and surrounding space removed."""
    return _MARKER_NOISE.sub("", raw)


def _blank(match: re.Match[str]) -> str:
    """The matched span replaced by spaces, its newlines kept so length and every
    later line number still line up with the real file."""
    return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))


def blank_strings(source: str) -> str:
    """`source` with string literals and docstrings blanked; comments and line numbers kept."""
    return _QUOTED.sub(_blank, _TRIPLE_QUOTED.sub(_blank, source))


@lru_cache(maxsize=None)
def _token_pattern(ext: str) -> re.Pattern[str]:
    comments = [] if ext in HASH_ONLY_EXTS else [_BLOCK_COMMENT_SOURCE, _SLASH_COMMENT_SOURCE]
    if ext == ".php":
        comments.append(_PHP_HASH_COMMENT_SOURCE)
    elif ext in HASH_COMMENT_EXTS:
        comments.append(_HASH_COMMENT_SOURCE)
    return re.compile(
        f"(?P<triple>{_TRIPLE_QUOTED_SOURCE})"
        f"|(?P<comment>{'|'.join(comments)})"
        f"|(?P<string>{_ONE_LINE_QUOTED_SOURCE})",
        re.DOTALL,
    )


def _continues_expression(source: str, line_start: int) -> bool:
    return source[:line_start].rstrip().endswith(_OPEN_EXPRESSION_ENDINGS)


def _scan(source: str, ext: str) -> list[tuple[int, str, bool]]:
    """(line number, comment text, follows code on its line) for every comment and docstring line."""
    found: list[tuple[int, str, bool]] = []
    for match in _token_pattern(ext).finditer(source):
        kind = match.lastgroup
        if kind == "string":
            continue
        line_start = source.rfind("\n", 0, match.start()) + 1
        follows_code = bool(source[line_start : match.start()].strip())
        if kind == "triple" and (
            ext not in DOCSTRING_EXTS or follows_code or _continues_expression(source, line_start)
        ):
            continue
        first = source.count("\n", 0, match.start()) + 1
        text = match.group(0)
        if kind == "comment" and not text.startswith("/*"):
            found.append((first, _LEADING_MARKERS.sub("", text), follows_code))
            continue
        lines = text.splitlines()
        trailing = follows_code and len(lines) == 1
        found.extend((first + offset, line, trailing) for offset, line in enumerate(lines))
    return found


def commented_lines(source: str, ext: str) -> list[tuple[int, str]]:
    """(line number, comment prose) for every comment and docstring line in a file."""
    return [(lineno, text) for lineno, text, _trailing in _scan(source, ext)]


def own_line_comments(source: str, ext: str) -> list[tuple[int, str]]:
    """`commented_lines` without the comments that follow code on their line."""
    return [(lineno, text) for lineno, text, trailing in _scan(source, ext) if not trailing]
