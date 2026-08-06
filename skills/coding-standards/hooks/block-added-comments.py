#!/usr/bin/env python3
"""PreToolUse hook — CM-007, the one-line limit on comment blocks (all languages).

Judges only the prose a write ADDS: the file on disk is read first and its existing
comment lines subtracted, so re-writing a file or editing beside an old block passes.

A file-header block is exempt, and only a real one — the exemption asks what precedes
the block, not what line it sits on. Blank lines and machine directives may come
first; one line of code disqualifies it. For an `Edit` that test reads the fragment
rather than the file, so a fragment opening with a block is exempt.

Limit: `CODING_STANDARDS_MAX_COMMENT_LINES` prose lines, default 1.

Stdlib only. Exit 2 on block, 0 on pass.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _comment_blocks import group_blocks  # noqa: E402
from _comment_scan import commented_lines, is_directive, strip_marker  # noqa: E402
from _hook_run import block, read_payload, resolve_target  # noqa: E402
from _languages import SOURCE_EXTENSIONS  # noqa: E402

DEFAULT_MAX_LINES = 1
MAX_REPORTED = 10

SEE_LINE = "See references/common/comments.md#cm-007 — the default for a comment is none."


def max_lines() -> int:
    """The longest comment block a write may add, from the environment or the default."""
    raw = os.environ.get("CODING_STANDARDS_MAX_COMMENT_LINES", "")
    try:
        return max(1, int(raw))
    except ValueError:
        return DEFAULT_MAX_LINES


def prose_blocks(source: str, ext: str) -> list[tuple[int, list[str]]]:
    """(start line, prose lines) for every comment block carrying prose."""
    found: list[tuple[int, list[str]]] = []
    for group in group_blocks(commented_lines(source, ext)):
        prose = [
            strip_marker(raw) for _lineno, raw in group if strip_marker(raw) and not is_directive(raw)
        ]
        if prose:
            found.append((group[0][0], prose))
    return found


def directive_lines(source: str, ext: str) -> set[int]:
    return {lineno for lineno, prose in commented_lines(source, ext) if is_directive(prose)}


def opens_the_file(source: str, directives: set[int], start: int) -> bool:
    return all(
        not line.strip() or lineno in directives
        for lineno, line in enumerate(source.splitlines()[: start - 1], start=1)
    )


def existing_prose(file_path: str, ext: str) -> set[str]:
    """Every comment line already in the file on disk — the write is not answerable
    for these."""
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    return {line for _start, prose in prose_blocks(source, ext) for line in prose}


def added_violations(new_content: str, file_path: str, ext: str, limit: int) -> list[str]:
    """One message per comment block this write adds that runs past `limit` lines."""
    already = existing_prose(file_path, ext)
    directives = directive_lines(new_content, ext)
    violations: list[str] = []
    for start, prose in prose_blocks(new_content, ext):
        if opens_the_file(new_content, directives, start):
            continue
        added = [line for line in prose if line not in already]
        if len(added) <= limit:
            continue
        violations.append(
            f"{file_path}:{start} — CM-007: comment block adds {len(added)} lines of prose "
            f"(limit {limit}). State the constraint in one line, or delete it — "
            f'starts "{added[0][:60]}"'
        )
    return violations


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, set(SOURCE_EXTENSIONS))
    if target is None:
        return 0
    file_path, new_content = target
    violations = added_violations(
        new_content, file_path, Path(file_path).suffix, max_lines()
    )
    if not violations:
        return 0
    return block(violations[:MAX_REPORTED], SEE_LINE)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: block-added-comments internal error, skipped ({exc})\n")
        sys.exit(0)
