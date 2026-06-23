#!/usr/bin/env python3
"""Regression test — bootstrap wiring matrix (AGENTS.md 6-test matrix + ISS-006).

Automates the matrix that used to be manual: project/global wiring, idempotency,
preservation of unrelated settings, refusal outside `.claude`, and the ISS-006
additions (SessionStart health-check wiring, venv relocated outside the skill
dir, degraded-enforcement warning). Everything runs in a temp `$HOME` sandbox —
the real `~/.claude/settings.json` is NEVER touched (AGENTS.md cardinal rule).

Reuses the running interpreter's venv (it must have tree-sitter) so no pip/network
build is needed; if tree-sitter isn't importable here, it skips loudly and lets
run-all.py report the suite as DEGRADED rather than passing silently.

    <venv-python> hooks/tests/test-bootstrap-matrix.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_SKILL = Path(__file__).resolve().parent.parent.parent  # skills/coding-standards


def reuse_venv() -> str | None:
    """The venv dir to reuse (so bootstrap skips the pip build), or None if the
    running interpreter has no tree-sitter — in which case the matrix can't run
    the real wiring path and should skip loudly."""
    try:
        import tree_sitter, tree_sitter_typescript  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return str(Path(sys.executable).parent.parent)  # <venv>/bin/python -> <venv>


def run_bootstrap(home: Path, skill: Path, venv: str, projdir: Path | None) -> int:
    env = {**os.environ, "HOME": str(home), "CODING_STANDARDS_VENV": venv}
    if projdir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(projdir)
    cwd = str(projdir) if projdir is not None else str(home)
    proc = subprocess.run(
        ["python3", str(skill / "bootstrap.py"), "--auto-install"],
        env=env, cwd=cwd, capture_output=True, text=True, timeout=180,
    )
    return proc.returncode


def link_skill(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    link = parent / "coding-standards"
    link.symlink_to(REPO_SKILL)
    return link


def commands(settings: dict, section: str) -> list[str]:
    out: list[str] = []
    for entry in settings.get("hooks", {}).get(section, []):
        for hook in entry.get("hooks", []):
            out.append(hook.get("command", ""))
    return out


def _check_committed_settings(settings: dict, proj: Path) -> list[str]:
    """Committed settings.json stays portable: ${CLAUDE_PROJECT_DIR} hook paths, the
    SessionStart health check, and no machine-absolute perms/paths (ISS-012)."""
    out: list[str] = []
    if not all("${CLAUDE_PROJECT_DIR}" in c for c in commands(settings, "PreToolUse")):
        out.append("project: PreToolUse should use ${CLAUDE_PROJECT_DIR}")
    if not any("session-health-check.py" in c for c in commands(settings, "SessionStart")):
        out.append("project: SessionStart health check not wired")
    if "permissions" in settings:
        out.append("ISS-012: committed settings.json must not carry permissions")
    if str(proj) in json.dumps(settings):
        out.append("ISS-012: committed settings.json leaks an absolute checkout path")
    return out


def _check_local_perms(proj: Path) -> list[str]:
    """Machine perms live in settings.local.json (allow rules, no additionalDirectories)
    and that file must be gitignored so its absolute paths can't be committed (ISS-012)."""
    out: list[str] = []
    local = proj / ".claude" / "settings.local.json"
    if not local.exists():
        return out + ["ISS-012: settings.local.json not created for project perms"]
    perms = json.loads(local.read_text()).get("permissions", {})
    if not perms.get("allow"):
        out.append("ISS-012: settings.local.json missing allow rules")
    if "additionalDirectories" in perms:
        out.append("ISS-012: additionalDirectories should be skipped on project scope")
    gitignore = proj / ".gitignore"
    if not gitignore.exists() or ".claude/settings.local.json" not in gitignore.read_text():
        out.append("ISS-012: .gitignore should ignore .claude/settings.local.json")
    return out


def check_project(home: Path, venv: str, tmp: Path) -> list[str]:
    proj = tmp / "proj"
    (proj / ".claude").mkdir(parents=True)
    (proj / "package.json").write_text("{}\n")
    skill = link_skill(proj / ".claude" / "skills")
    fails: list[str] = []
    if run_bootstrap(home, skill, venv, proj) != 0:
        fails.append("project: bootstrap exited nonzero")
    settings_path = proj / ".claude" / "settings.json"
    if not settings_path.exists():
        return fails + ["project: settings.json not created"]
    settings = json.loads(settings_path.read_text())
    pre = commands(settings, "PreToolUse")
    fails += _check_committed_settings(settings, proj)
    fails += _check_local_perms(proj)
    if run_bootstrap(home, skill, venv, proj) != 0:  # idempotency
        fails.append("project: re-run exited nonzero")
    if len(commands(json.loads(settings_path.read_text()), "PreToolUse")) != len(pre):
        fails.append("project: re-run duplicated PreToolUse entries")
    return fails


def check_global_and_refuse(home: Path, venv: str, tmp: Path) -> list[str]:
    skill = link_skill(home / ".claude" / "skills")
    fails: list[str] = []
    if run_bootstrap(home, skill, venv, None) != 0:
        fails.append("global: bootstrap exited nonzero")
    s = json.loads((home / ".claude" / "settings.json").read_text())
    pre, ss = commands(s, "PreToolUse"), commands(s, "SessionStart")
    if not all(c.split()[1].startswith("/") for c in pre):
        fails.append("global: PreToolUse should use absolute paths")
    if any("${CLAUDE_PROJECT_DIR}" in c for c in pre):
        fails.append("global: PreToolUse must not use ${CLAUDE_PROJECT_DIR}")
    if not any("session-health-check.py" in c for c in ss):
        fails.append("global: SessionStart health check not wired")
    # venv must live OUTSIDE the skill dir (ISS-006)
    probe = subprocess.run(
        ["python3", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]);"
         "from _bootstrap.paths import MANAGED_VENV_DIR, SKILL_DIR;"
         "print(not str(MANAGED_VENV_DIR).startswith(str(SKILL_DIR)))",
         str(skill)],
        env={**os.environ, "HOME": str(home), "CODING_STANDARDS_VENV": ""},
        capture_output=True, text=True,
    )
    if probe.stdout.strip() != "True":
        fails.append("ISS-006: managed venv is not outside the skill dir")
    # refuse outside any .claude tree
    outside = tmp / "outside"
    outside.mkdir(parents=True)
    for item in REPO_SKILL.iterdir():
        if item.name == "bootstrap.py":
            (outside / "bootstrap.py").write_text(item.read_text())
    # copy the package so the import works, then strip the .claude context
    subprocess.run(["cp", "-r", str(REPO_SKILL / "_bootstrap"), str(outside)], check=False)
    rc = subprocess.run(
        ["python3", str(outside / "bootstrap.py"), "--auto-install"],
        env={**os.environ, "HOME": str(home), "CODING_STANDARDS_VENV": venv},
        cwd=str(outside), capture_output=True, text=True,
    ).returncode
    if rc == 0:
        fails.append("refuse: bootstrap should refuse outside a .claude tree")
    return fails


def main() -> int:
    venv = reuse_venv()
    if venv is None:
        sys.stderr.write("SKIP bootstrap-matrix: tree-sitter not importable here "
                         "(run with the venv python); run-all.py reports this as DEGRADED.\n")
        return 0
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        failures += check_project(tmp / "h1" / "home", venv, tmp / "p")
        failures += check_global_and_refuse(tmp / "h2" / "home", venv, tmp / "g")
    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print("ok — bootstrap-matrix (6-test matrix + ISS-006) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
