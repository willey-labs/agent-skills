#!/usr/bin/env python3
"""SessionStart + UserPromptSubmit hook — inject the coding-standards reminder.

For both events the hook's stdout is added to Claude's context, so this script
prints the reminder and exits 0. It carries the two rules that enforcement cannot
recover once they are missed: the comment default, because a write refused at the
last moment costs a whole turn, and the write-through-tools rule, because a file
written by shell redirection never reaches a hook at all.

NEVER exits non-zero. A non-zero UserPromptSubmit hook blocks the user's prompt and
shows stderr instead, so every error path exits 0.

Stdlib only.
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
COMMON_REFS = SKILL_DIR / "references" / "common"

REMINDER = f"""\
[coding-standards] Re-injected each turn so it isn't buried. Applies to CODE you write or edit.

Comments — the default is NONE (CM-001..CM-007). Say it in the name and the shape of the code.
  - A comment earns its place only by carrying what the code cannot: a constraint, a sharp edge,
    an external reference. Never narrate the code, the edit, or your own reasoning.
  - ONE line, or none (CM-007). A block past one line of prose is refused at write time. Past one
    line you have stopped stating the constraint and started arguing the decision to a reviewer —
    keep the fact the next reader needs, cut the case for the choice. File-header docstrings only
    are exempt.
  - Nothing addressed to a person, no first-person deliberation, no weighed alternatives, no
    untracked TODO, no emoji, no `Note:` preamble. If a thought belongs in the reply, put it there.

Author code ONLY through Write/Edit/MultiEdit — never shell redirection (`>`, `tee`, `sed -i`,
heredoc). The enforcement hooks fire on those tools alone; a shell-written file bypasses every one.

Before writing or reviewing code, read the full rules in:
  {COMMON_REFS}
"""


def main() -> int:
    sys.stdout.write(REMINDER)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # never block a prompt — fail open, note on stderr
        sys.stderr.write(f"coding-standards: inject reminder skipped ({exc})\n")
        sys.exit(0)
