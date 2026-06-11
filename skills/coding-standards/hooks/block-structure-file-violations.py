#!/usr/bin/env python3
"""PreToolUse hook — keep `.coding-standards-structure` to structure only.

The structure file records placement only: which folder layout a project uses — a
`follows: <standard>` line and/or a `layout:` tree describing the solved structure
(a project may carry both). It is NOT a place to tune or silence rules. Every
coding-standards rule is always
enforced; there is no per-project on/off. So this hook hard-blocks (exit 2) a
Write/Edit to a `.coding-standards-structure` file that introduces:

- a comment line (`# ...`) — the file is machine-read; comments are inert noise
  and were the vector for agents editorialising a one-line config into an essay,
- a `hooks:` block, or
- any legacy rule toggle key (`deep-import`, `god-file`, `god-file-max-lines`,
  `god-file-max-decls`, `flat-folder`, `flat-folder-max-files`).

Allowed: `follows:`, `layout:`, and the layout tree body. A clean rewrite always
passes, so the Step-4 self-heal (which normalises a legacy file down to `follows:`
/ `layout:`) is never blocked by this hook — only re-trashing is.

Checks the text the write INTRODUCES (Write `content`, Edit `new_string`,
MultiEdit new_strings), not the on-disk file — so a legacy file's existing cruft
doesn't block an unrelated edit; the self-heal handles pre-existing files.

Stdlib only. Exit 2 with stderr on block, 0 otherwise.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STRUCTURE_FILENAME = ".coding-standards-structure"

_COMMENT_LINE = re.compile(r"^\s*#")
_HOOKS_LINE = re.compile(r"^\s*hooks\s*:", re.IGNORECASE)
_TOGGLE_LINE = re.compile(
    r"^\s*(deep-import|god-file|god-file-max-lines|god-file-max-decls|"
    r"flat-folder|flat-folder-max-files)\s*:",
    re.IGNORECASE,
)


def introduced_text(tool_name: str, tool_input: dict[str, object]) -> str:
    """The text this write adds to the file: Write's full content, an Edit's
    new_string, or every new_string of a MultiEdit joined."""
    content = tool_input.get("content")
    if isinstance(content, str):
        return content
    new_string = tool_input.get("new_string")
    if isinstance(new_string, str):
        return new_string
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        parts = [e.get("new_string", "") for e in edits if isinstance(e, dict)]
        return "\n".join(p for p in parts if isinstance(p, str))
    return ""


def find_violations(text: str) -> list[str]:
    violations: list[str] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if _COMMENT_LINE.match(line):
            violations.append(f"line {idx}: comment — the file is machine-read; remove it")
        elif _HOOKS_LINE.match(line):
            violations.append(f"line {idx}: `hooks:` block — rules are not tunable; remove it")
        elif _TOGGLE_LINE.match(line):
            violations.append(f"line {idx}: rule toggle `{line.strip()}` — every rule is always enforced; remove it")
    return violations


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name", "")
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    if not file_path or Path(file_path).name != STRUCTURE_FILENAME:
        return 0

    violations = find_violations(introduced_text(tool_name, tool_input))
    if not violations:
        return 0

    sys.stderr.write(
        "coding-standards hook blocked this write — fix the file and try again.\n"
        f"`{STRUCTURE_FILENAME}` records structure only: a `follows: <standard>` line "
        "and/or a `layout:` tree (placement). No comments, no `hooks:`, no rule toggles — "
        "every rule is always enforced (see references/structure-resolution.md).\n"
        + "".join(f"  - {v}\n" for v in violations)
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Fail OPEN on an unexpected internal error: never block a legitimate write.
        sys.stderr.write(f"coding-standards: block-structure-file internal error, skipped ({exc})\n")
        sys.exit(0)
