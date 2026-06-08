#!/usr/bin/env python3
"""PreToolUse hook — ST-008 enforcement: god-file split + flat-folder promotion.

Two ST-008 signals, with deliberately different teeth:

1. **God-file BLOCK (exit 2)** — a Write/Edit targets a source file with more than
   the threshold of *behavioral* top-level declarations (functions, classes,
   methods — things that DO something). That is the least-blunt mechanical proxy
   for "this file does many jobs": a file with 11 top-level functions is doing 11
   things and must split. A 1.7k-line single-class state machine is ONE behavioral
   declaration and passes — length alone never blocks.
2. **God-file size WARNING (exit 0)** — the file is past the line threshold.
   Raw line count is too blunt to gate on (a cohesive large file is legitimate),
   so it nudges without blocking.
3. **Flat-folder WARNING (exit 0)** — a Write creates a NEW source file in a folder
   already holding more than the threshold of flat source files. At that count, 3+
   siblings sharing a theme have almost certainly earned a sub-feature folder (Rule
   of Three). Fires only on new-file creation, never on edits in place, and never
   when the new file is itself a front door (index/__init__/mod).

See references/common/structure.md#st-008 for both directions.

**Why behavioral declarations gate but lines/siblings only warn.** AGENTS.md sets a
~1% false-positive bar for hard blocks. Counting *behavioral* declarations clears
it where raw line count does not: data-only files (a 25-entry constants file, a
types/DTO file, a big enum) carry zero behavioral declarations, so they never
block; and you need 11+ column-0 `def`/`function`/`class`/`func`/`fn`/`impl` lines
to trip it, which strings/comments don't accumulate by accident. Residual, rare
false positive: a file that is genuinely a flat dispatch table of 11+ tiny related
functions — caught by the line/sibling warnings and the reviewer's judgement, never
silently. Length and sibling count stay advisory precisely because they are blunt.

**Two contexts, one rule.** At WRITE time this block is absolute — a new/edited file
over the threshold is rejected, no negotiation. At REVIEW/FIX time the *remedy* is the
reviewer's call: a cohesive split, OR a recorded exemption (.coding-standards-ignore +
a one-line reason, logged `accepted`) when the file is the one cohesive job the
column-0 proxy miscounts. That cohesion judgement is the backstop the residual false
positive relies on. See references/common/structure.md#st-008 "scatter": a split that
fragments cohesion or copies a sibling's machinery is itself a violation, not a fix.

Every rule here is fixed by the standard — there is NO per-project on/off or
threshold override. A project adopts a structure (placement), never a relaxed rule.

Skips: excluded paths (node_modules, generated, ...), generated-marker files, and
test/schema/fixture/story files (any language). Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402

# Source extensions this rule applies to (mirrors block-junk-paths.py's set).
SOURCE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs",
    ".py", ".go", ".cs", ".java", ".kt", ".php", ".rb", ".rs", ".vue", ".swift",
}

# Fixed thresholds from ST-008 — the standard, not tunable per project.
MAX_BEHAVIORAL_DECLS = 10   # > this many top-level functions/classes → BLOCK
MAX_LINES = 400             # > this many lines → advisory warning
MAX_FLAT_FILES = 12         # > this many flat source siblings → advisory warning

# Test / schema / fixture / story files — legitimately large, never flagged.
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

# A BEHAVIORAL top-level declaration: a callable/type-with-behavior keyword at
# column 0 (no indent). Data declarations (const/let/var/type/interface/enum/
# struct) are deliberately excluded — a file full of those is data, not many jobs.
# `pub\s+` covers Rust `pub fn` / `pub impl` at column 0.
_BEHAVIORAL_DECL = re.compile(
    r"^(export\s+)?(default\s+)?(pub\s+|public\s+|private\s+|protected\s+|internal\s+|"
    r"abstract\s+|static\s+|final\s+|async\s+)*"
    r"(function|func|fn|def|class|impl|trait|protocol)\b"
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


def count_behavioral_decls(content: str) -> int:
    return sum(1 for line in content.splitlines() if _BEHAVIORAL_DECL.match(line))


def assess_god_file_block(file_path: str, content: str) -> str | None:
    """Return a BLOCKING message when the file has too many behavioral top-level
    declarations (does many jobs), else None."""
    decl_count = count_behavioral_decls(content)
    if decl_count <= MAX_BEHAVIORAL_DECLS:
        return None
    return (
        f"{file_path} — ST-008: {decl_count} behavioral top-level declarations "
        f"(> {MAX_BEHAVIORAL_DECLS}). This file does many jobs — split it into named "
        f"sibling units, one job each (see references/common/structure.md#st-008)."
    )


def assess_size_warning(file_path: str, content: str) -> str | None:
    """Return an ADVISORY message when the file is past the line threshold, else None."""
    line_count = len(content.splitlines())
    if line_count <= MAX_LINES:
        return None
    return (
        f"{file_path} — ST-008: {line_count} lines (> {MAX_LINES}). If this file holds "
        f"more than one responsibility, split it into named siblings "
        f"(see references/common/structure.md#st-008)."
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
    folder = target.parent
    try:
        sibling_count = sum(1 for p in folder.iterdir() if is_countable_unit(p))
    except OSError:
        return None  # brand-new or unreadable folder — nothing flat yet
    unit_count = sibling_count + 1  # + the file being written
    if unit_count <= MAX_FLAT_FILES:
        return None
    return (
        f"{folder} — ST-008: this write makes {unit_count} flat source files in one "
        f"folder (> {MAX_FLAT_FILES}). If 3+ of them share a theme they have earned a "
        f"sub-feature folder (Rule of Three) — promote the themed cluster "
        f"(see references/common/structure.md#st-008)."
    )


def read_content(tool_input: dict[str, object], file_path: str) -> str | None:
    """The full new content for Write; the current on-disk file for Edit/MultiEdit
    (whose payload carries only the diff). None when nothing is readable."""
    content = tool_input.get("content")
    if isinstance(content, str):
        return content
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


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

    content = read_content(tool_input, file_path)
    if content is None:
        return 0
    if has_generation_marker(content):
        return 0

    block_msg = assess_god_file_block(file_path, content)
    advisories = [
        m for m in (assess_size_warning(file_path, content), assess_flat_folder(file_path)) if m
    ]

    if block_msg:
        sys.stderr.write("coding-standards (BLOCKED — ST-008):\n  - " + block_msg + "\n")
        return 2

    if advisories:
        sys.stderr.write(
            "coding-standards (advisory — not blocked):\n"
            + "".join(f"  - {m}\n" for m in advisories)
        )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail OPEN:
        # exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-god-file internal error, skipped ({exc})\n")
        sys.exit(0)
