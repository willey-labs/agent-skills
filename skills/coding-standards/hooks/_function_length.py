#!/usr/bin/env python3
"""FN-001 function-length ADVISORY for the brace languages without an AST check.

TS/JS and Python get a precise statement-count FN-001 block from their AST layers
(_ts_node_checks / _py_ast). Go, C#, Java, Kotlin, and PHP have no stdlib parser
here, so a precise count isn't available — and a blunt line count can't clear the
~1% false-positive bar a hard block requires (AGENTS.md). So this is an *advisory*
(exit 0 + stderr via block-god-file's advisory path): it warns when a function body
runs long, the reviewer confirms whether it's really doing more than one thing.

Body length is measured by brace-matching from the function's opening `{` (over
text with strings/comments stripped, so braces inside them don't miscount). The
threshold is generous (higher-ceremony languages run longer) to keep the warning
rare and meaningful.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

# Generous on purpose — this is a blunt line count, not a statement count, so it
# warns only on clearly-long bodies. The precise ~20-statement FN-001 line is the
# AST hooks' job on TS/Python.
FN_LEN_ADVISORY_LINES = 50

# "Looks like a function header" per language. Go/Kotlin/PHP have an unambiguous
# keyword; C#/Java require an access modifier (keeps the false-positive rate near
# zero — control-flow `if (...)`/`for (...)` never start with one). Approximate by
# design: a missed package-private Java method is fine for an advisory.
_HEADER_BY_EXT: dict[str, re.Pattern[str]] = {
    ".go": re.compile(r"\bfunc\b.*\("),
    ".kt": re.compile(r"\bfun\b.*\("),
    ".kts": re.compile(r"\bfun\b.*\("),
    ".php": re.compile(r"\bfunction\b.*\("),
    ".cs": re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(?:public|private|protected|internal)\b[^;=]*\("),
    ".java": re.compile(r"^\s*(?:@\w+\s*)*(?:public|private|protected)\b[^;=]*\("),
}


def _strip(source: str) -> str:
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"#[^\n]*", blank, source)
    source = re.sub(r"`(?:\\.|[^`\\])*`", blank, source, flags=re.DOTALL)
    source = re.sub(r'"(?:\\.|[^"\\])*"', blank, source)
    source = re.sub(r"'(?:\\.|[^'\\])*'", blank, source)
    return source


def _body_line_count(clean: list[str], raw: list[str], header_idx: int) -> tuple[int, int]:
    """From a header line, find the body's opening `{` (within 3 lines — else it's
    a bodiless declaration) and brace-match to its close. Returns (body_nonblank,
    close_idx); body_nonblank is -1 when there's no body to measure."""
    n = len(clean)
    k = header_idx
    while k < min(header_idx + 3, n):
        if "{" in clean[k]:
            break
        if ";" in clean[k]:  # bodiless decl (interface / abstract) before any brace
            return -1, header_idx
        k += 1
    else:
        return -1, header_idx
    if "{" not in clean[k]:
        return -1, header_idx

    depth = 0
    body = 0
    j = k
    while j < n:
        depth += clean[j].count("{") - clean[j].count("}")
        if j > k and raw[j].strip():
            body += 1
        if depth <= 0:
            break
        j += 1
    if j < n and raw[j].strip():
        body -= 1  # exclude the closing-brace line
    return body, j


def iter_long_functions(content: str, ext: str, file_path: str) -> Iterable[str]:
    header = _HEADER_BY_EXT.get(ext.lower())
    if header is None:
        return
    clean = _strip(content).splitlines()
    raw = content.splitlines()
    i = 0
    while i < len(clean):
        if header.search(clean[i]):
            body, close_idx = _body_line_count(clean, raw, i)
            if body > FN_LEN_ADVISORY_LINES:
                yield (
                    f"{file_path}:{i + 1} — FN-001: function body is ~{body} lines "
                    f"(> {FN_LEN_ADVISORY_LINES}); if it does more than one thing, "
                    f"extract helpers (advisory — no AST length check for this language)"
                )
            if body >= 0:
                i = close_idx + 1
                continue
        i += 1
