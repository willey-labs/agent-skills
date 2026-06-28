#!/usr/bin/env python3
"""SessionStart + UserPromptSubmit hook — inject the writing-standards reminder.

Wired to both events by bootstrap.py. For both, the hook's stdout is added to
Claude's context (verified against the Claude Code hooks docs: "stdout is added
as context that Claude can see and act on"). So this script just prints the
reminder and exits 0 — no JSON needed.

The point: the full rules live in references/common/, read once when a document
is actually written; this short reminder rides every turn so the rules don't get
buried as a conversation grows (the failure mode the skill exists to fix).

NEVER exits non-zero. A non-zero UserPromptSubmit hook BLOCKS the user's prompt
and shows stderr instead — a reminder must never do that. Any error → exit 0.

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Skill dir as invoked (through the .claude/... install path) — kept recognizable
# so the agent can open the referenced files. Not resolved; display only.
SKILL_DIR = Path(__file__).parent.parent
COMMON_REFS = SKILL_DIR / "references" / "common"

REMINDER = f"""\
[writing-standards] Re-injected each turn so it isn't buried. Applies when you produce a
DOCUMENT — README, spec, rule, skill, design doc, guide, review — not to normal chat or code.

Source → deliverable: abstract the source, never echo it.
  - Code → doc: write what the system DOES, in plain language. No code, no function/class/file names.
  - Discussion → rule: write the general principle, not the example just discussed; if you show an
    example, invent a fresh one — never reuse the case or names from this chat.
  The source is what you learned from; it stays out of the output.

No slop: cut hedging (may/might/generally/potentially), hype (leverage, robust, seamless,
cutting-edge), throat-clearing ("let's take a look at…"), cheerleading ("Great job!"), reflexive
headers/bold/lists, and any sentence that carries no information. Active voice; say each fact once.

Before writing or reviewing a document, read the full rules:
  {COMMON_REFS / "source-to-deliverable.md"}
  {COMMON_REFS / "anti-slop.md"}
"""


def main() -> int:
    sys.stdout.write(REMINDER)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never block a prompt — fail open, note on stderr
        sys.stderr.write(f"writing-standards: inject reminder skipped ({exc})\n")
        sys.exit(0)
