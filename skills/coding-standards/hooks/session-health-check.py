#!/usr/bin/env python3
"""SessionStart hook — restore write-time enforcement, or say loudly that it is off.

The PreToolUse hooks are the enforcement, and it can be absent without a symptom:
scripts the wiring never picked up, an interpreter that cannot load the required
packages, a moved skill dir leaving every hook to exit 127. Nothing blocks, and the
user keeps writing unchecked code believing they are covered (ISS-006).

So this hook repairs rather than reports. It asks whether enforcement is live, and on
a failure runs the installer itself. That rewrites settings.json without being asked,
which is the deliberate trade: a session that silently checks nothing is worse than a
configuration write the user did not initiate. Settings are read at session start, so
a repair lands for the NEXT session and the report says so.

A repair that fails is remembered against the report that prompted it. A machine that
cannot be fixed — no network for the package install, an unwritable settings file —
therefore spends the attempt once rather than at every session start, and reports from
then on. Any different failure is a new report, and earns a fresh attempt.

Output contract, from the Claude Code hooks docs: SessionStart cannot block, and on
exit 2 stdout is discarded and only stderr reaches the user. The reader who can act on
this is Claude, so the report goes to stdout and the hook exits 0 — the case where
SessionStart stdout is added to the context.

Wired with a stable `python3` (NOT the venv) on purpose: running under the venv it is
meant to police would let a wiped venv take the check down with it.

Stdlib only.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Do NOT resolve: the invoked path carries the `.claude/...` segment bootstrap's
# scope detection needs (resolving collapses the install symlink to its canonical
# target, which has no `.claude` ancestor — see _bootstrap/paths.py).
BOOTSTRAP = Path(__file__).parent.parent / "bootstrap.py"

VERIFY_TIMEOUT = 60
# Under the 600s SessionStart default even with a verify either side, and generous
# enough for a package install on a cold machine.
REPAIR_TIMEOUT = 420

_OFF = "⚠ coding-standards: write-time enforcement is NOT active — code you write is NOT checked."
_WIRED = (
    "coding-standards: write-time enforcement was not wired, and has been wired now. "
    "Settings are read at session start, so it activates on the NEXT session — code "
    "written in THIS one is still unchecked. Restart when convenient."
)


def stamp_path() -> Path:
    """The file remembering a repair that already failed."""
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "coding-standards" / "repair-failed"


def run_bootstrap(args: list[str], timeout: int) -> subprocess.CompletedProcess | None:
    """Bootstrap's result, or None when it could not be run at all."""
    try:
        return subprocess.run(
            [sys.executable, str(BOOTSTRAP), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception:  # noqa: BLE001 — a health check must never break the session
        return None


def repair_already_failed(reported: str) -> bool:
    """True when the last attempt failed against this same report."""
    try:
        return stamp_path().read_text(encoding="utf-8").strip() == reported.strip()
    except OSError:
        return False


def remember_failure(reported: str | None) -> None:
    """Record a failed repair, or clear the record once one succeeds."""
    path = stamp_path()
    try:
        if reported is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(reported.strip(), encoding="utf-8")
    except OSError:
        # An unwritable stamp costs one redundant repair attempt next session, nothing more.
        return


def report(headline: str, detail: str) -> int:
    """Hand the outcome to Claude as session context."""
    body = detail.strip()
    sys.stdout.write(f"{headline}\n{body}\n" if body else f"{headline}\n")
    return 0


def main() -> int:
    verify = run_bootstrap(["--verify"], VERIFY_TIMEOUT)
    if verify is None or verify.returncode == 0:
        return 0

    reported = verify.stdout
    if repair_already_failed(reported):
        return report(f"{_OFF} The last automatic repair failed; fix this by hand:", reported)

    repair = run_bootstrap(["--auto-install"], REPAIR_TIMEOUT)
    recheck = run_bootstrap(["--verify"], VERIFY_TIMEOUT) if repair is not None else None
    if recheck is not None and recheck.returncode == 0:
        remember_failure(None)
        return report(_WIRED, "")

    remember_failure(reported)
    said = (repair.stdout or repair.stderr) if repair is not None else "bootstrap could not run"
    return report(f"{_OFF} The automatic repair failed. What the installer said:", said)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: session-health-check error, skipped ({exc})\n")
        sys.exit(0)
