#!/usr/bin/env python3
"""Regression test — the session-start check repairs a dead enforcement, or explains it.

Enforcement can be absent without a symptom, so the check runs the installer itself
rather than asking someone to. Three behaviours carry that: an incomplete wiring is
repaired and the session told to restart; a repair already known to fail is not
attempted again, and the reported cause is passed through instead of a guessed one; a
live wiring produces no session-start noise at all.

Everything runs against a temp `$HOME` with the working venv handed to the installer,
so no real settings.json is touched and no package is fetched.

    python3 hooks/tests/test-health-check-relay.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import report_failures  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent.parent
HEALTH_CHECK = "hooks/session-health-check.py"


def reuse_venv() -> str | None:
    """The venv to hand the installer so it skips the pip build, or None if this
    interpreter has no grammars — the repair path can't be exercised without one."""
    try:
        import tree_sitter, tree_sitter_typescript  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return str(Path(sys.executable).parent.parent)


def sandbox(root: Path) -> Path:
    """A temp $HOME with the skill installed and a single lone hook wired."""
    home = root / "home"
    skills = home / ".claude" / "skills"
    skills.mkdir(parents=True)
    (skills / "coding-standards").symlink_to(SKILL_DIR)
    wired = skills / "coding-standards" / "hooks" / "block-junk-paths.py"
    settings = {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": "Write|Edit|MultiEdit",
                    "hooks": [{"type": "command", "command": f"python3 {wired}"}],
                }
            ]
        }
    }
    (home / ".claude" / "settings.json").write_text(json.dumps(settings))
    return home


def run_in(home: Path, venv: str, script: str, *args: str) -> subprocess.CompletedProcess:
    installed = home / ".claude" / "skills" / "coding-standards"
    return subprocess.run(
        ["python3", str(installed / script), *args],
        input="{}",
        capture_output=True,
        text=True,
        timeout=300,
        env={
            **os.environ,
            "HOME": str(home),
            "XDG_DATA_HOME": str(home / "data"),
            "CODING_STANDARDS_VENV": venv,
        },
    )


def stamp(home: Path) -> Path:
    return home / "data" / "coding-standards" / "repair-failed"


def repair_failures(venv: str) -> list[str]:
    """An incomplete wiring is wired, and the session told the repair lands next time."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        home = sandbox(Path(tmp))
        if run_in(home, venv, "bootstrap.py", "--verify").returncode == 0:
            return ["the sandbox wiring was accepted as complete — the fixture no longer degrades"]

        healed = run_in(home, venv, HEALTH_CHECK)
        if healed.returncode != 0:
            return [f"the check must exit 0 so Claude sees stdout, got {healed.returncode}"]
        if "wired now" not in healed.stdout:
            failures.append(f"repair not reported as done: {healed.stdout.strip()!r}")
        if "NEXT session" not in healed.stdout:
            failures.append("the report does not say the repair lands on the next session")
        if run_in(home, venv, "bootstrap.py", "--verify").returncode != 0:
            failures.append("the check reported a repair that did not actually wire anything")

        quiet = run_in(home, venv, HEALTH_CHECK)
        if quiet.stdout.strip():
            failures.append(f"a live wiring still produced session-start noise: {quiet.stdout!r}")
    return failures


def known_failure_failures(venv: str) -> list[str]:
    """A repair already known to fail is not retried, and the real cause is passed on."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        home = sandbox(Path(tmp))
        reported = run_in(home, venv, "bootstrap.py", "--verify").stdout
        stamp(home).parent.mkdir(parents=True, exist_ok=True)
        stamp(home).write_text(reported.strip(), encoding="utf-8")
        before = (home / ".claude" / "settings.json").read_text()

        held = run_in(home, venv, HEALTH_CHECK)
        if (home / ".claude" / "settings.json").read_text() != before:
            failures.append("a repair known to fail was attempted again")
        for line in (ln.strip() for ln in reported.splitlines() if ln.strip()):
            if line not in held.stdout:
                failures.append(f"the report dropped a reported line: {line!r}")
                break
    return failures


def main() -> int:
    venv = reuse_venv()
    if venv is None:
        print(
            "SKIP health-check-relay: tree-sitter not importable here (run with the venv "
            "python); run-all.py reports this as DEGRADED."
        )
        return 0
    failures = repair_failures(venv) + known_failure_failures(venv)
    return report_failures("health-check-relay", failures, 7)


if __name__ == "__main__":
    sys.exit(main())
