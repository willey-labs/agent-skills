#!/usr/bin/env python3
"""PreToolUse hook — CM-007 multi-line comment blocks (all source languages).

A write may add a one-line comment. A block of two or more prose lines is refused:
past one line a comment has stopped stating a constraint and started arguing for the
choice, and the argument belongs in the pull request, not the file.

Only blocks this write ADDS are judged. The file on disk is read first and its
existing comment prose collected, so re-writing a file, or editing near a long
comment that is already there, passes untouched — the check cannot retroactively
condemn prose the author never opened. Judging whole files instead would refuse
roughly a third of the comments in a mature codebase, most of them load-bearing.

Threshold: `CODING_STANDARDS_MAX_COMMENT_LINES` prose lines, default 1.

Trade-off accepted: a block opening the written text (first two lines) is exempt, so
a file-header docstring and a rewrite of one both pass. For an `Edit` the exemption
reads the fragment's own first lines rather than the file's, which lets a two-line
comment through when an edit happens to begin with one. Recall lost there is cheaper
than refusing every module docstring in the repo.

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
HEADER_LINES = 2
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
    violations: list[str] = []
    for start, prose in prose_blocks(new_content, ext):
        if start <= HEADER_LINES:
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
