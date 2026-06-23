#!/usr/bin/env python3
"""SessionStart hook — make degraded coding-standards enforcement LOUD.

The PreToolUse hooks are the enforcement. If their interpreter or scripts go
missing (a wiped venv, a moved/renamed skill dir), each hook exits 127 and never
blocks — enforcement is silently dead and the user keeps writing unchecked code
believing they're covered (ISS-006). This hook runs at session start, asks
`bootstrap.py --verify` whether enforcement is actually live, and if not, says so
loudly. It NEVER blocks the session (SessionStart hooks can't, and shouldn't).

Wired with a stable `python3` (NOT the venv) on purpose: if it ran under the venv
it's meant to police, a wiped venv would take the health check down with it.

Output contract (verified against the Claude Code hooks docs):
- stdout is added to Claude's context — so the agent can self-heal by re-running
  bootstrap, or tell the user.
- on exit 2, stderr is shown to the user directly.
We write the warning to BOTH and exit 2 when degraded; exit 0 (silent) when healthy.

Stdlib only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Do NOT resolve: the invoked path carries the `.claude/...` segment bootstrap's
# scope detection needs (resolving collapses the install symlink to its canonical
# target, which has no `.claude` ancestor — see _bootstrap/paths.py).
BOOTSTRAP = Path(__file__).parent.parent / "bootstrap.py"


def main() -> int:
    try:
        proc = subprocess.run(
            [sys.executable, str(BOOTSTRAP), "--verify"],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception:  # noqa: BLE001 — a health check must never break the session
        return 0
    if proc.returncode == 0:
        return 0  # enforcement is live — stay quiet, no session-start noise

    warning = (
        "⚠ coding-standards: write-time enforcement is NOT active this session. "
        "The hooks' interpreter or scripts are missing (e.g. a wiped venv or a "
        "moved skill dir), so code you write will NOT be checked against the "
        "standards. To restore it, run the skill once (it self-heals on "
        f"activation) or run:\n    python3 {BOOTSTRAP} --auto-install\n"
    )
    sys.stdout.write(warning)   # → Claude's context, so the agent can self-heal
    sys.stderr.write(warning)   # → shown to the user (exit 2)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: session-health-check error, skipped ({exc})\n")
        sys.exit(0)
