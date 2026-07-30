#!/usr/bin/env python3
"""Which comments a turn is answerable for.

The comment judge must look at what this turn wrote and nothing else: dragging a
legacy file's existing comments into the verdict would hold a turn open over prose
its author never touched. This collects runs of consecutive comment lines from the
files a turn wrote, keeps only those the working tree changed, and attaches the code
each run sits above so narration is visible to the judge.

Where the changed lines can't be determined — no git, not a repo, change already
committed — a file is judged whole only while it carries few comments. Precision over
recall: a missed comment is cheaper than a turn held open over unrelated code.

Stdlib only.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from _comment_scan import commented_lines, is_directive, strip_marker
from _languages import SOURCE_EXTENSIONS

MAX_BLOCKS = 30
MAX_BLOCKS_WITHOUT_DIFF = 8
CONTEXT_LINES = 6

_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True)
class CommentBlock:
    """One run of consecutive comment lines, with the code it sits above."""

    block_id: int
    file_path: str
    line: int
    comment: str
    code: str


def changed_lines(file_path: str) -> set[int] | None:
    """The line numbers this working tree changed in `file_path`, or None when that
    can't be determined."""
    if not shutil.which("git"):
        return None
    path = Path(file_path)
    try:
        proc = subprocess.run(
            ["git", "diff", "-U0", "--no-color", "--", path.name],
            cwd=path.parent,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines: set[int] = set()
    for row in proc.stdout.splitlines():
        match = _HUNK.match(row)
        if match:
            start = int(match.group(1))
            span = int(match.group(2) or "1")
            lines.update(range(start, start + span))
    return lines or None


def group_blocks(numbered: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    """Consecutive comment lines, grouped into blocks."""
    blocks: list[list[tuple[int, str]]] = []
    for lineno, raw in sorted(numbered):
        if blocks and blocks[-1][-1][0] == lineno - 1:
            blocks[-1].append((lineno, raw))
        else:
            blocks.append([(lineno, raw)])
    return blocks


def _code_after(source_lines: list[str], last_comment_line: int) -> str:
    """Up to CONTEXT_LINES of code below a comment block, so narration is visible."""
    tail = [line for line in source_lines[last_comment_line:] if line.strip()]
    return "\n".join(tail[:CONTEXT_LINES])


def _prose_groups(source: str, ext: str) -> list[list[tuple[int, str]]]:
    """Comment blocks carrying prose — machine directives dropped."""
    return [
        group
        for group in group_blocks(commented_lines(source, ext))
        if any(strip_marker(raw) and not is_directive(raw) for _lineno, raw in group)
    ]


def blocks_for_file(file_path: str, next_id: int) -> list[CommentBlock]:
    """Every judgeable comment block in one file, numbered from `next_id`."""
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    groups = _prose_groups(source, Path(file_path).suffix)
    touched = changed_lines(file_path)
    if touched is None:
        if len(groups) > MAX_BLOCKS_WITHOUT_DIFF:
            return []
    else:
        groups = [group for group in groups if any(lineno in touched for lineno, _raw in group)]

    source_lines = source.splitlines()
    return [
        CommentBlock(
            block_id=next_id + offset,
            file_path=file_path,
            line=group[0][0],
            comment="\n".join(strip_marker(raw) for _lineno, raw in group if strip_marker(raw)),
            code=_code_after(source_lines, group[-1][0]),
        )
        for offset, group in enumerate(groups)
    ]


def collect_blocks(files: list[str]) -> list[CommentBlock]:
    """Judgeable comment blocks across every file a turn wrote, capped."""
    blocks: list[CommentBlock] = []
    for file_path in files:
        if Path(file_path).suffix not in SOURCE_EXTENSIONS:
            continue
        blocks.extend(blocks_for_file(file_path, len(blocks) + 1))
        if len(blocks) >= MAX_BLOCKS:
            return blocks[:MAX_BLOCKS]
    return blocks
