#!/usr/bin/env python3
"""PreToolUse hook — ST-008 god-file soft warning.

Warns (stderr, exit 0 — NEVER blocks) when a Write/Edit targets a source file
that has grown past the project threshold (default 400 lines / 10 top-level
declarations), which usually means it holds more than one responsibility and
should be split into named sibling units. See references/common/structure.md#st-008.

This is a WARNING, not a block: a raw line/declaration count has a false-positive
rate well above the ~1% bar AGENTS.md sets for hard blocks (large test files,
schema/DTO files, lookup tables). So it nudges on the write path that fast/
single-agent mode would otherwise skip, without fighting legitimate large files.

Skips: excluded paths (node_modules, generated, ...), generated-marker files,
and test/schema/fixture/story files (any language). Reads the threshold +
on/off from .coding-standards-structure via _structure.py. Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402
from _structure import load_god_file_config  # noqa: E402

# Source extensions this rule applies to (mirrors block-junk-paths.py's set).
SOURCE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs",
    ".py", ".go", ".cs", ".java", ".kt", ".php", ".rb", ".rs", ".vue", ".swift",
}

# Test / schema / fixture / story files — legitimately large, never warned.
# Matched against the filename (lowercased), language-agnostic.
EXEMPT_NAME_PATTERNS = (
    re.compile(r"\.test\."), re.compile(r"\.spec\."),
    re.compile(r"_test\.(py|go)$"), re.compile(r"^test_.*\.py$"),
    re.compile(r"(test|tests)\.(java|kt|cs)$"),   # FooTest.java, FooTests.cs
    re.compile(r"\.schema\."), re.compile(r"-schema(s)?\."),
    re.compile(r"\.fixtures?\."), re.compile(r"\.stories\."),
    re.compile(r"\.e2e\."),
)

# A top-level declaration: a declaration keyword at column 0 (no indent). Broad
# on purpose — it's a warning heuristic, not a gate.
_DECL_LINE = re.compile(
    r"^(export\s+)?(default\s+)?(public\s+|private\s+|protected\s+|internal\s+|"
    r"abstract\s+|static\s+|final\s+|async\s+)*"
    r"(function|class|interface|type|enum|struct|const|let|var|def|func|trait|impl|protocol)\b"
)


def is_exempt_name(file_path: str) -> bool:
    name = Path(file_path).name.lower()
    return any(p.search(name) for p in EXEMPT_NAME_PATTERNS)


def count_top_level_decls(content: str) -> int:
    return sum(1 for line in content.splitlines() if _DECL_LINE.match(line))


def assess(file_path: str, content: str) -> str | None:
    """Return a warning message if the file is over threshold, else None."""
    cfg = load_god_file_config(file_path)
    if not cfg["enabled"]:
        return None
    line_count = content.count("\n") + 1 if content else 0
    decl_count = count_top_level_decls(content)
    over_lines = line_count > cfg["max_lines"]
    over_decls = decl_count > cfg["max_decls"]
    if not (over_lines or over_decls):
        return None
    reasons = []
    if over_lines:
        reasons.append(f"{line_count} lines (> {cfg['max_lines']})")
    if over_decls:
        reasons.append(f"{decl_count} top-level declarations (> {cfg['max_decls']})")
    return (
        f"{file_path} — ST-008: {', '.join(reasons)}. This file likely holds more "
        f"than one responsibility — consider splitting it into named sibling units "
        f"(see references/common/structure.md#st-008). "
        f"Tune or disable via .coding-standards-structure (god-file / god-file-max-lines)."
    )


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name", "") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    if not file_path or Path(file_path).suffix.lower() not in SOURCE_EXTS:
        return 0
    if is_exempt_name(file_path):
        return 0

    excluded, _ = is_excluded_path(file_path)
    if excluded:
        return 0

    # For Edit/MultiEdit the full new content isn't in the payload; fall back to
    # the post-edit file on disk if present, else the provided content/new_string.
    content = tool_input.get("content")
    if content is None:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return 0
    if has_generation_marker(content):
        return 0

    message = assess(file_path, content)
    if message:
        sys.stderr.write(
            "coding-standards (advisory — not blocked):\n  - " + message + "\n"
        )
    return 0  # ALWAYS 0 — advisory only.


if __name__ == "__main__":
    sys.exit(main())
