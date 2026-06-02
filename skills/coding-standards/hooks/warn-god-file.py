#!/usr/bin/env python3
"""PreToolUse hook — ST-008 soft warnings: god-file size + flat-folder promotion.

Warns (stderr, exit 0 — NEVER blocks) on two ST-008 signals:

1. **God-file** — a Write/Edit targets a source file past the project threshold
   (default 400 lines / 10 top-level declarations), which usually means it holds
   more than one responsibility and should be split into named sibling units.
2. **Flat folder** — a Write creates a NEW source file in a folder already
   holding more than the threshold of flat source files (default 12). At that
   count, 3+ siblings sharing a theme have almost certainly earned a sub-feature
   folder (Rule of Three) — the promotion direction of ST-008. Fires only on
   new-file creation (the "piling on" moment), never on edits in place, and
   never when the new file is itself a front door (index/__init__/mod).

See references/common/structure.md#st-008 for both directions.

These are WARNINGS, not blocks: raw line/declaration/sibling counts have a
false-positive rate well above the ~1% bar AGENTS.md sets for hard blocks
(large test files, schema/DTO files, lookup tables; idiomatic flat Go/Python
packages). So they nudge on the write path that fast/single-agent mode would
otherwise skip, without fighting legitimate large files or flat-by-design
layouts.

Skips: excluded paths (node_modules, generated, ...), generated-marker files,
and test/schema/fixture/story files (any language). Reads thresholds + on/off
from .coding-standards-structure via _structure.py (god-file / flat-folder
keys). Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402
from _structure import load_flat_folder_config, load_god_file_config  # noqa: E402

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
    re.compile(r"\.fixtures?\."), re.compile(r"\.stor(?:y|ies)\."),
    re.compile(r"\.e2e\."),
)

# Front-door / entry files (by stem) — a folder's barrel doesn't count toward
# flatness, and writing one is usually part of FIXING a flat folder.
ENTRY_FILE_STEMS = {"index", "__init__", "mod"}

# A top-level declaration: a declaration keyword at column 0 (no indent). Broad
# on purpose — it's a warning heuristic, not a gate.
# `pub\s+` covers Rust `pub fn` / `pub struct` / etc. at column 0.
_DECL_LINE = re.compile(
    r"^(export\s+)?(default\s+)?(pub\s+|public\s+|private\s+|protected\s+|internal\s+|"
    r"abstract\s+|static\s+|final\s+|async\s+)*"
    r"(fn|function|class|interface|type|enum|struct|const|let|var|def|func|trait|impl|protocol)\b"
)


def is_exempt_name(file_path: str) -> bool:
    name = Path(file_path).name.lower()
    return any(p.search(name) for p in EXEMPT_NAME_PATTERNS)


def is_countable_unit(path: Path) -> bool:
    """A flat source file that counts toward folder flatness: a real source
    unit, not a front door, not a test/schema/fixture sibling (ST-007 puts
    those beside their units — they don't add units)."""
    return (
        path.is_file()
        and path.suffix.lower() in SOURCE_EXTS
        and path.stem.lower() not in ENTRY_FILE_STEMS
        and not is_exempt_name(path.name)
    )


def count_top_level_decls(content: str) -> int:
    return sum(1 for line in content.splitlines() if _DECL_LINE.match(line))


def assess_file_size(file_path: str, content: str) -> str | None:
    """Return a warning message if the file is over the size threshold, else None."""
    cfg = load_god_file_config(file_path)
    if not cfg["enabled"]:
        return None
    line_count = len(content.splitlines())
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


def assess_flat_folder(file_path: str) -> str | None:
    """Warn when a NEW source file lands in a folder already past the flat-sibling
    threshold — the 'piling on' moment ST-008's Rule of Three is about. Edits in
    place never change the folder's unit count, so they never warn here."""
    target = Path(file_path)
    if target.exists():
        return None  # not a new file — folder flatness unchanged
    if target.stem.lower() in ENTRY_FILE_STEMS:
        return None  # writing a barrel is usually part of fixing flatness
    cfg = load_flat_folder_config(file_path)
    if not cfg["enabled"]:
        return None
    folder = target.parent
    try:
        sibling_count = sum(1 for p in folder.iterdir() if is_countable_unit(p))
    except OSError:
        return None  # brand-new or unreadable folder — nothing flat yet
    unit_count = sibling_count + 1  # + the file being written
    if unit_count <= cfg["max_files"]:
        return None
    return (
        f"{folder} — ST-008: this write makes {unit_count} flat source files in one "
        f"folder (> {cfg['max_files']}). If 3+ of them share a theme they have earned "
        f"a sub-feature folder (Rule of Three) — consider promoting the themed cluster "
        f"(see references/common/structure.md#st-008). "
        f"Tune or disable via .coding-standards-structure (flat-folder / flat-folder-max-files)."
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
    # the pre-edit (current on-disk) file if present, else the provided content/new_string.
    content = tool_input.get("content")
    if content is None:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return 0
    if has_generation_marker(content):
        return 0

    warnings = [
        m for m in (assess_file_size(file_path, content), assess_flat_folder(file_path)) if m
    ]
    if warnings:
        sys.stderr.write(
            "coding-standards (advisory — not blocked):\n"
            + "".join(f"  - {m}\n" for m in warnings)
        )
    return 0  # ALWAYS 0 — advisory only.


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail OPEN:
        # exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: warn-god-file internal error, skipped ({exc})\n")
        sys.exit(0)
