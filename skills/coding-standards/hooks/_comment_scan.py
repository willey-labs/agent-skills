#!/usr/bin/env python3
"""Comment and docstring extraction, shared by the comment hooks.

`advise-comment-slop.py` (regex tells) and `judge-comments.py` (model judgement)
both need the same answer to "which lines of this file are comment prose, and
where do they start" — so the extraction lives here once (DP-007).

String literals are blanked before comments are read, so a `#` inside a JS string
is never mistaken for a comment. Python docstrings count as comments; a
triple-quoted block only counts when it opens a statement, which keeps prompt
templates and SQL blobs out. `#` counts as a comment marker only where the
language says so — elsewhere it introduces a private field or a preprocessor
directive.

Stdlib only.
"""

from __future__ import annotations

import re

HASH_COMMENT_EXTS = {".py", ".pyi", ".rb", ".php"}
DOCSTRING_EXTS = {".py", ".pyi"}

_TRIPLE_QUOTED = re.compile(
    r'"""(?:\\.|[^"\\]|"(?!""))*"""' r"|'''(?:\\.|[^'\\]|'(?!''))*'''", re.DOTALL
)
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_QUOTED = re.compile(r"`(?:\\.|[^`\\])*`" r'|"(?:\\.|[^"\\])*"' r"|'(?:\\.|[^'\\])*'")
_SLASH_COMMENT = re.compile(r"//+(.*)$")
_HASH_COMMENT = re.compile(r"#+(.*)$")
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


def _spans(
    text: str, pattern: re.Pattern[str], statement_position: bool = False
) -> tuple[list[tuple[int, str]], str]:
    """Every line of every `pattern` match, numbered, plus `text` with those spans
    blanked out. With `statement_position`, only matches that open a statement are
    collected — a triple-quoted block is a docstring when nothing but indentation
    precedes it, and a prompt template or a SQL blob when an assignment, a call, or
    a string prefix does."""
    lines: list[tuple[int, str]] = []
    for match in pattern.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        if statement_position and text[line_start : match.start()].strip():
            continue
        first = text.count("\n", 0, match.start()) + 1
        lines.extend(
            (first + offset, line) for offset, line in enumerate(match.group(0).splitlines())
        )
    return lines, pattern.sub(_blank, text)


def commented_lines(source: str, ext: str) -> list[tuple[int, str]]:
    """(line number, comment prose) for every comment and docstring line in a file."""
    found: list[tuple[int, str]] = []
    if ext in DOCSTRING_EXTS:
        docstrings, remaining = _spans(source, _TRIPLE_QUOTED, statement_position=True)
        found.extend(docstrings)
    else:
        remaining = _TRIPLE_QUOTED.sub(_blank, source)
        blocks, remaining = _spans(remaining, _BLOCK_COMMENT)
        found.extend(blocks)

    remaining = _QUOTED.sub(_blank, remaining)
    markers = [_SLASH_COMMENT]
    if ext in HASH_COMMENT_EXTS:
        markers.append(_HASH_COMMENT)
    for lineno, line in enumerate(remaining.splitlines(), start=1):
        for marker in markers:
            match = marker.search(line)
            if match:
                found.append((lineno, match.group(1)))
                break

    return found
