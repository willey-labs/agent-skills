#!/usr/bin/env python3
"""Shared PreToolUse plumbing for the block-*.py content hooks.

Every language hook runs the same lifecycle — read the tool-call JSON, decide
whether the target file is ours, and emit a block message — and only the
*checks* differ. That shared lifecycle lives here so it isn't copy-pasted across
six hooks (DP-001 DRY). Each hook keeps only its own constants, its check
functions, and a thin `main` that wires its extension set + checks into this
runner.

`strip_strings_and_comments` is deliberately NOT here: each language blanks
different literal/comment syntax (Python triple-quotes, JS template literals,
PHP heredocs), so those are genuinely distinct implementations, not duplication.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402

_RULE_CODE = re.compile(r"\b(?:FN|NM|OD|ST|EH|FMT|DP)-\d+\b")

# The fixed first line of every block message; the per-hook "See ..." line
# follows it (see `block`).
_BLOCK_LEAD = "coding-standards hook blocked this write — fix the violations and try again.\n"


def read_payload() -> dict | None:
    """Read and parse the PreToolUse JSON from stdin.

    Returns the payload dict, or None when stdin is empty or unparseable (the
    caller then exits 0 — there's nothing to check).
    """
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def extract_new_content(tool_name: str, tool_input: dict) -> str:
    """The proposed new file content carried by a Write/Edit/MultiEdit call."""
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


def resolve_target(payload: dict, extensions: set[str]) -> tuple[str, str] | None:
    """The shared gate. Returns (file_path, new_content) when the event is ours.

    "Ours" = a Write/Edit/MultiEdit of a non-excluded, non-generated file whose
    extension is in `extensions`, carrying non-empty content. Otherwise None
    (the caller passes through with exit 0).
    """
    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return None
    file_path = tool_input.get("file_path", "")
    if not file_path or Path(file_path).suffix not in extensions:
        return None
    excluded, _pattern = is_excluded_path(file_path)
    if excluded:
        return None
    new_content = extract_new_content(tool_name, tool_input)
    if not new_content.strip():
        return None
    if has_generation_marker(new_content):
        return None
    return file_path, new_content


def join_wrapped_signatures(lines: list[str]) -> list[tuple[int, str]]:
    """Yield (start_lineno, text) where a line with unbalanced parens is extended
    with following lines until the parens close. A signature split across lines —
    the natural shape for a long parameter list — is then matched as one unit, so
    the arg-count checks can't be evaded by wrapping. Over-merging is harmless: the
    arg-count regexes only fire on `func`/`def`/method patterns, so a merged
    non-signature run simply doesn't match. Line number is the first physical line.
    """
    joined: list[tuple[int, str]] = []
    i, n = 0, len(lines)
    while i < n:
        start = i
        buf = lines[i]
        depth = buf.count("(") - buf.count(")")
        while depth > 0 and i + 1 < n:
            i += 1
            buf += " " + lines[i]
            depth += lines[i].count("(") - lines[i].count(")")
        joined.append((start + 1, buf))
        i += 1
    return joined


def cited_rules(violations: list[str]) -> str:
    """The sorted set of rule codes that fired, for the citation line.

    e.g. "FN-005, NM-006". Violations with no code (the bare `any` ban) don't
    contribute; returns "the rule references" when nothing carries a code.
    """
    cited = sorted({m.group(0) for v in violations for m in _RULE_CODE.finditer(v)})
    return ", ".join(cited) if cited else "the rule references"


def block(violations: list[str], see_line: str) -> int:
    """Write the block message (lead + per-hook `see_line` + bulleted
    violations) to stderr and return the exit-2 block code."""
    header = _BLOCK_LEAD + see_line + "\n"
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2
