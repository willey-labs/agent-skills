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
# FN-001 length advisory for the languages with no AST statement-count (Go, C#,
# Java, Kotlin, PHP). TS/JS/Python get a precise FN-001 block from their AST hooks.
from _function_length import iter_long_functions  # noqa: E402

# Source extensions this rule applies to — shared so it can't drift from the
# other hooks' sets (ISS-010). One canonical set in _languages.py.
from _languages import CONTENT_HOOK_EXTENSIONS, SOURCE_EXTENSIONS as SOURCE_EXTS  # noqa: E402

# Fixed thresholds from ST-008 — the standard, not tunable per project.
MAX_BEHAVIORAL_DECLS = 10   # > this many top-level functions/classes → BLOCK
MAX_LINES = 400             # > this many lines → advisory warning
MAX_FLAT_FILES = 12         # > this many flat source siblings → advisory warning

# Test / schema / fixture / story files — legitimately large, never flagged.
# Matched against the filename (lowercased), language-agnostic.
EXEMPT_NAME_PATTERNS = (
    re.compile(r"\.test\."), re.compile(r"\.spec\."),
    re.compile(r"_test\.(py|go)$"), re.compile(r"^test_.*\.py$"),
    re.compile(r"\.schema\."), re.compile(r"-schema(s)?\."),
    re.compile(r"\.fixtures?\."), re.compile(r"\.stor(?:y|ies)\."),
    re.compile(r"\.e2e\."),
)

# JVM / C# test classes are PascalCase (FooTest, FooTests, OrderServiceTests).
# Matched against the ORIGINAL-case name with a capital `T` preceded by start or a
# lower/digit boundary, so `Contest.java` / `Attest.cs` (lowercase "test") are NOT
# exempted (ISS-022) while real `FooTest.java` still is.
EXEMPT_CLASSFILE_PATTERN = re.compile(r"(?:^|[a-z0-9])Tests?\.(java|kt|cs)$")

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

# ISS-004 — modern TS/JS declares functions as `const f = () => …` or
# `const f = function () {…}`, the dominant style. Count those as behavioral so
# the god-file block can't be evaded by writing 14 arrow-consts. Precision: the
# arrow/function-expression must sit IMMEDIATELY after `=`, so a const holding a
# value, object, array, or a `.map(i => …)` result stays non-behavioral (data).
_BEHAVIORAL_ASSIGN = re.compile(
    r"^(export\s+)?(default\s+)?(const|let|var)\s+\w+"
    r"(\s*:\s*[^=]+?)?\s*=\s*(async\s+)?"
    r"(function\b|(\([^)]*\)|\w+)\s*(:\s*[^=]+?)?=>)"
)


def is_exempt_name(file_path: str) -> bool:
    name = Path(file_path).name
    if any(p.search(name.lower()) for p in EXEMPT_NAME_PATTERNS):
        return True
    return bool(EXEMPT_CLASSFILE_PATTERN.search(name))


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


def strip_noncode(source: str) -> str:
    """Blank multi-line strings and comments (preserving newlines) so a file that
    *embeds* code — fixture generators, docs with samples, templates, heredocs —
    isn't counted as having those embedded `def`/`function`/`class` lines as its
    own declarations. Covers the column-0 false-positive vector: triple-quoted
    strings (Python), backtick template literals (JS/TS), block comments, and
    line comments. Single-line string literals are left alone — a column-0 decl
    keyword almost never hides inside one."""
    def blank(match: re.Match[str]) -> str:
        return "".join(" " if ch != "\n" else "\n" for ch in match.group(0))

    source = re.sub(r'""".*?"""', blank, source, flags=re.DOTALL)
    source = re.sub(r"'''.*?'''", blank, source, flags=re.DOTALL)
    source = re.sub(r"`(?:\\.|[^`\\])*`", blank, source, flags=re.DOTALL)
    source = re.sub(r"/\*.*?\*/", blank, source, flags=re.DOTALL)
    source = re.sub(r"//[^\n]*", blank, source)
    source = re.sub(r"#[^\n]*", blank, source)
    return source


