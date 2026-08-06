#!/usr/bin/env python3
"""PreToolUse hook — CM-004/CM-005/CM-006 comment slop (all source languages).

ADVISORY ONLY: exit 0, findings handed to Claude as tool-result context, never exit
2 (`_hook_run.advise`). The CM-* rules are about
prose, and a legitimate rationale comment may contain any word at all, so no regex
here clears the ~1% false-positive bar a hard block needs (`AGENTS.md`). What this
hook catches is the *mechanical* subset — the tells that are almost never anything
else:

- decoration: emoji, an exclaimed comment (CM-005)
- edit narration: a `NEW:` label, a sentence about what an edit did, a was/now pair (CM-005)
- filler preambles: `// Note:`, `// Basically`, `// Here's how this works` (CM-005)
- banner/divider comments: `# ===== helpers =====` (CM-004)
- reader address, first-person deliberation, deliberation left in place (CM-006)
- `TODO`/`FIXME` carrying no ticket or link (CM-006)

The prose judgement — is this narration, does it say *what* instead of *why*, does
the docstring add anything — stays in review; this hook cannot see it.

Comment and docstring extraction is shared with the model-judge hook and lives in
`_comment_scan.py`. Machine directives (linter pragmas, shebangs, encoding lines,
SPDX) are prose to no one and are never flagged.

One finding per line, first match winning, capped so a chatty file cannot flood the
transcript. Stdlib only. Exit 0 always.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _comment_scan import commented_lines, is_directive, strip_marker  # noqa: E402
from _hook_run import advise, advisory_message, read_payload, resolve_target  # noqa: E402
from _languages import SOURCE_EXTENSIONS  # noqa: E402

ADVISORY_LEAD = (
    "coding-standards (advisory: not hard-blocked, but each is still a must-fix "
    "violation — delete the comment or record it accepted with a reason).\n"
    "The default for a comment is none: see "
    "skills/coding-standards/references/common/comments.md.\n"
)

MAX_FINDINGS = 15

_TODO = re.compile(r"^(?:TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
_TRACKED = re.compile(r"[A-Z][A-Z0-9]+-\d+|#\d+|https?://")
_TODO_FINDING = (
    "CM-006",
    "TODO/FIXME carrying no ticket or link — do it now, or track it where work is tracked",
)

# (pattern, rule, what it is). First match on a line wins, so order is priority.
SLOP_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"[\U0001f000-\U0001faff✅❌✨⭐❗‼]"),
        "CM-005",
        "emoji in a comment — decoration reads as generated, not written",
    ),
    (
        re.compile(
            r"^(?:NEW|OLD|WAS|NOW|UPDATED?|CHANGED?|FIXED|ADDED|REMOVED|RENAMED|MOVED"
            r"|REFACTORED|PREVIOUSLY)\b\s*[:!\-–—]"
        ),
        "CM-005",
        "edit narration — the change belongs in the commit message, not the file",
    ),
    (
        re.compile(
            r"\b(?:updated|changed|switched|renamed|moved|refactored|bumped|replaced|reverted)"
            r"\s+(?:this|it|the|to|from|so|for|because|in favou?r)\b",
            re.IGNORECASE,
        ),
        "CM-005",
        "edit narration — the change belongs in the commit message, not the file",
    ),
    (
        re.compile(r"\bwas\s+\S+,\s*(?:now|is now)\b", re.IGNORECASE),
        "CM-005",
        "edit narration (was X, now Y) — state the current behaviour and stop",
    ),
    (
        re.compile(
            r"\b(?:used to (?:be|do|call|live|return|handle)"
            r"|no longer (?:needed|used|necessary|required)"
            r"|previously (?:we|this|it|the code)"
            r"|before (?:this|the) (?:change|refactor|fix)"
            r"|in the old (?:version|code|approach|way)"
            r"|legacy (?:approach|behaviou?r))\b",
            re.IGNORECASE,
        ),
        "CM-005",
        "history narration — the file states the current fact; git holds the past",
    ),
    (
        re.compile(
            r"^(?:note|important|caution|fyi|heads[ -]up|reminder|basically|obviously"
            r"|clearly|essentially|tl;?dr|here'?s (?:how|what|the)|here is (?:how|what)"
            r"|as you can see|in other words|simply put|to be clear)\b[:,]?",
            re.IGNORECASE,
        ),
        "CM-005",
        "filler preamble — if the point matters, state it plainly; if not, cut it",
    ),
    (
        re.compile(
            r"\b(?:as (?:you )?requested|as we discussed|as (?:per )?(?:your|the) request"
            r"|per your (?:request|suggestion|comment|feedback)"
            r"|per our (?:discussion|conversation)"
            r"|you (?:asked|wanted|mentioned|suggested)|let me know|feel free to"
            r"|hope (?:this|that) helps|if you (?:want|prefer|need|like)"
            r"|for your reference|implements the (?:user story|requirement|task))\b",
            re.IGNORECASE,
        ),
        "CM-006",
        "addressed to a person — chat and review talk belong outside the file",
    ),
    (
        re.compile(
            r"\bI['’]?(?:ve|m|ll|d)\b"
            r"|\bI (?:think|guess|assume|believe|left|added|chose|went|decided|kept"
            r"|prefer|suspect|am|would|will|just|didn'?t|don'?t|wasn'?t)\b"
        ),
        "CM-006",
        "first-person deliberation — thinking out loud is not documentation",
    ),
    (
        re.compile(
            r"\b(?:we could (?:also|instead|maybe|probably)|we should probably"
            r"|we might want|could (?:also|instead) (?:use|do|go|try)"
            r"|not sure (?:if|whether|why|how)|unsure (?:if|whether)"
            r"|leaving (?:this|it) (?:here|for now)|open question|thoughts\?)\b",
            re.IGNORECASE,
        ),
        "CM-006",
        "deliberation left in the file — a rejected option earns a line only as a constraint",
    ),
    (
        re.compile(r"^[=\-~_#+]{3,}\s*$|^[=\-~_#+]{2,}[^\n]*?[=\-~_#+]{2,}$"),
        "CM-004",
        "banner/divider comment — vertical spacing groups code without one",
    ),
    (
        re.compile(r"\w!(?:\s|$)"),
        "CM-005",
        "exclamation in a comment — decoration reads as generated, not written",
    ),
]


def slop_in(prose: str) -> tuple[str, str] | None:
    """The (rule, label) of the first tell in one comment line, or None if clean."""
    if _TODO.search(prose) and not _TRACKED.search(prose):
        return _TODO_FINDING
    for pattern, rule, label in SLOP_PATTERNS:
        if pattern.search(prose):
            return rule, label
    return None


def collect(new_content: str, file_path: str, ext: str) -> list[str]:
    """Advisory messages for one file, at most one per comment line."""
    findings: list[str] = []
    for lineno, raw in commented_lines(new_content, ext):
        if is_directive(raw):
            continue
        prose = strip_marker(raw)
        if not prose:
            continue
        found = slop_in(prose)
        if found:
            rule, label = found
            findings.append(f"{file_path}:{lineno} — {rule}: {label}")
    return findings


def main() -> int:
    payload = read_payload()
    if payload is None:
        return 0
    target = resolve_target(payload, set(SOURCE_EXTENSIONS))
    if target is None:
        return 0
    file_path, new_content = target
    findings = collect(new_content, file_path, Path(file_path).suffix)
    if not findings:
        return 0

    shown = findings[:MAX_FINDINGS]
    hidden = len(findings) - len(shown)
    tail = f"  - (+{hidden} more comment findings in this file)\n" if hidden else ""
    return advise(advisory_message(shown, ADVISORY_LEAD, tail))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: advise-comment-slop internal error, skipped ({exc})\n")
        sys.exit(0)
