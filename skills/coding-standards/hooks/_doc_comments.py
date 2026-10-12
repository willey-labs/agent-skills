#!/usr/bin/env python3
"""Recognizes a doc comment: the language's documentation syntax, directly above a declaration.

A doc comment documents a contract a caller relies on — parameters, return value,
errors — and documentation tools render it, so it may run past one line. The
syntax alone is not enough: the same opener above a statement is a paragraph of
prose, and stays under the one-line limit.

  /** ... */  TS/JS, Java, Kotlin, PHP, C#, Swift
  ///         C#, Rust, Swift
  //          Go, above a top-level declaration or an exported member
  #           Ruby, above def/class/module/attr
  \"\"\" ... \"\"\"  Python, first statement of a def or class body

Stdlib only.
"""

from __future__ import annotations

import re

_SLASH_DECLARATION = re.compile(
    r"^\s*(?:"
    r"[@\[]|#\["
    r"|(?:export|default|public|private|protected|internal|static|abstract|final|async|override"
    r"|readonly|declare|open|sealed|data|inline|suspend|virtual|partial|unsafe|pub|extern"
    r"|function|class|interface|trait|enum|struct|record|type|const|let|var|val|fun|fn|func"
    r"|module|namespace|impl|mod|object|protocol|extension|init|get|set|constructor|typealias)\b"
    r"|(?!(?:return|throw|await|yield|new|else|case|delete|typeof|if|for|while|switch)\b)"
    r"[\w$<>\[\]?,.]+\s+[\w$]+\s*[(<]"
    r"|(?!(?:if|for|while|switch|catch|return)\b)[A-Za-z_$][\w$]*\s*(?:<[^>]*>)?\s*\([^;]*$"
    r")"
)
_GO_DECLARATION = re.compile(r"^(?:func|type|var|const|package)\b|^\s+[A-Z]\w*\b")
_RUBY_DECLARATION = re.compile(r"^\s*(?:def|class|module|attr_\w+)\b")
_PYTHON_BODY_OPENER = re.compile(r":\s*(?:#.*)?$")

SLASH_DOC_EXTS = {
    ".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".java", ".kt", ".kts", ".php", ".cs", ".rs", ".swift",
}


def _line(source_lines: list[str], lineno: int) -> str:
    return source_lines[lineno - 1] if 0 < lineno <= len(source_lines) else ""


def _previous_code_line(source_lines: list[str], lineno: int) -> str:
    for candidate in range(lineno - 1, 0, -1):
        text = _line(source_lines, candidate)
        if text.strip():
            return text
    return ""


def _documents_python_body(source_lines: list[str], first: int) -> bool:
    opener = _line(source_lines, first).lstrip()
    if not opener.startswith(('"""', "'''")):
        return False
    return bool(_PYTHON_BODY_OPENER.search(_previous_code_line(source_lines, first)))


def is_doc_comment(source_lines: list[str], group: list[tuple[int, str]], ext: str) -> bool:
    """True when a comment block is a doc comment on the declaration directly below it."""
    first, last = group[0][0], group[-1][0]
    opener = _line(source_lines, first).lstrip()
    below = _line(source_lines, last + 1)
    if ext in {".py", ".pyi"}:
        return _documents_python_body(source_lines, first)
    if ext == ".go":
        return opener.startswith("//") and bool(_GO_DECLARATION.match(below))
    if ext == ".rb":
        return opener.startswith("#") and bool(_RUBY_DECLARATION.match(below))
    if ext in SLASH_DOC_EXTS and opener.startswith(("/**", "///")):
        return bool(_SLASH_DECLARATION.match(below))
    return False