def count_behavioral_decls(content: str) -> int:
    clean = strip_noncode(content)
    return sum(
        1
        for line in clean.splitlines()
        if _BEHAVIORAL_DECL.match(line) or _BEHAVIORAL_ASSIGN.match(line)
    )


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


def _apply_edits(base: str, tool_input: dict[str, object]) -> tuple[str, bool]:
    """Apply Edit/MultiEdit diffs to `base`; return (post_content, applied_cleanly).
    applied_cleanly is False when an old_string isn't found — the caller then
    counts the pre-edit content and says so, instead of guessing."""
    multi = tool_input.get("edits")
    edits = multi if isinstance(multi, list) else [tool_input]
    text = base
    applied = True
    for edit in edits:
        if not isinstance(edit, dict):
            continue
        old = edit.get("old_string", "")
        new = edit.get("new_string", "")
        if not isinstance(old, str) or not isinstance(new, str) or old == "":
            applied = False
            continue
        if old not in text:
            applied = False
            continue
        text = text.replace(old, new) if edit.get("replace_all") else text.replace(old, new, 1)
    return text, applied


def resolve_content(payload: dict[str, object], file_path: str) -> tuple[str | None, bool]:
    """Return (content_to_count, post_edit_computed).

    Write: the full new content (post_edit_computed is trivially True).
    Edit/MultiEdit: the POST-edit content — apply the diff to the on-disk file so
    the count reflects the file AFTER the write, not before (ISS-005). Falls back
    to the on-disk pre-edit content (post_edit_computed=False) when the diff can't
    be applied (old_string missing / unreadable file)."""
    tool_input = payload.get("tool_input") or {}
    content = tool_input.get("content")
    if isinstance(content, str):  # Write
        return content, True
    try:  # Edit / MultiEdit — payload carries only the diff
        base = Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None, False
    return _apply_edits(base, tool_input)


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

    content, post_edit_computed = resolve_content(payload, file_path)
    if content is None:
        return 0
    if has_generation_marker(content):
        return 0

    ext = Path(file_path).suffix.lower()
    block_msg = assess_god_file_block(file_path, content)
    advisories = [
        m for m in (assess_size_warning(file_path, content), assess_flat_folder(file_path)) if m
    ]
    advisories.extend(iter_long_functions(content, Path(file_path).suffix, file_path))

    # The decl-count BLOCK is hard only for languages with a dedicated content hook.
    # Ruby / Rust / Swift have none (v5-unsupported), so a hard ST-008 block there is
    # half-enforcement — demote it to an advisory. The path-based ST-005 check
    # (block-junk-paths.py) still blocks for every language.
    if block_msg and ext not in CONTENT_HOOK_EXTENSIONS:
        advisories.insert(
            0,
            block_msg + "\n    (advisory — no content hook for this language yet; "
            "ST-008 is not hard-blocked here, but this file still does too many jobs)",
        )
        block_msg = None

    if block_msg:
        # The way out is a structural split, which is a full-file Write (or new
        # sibling files) — never another Edit, which would re-trip this block.
        escape = (
            "\n    Fix: split this into named sibling units with a full-file Write "
            "(or new files), one job each — not another Edit."
        )
        if not post_edit_computed:
            escape += (
                "\n    (Counted the on-disk file: the edit's old_string wasn't found, "
                "so the post-edit size couldn't be computed.)"
            )
        sys.stderr.write("coding-standards (BLOCKED — ST-008):\n  - " + block_msg + escape + "\n")
        return 2

    if advisories:
        sys.stderr.write(
            "coding-standards (advisory: not hard-blocked, but each is still a "
            "must-fix violation — fix it or record it accepted with a reason):\n"
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
