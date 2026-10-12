#!/usr/bin/env python3
"""Regression test — bootstrap wiring matrix (AGENTS.md 6-test matrix).

Automates the whole matrix: project/global wiring, idempotency,
preservation of unrelated settings, refusal outside `.claude`, replacement of an
older install's entries on upgrade, plus the SessionStart health-check wiring, the
venv living outside the skill dir, and the opt-in comment judge. Everything runs in
a temp `$HOME` sandbox — the real `~/.claude/settings.json` is NEVER touched
(AGENTS.md cardinal rule).

Reuses the running interpreter's venv (it must have tree-sitter) so no pip/network
build is needed; if tree-sitter isn't importable here, it skips loudly and lets
run-all.py report the suite as DEGRADED rather than passing silently.

    <venv-python> hooks/tests/test-bootstrap-matrix.py
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from bootstrap_sandbox import (
    REPO_SKILL,
    Sandbox,
    commands,
    link_skill,
    project_sandbox,
    reuse_venv,
    run_bootstrap,
    wire_seeded_project,
)

sys.path.insert(0, str(REPO_SKILL))
from _bootstrap.hook_identity import (  # noqa: E402
    comment_judge_wired,
    is_our_entry,
    is_our_session_entry,
    missing_wired_scripts,
)

OLD_HOOKS_DIR = "/old/install/coding-standards/hooks"
UNRELATED_PRE_TOOL_USE = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo audit"}]}
UNRELATED_STOP = {"hooks": [{"type": "command", "command": "notify-send done"}]}


def old_install_command(script: str) -> dict:
    return {"type": "command", "command": f"python3 {OLD_HOOKS_DIR}/{script}"}


PRESERVE_SEED = {
    "model": "opus",
    "env": {"AUDIT": "1"},
    "hooks": {"PreToolUse": [UNRELATED_PRE_TOOL_USE], "Stop": [UNRELATED_STOP]},
}
UPGRADE_SEED = {
    "hooks": {
        "PreToolUse": [
            UNRELATED_PRE_TOOL_USE,
            {
                "matcher": "Write|Edit",
                "hooks": [
                    old_install_command("block-junk-paths.py"),
                    old_install_command("warn-god-file.py"),
                ],
            },
        ],
        "SessionStart": [
            {"matcher": "startup", "hooks": [old_install_command("session-health-check.py")]},
        ],
    },
}
JUDGE_RUNS = ((), ("--with-comment-judge",), (), ("--without-comment-judge",))
JUDGE_STATES = [False, True, True, False]


def _check_committed_settings(settings: dict, proj: Path) -> list[str]:
    """Committed settings.json stays portable: ${CLAUDE_PROJECT_DIR} hook paths, the
    SessionStart health check, and no machine-absolute perms/paths."""
    out: list[str] = []
    if not all("${CLAUDE_PROJECT_DIR}" in c for c in commands(settings, "PreToolUse")):
        out.append("project: PreToolUse should use ${CLAUDE_PROJECT_DIR}")
    if not any("session-health-check.py" in c for c in commands(settings, "SessionStart")):
        out.append("project: SessionStart health check not wired")
    if "permissions" in settings:
        out.append("project: committed settings.json must not carry permissions")
    if str(proj) in json.dumps(settings):
        out.append("project: committed settings.json leaks an absolute checkout path")
    return out


def _check_local_perms(proj: Path) -> list[str]:
    """Machine perms live in settings.local.json (allow rules, no additionalDirectories)
    and that file must be gitignored so its absolute paths can't be committed."""
    out: list[str] = []
    local = proj / ".claude" / "settings.local.json"
    if not local.exists():
        return out + ["project: settings.local.json not created for project perms"]
    perms = json.loads(local.read_text()).get("permissions", {})
    if not perms.get("allow"):
        out.append("project: settings.local.json missing allow rules")
    if "additionalDirectories" in perms:
        out.append("project: additionalDirectories should be skipped on project scope")
    gitignore = proj / ".gitignore"
    if not gitignore.exists() or ".claude/settings.local.json" not in gitignore.read_text():
        out.append("project: .gitignore should ignore .claude/settings.local.json")
    return out


def check_project(home: Path, venv: str, tmp: Path) -> list[str]:
    sandbox = project_sandbox(home, venv, tmp / "proj")
    fails: list[str] = []
    if run_bootstrap(sandbox) != 0:
        fails.append("project: bootstrap exited nonzero")
    if not sandbox.project_settings.exists():
        return fails + ["project: settings.json not created"]
    settings = json.loads(sandbox.project_settings.read_text())
    pre = commands(settings, "PreToolUse")
    fails += _check_committed_settings(settings, sandbox.project)
    fails += _check_local_perms(sandbox.project)
    if run_bootstrap(sandbox) != 0:  # idempotency
        fails.append("project: re-run exited nonzero")
    if len(commands(json.loads(sandbox.project_settings.read_text()), "PreToolUse")) != len(pre):
        fails.append("project: re-run duplicated PreToolUse entries")
    return fails


def check_global_and_refuse(home: Path, venv: str, tmp: Path) -> list[str]:
    sandbox = Sandbox(home=home, skill=link_skill(home / ".claude" / "skills"), venv=venv)
    fails: list[str] = []
    if run_bootstrap(sandbox) != 0:
        fails.append("global: bootstrap exited nonzero")
    s = json.loads((home / ".claude" / "settings.json").read_text())
    pre, ss = commands(s, "PreToolUse"), commands(s, "SessionStart")
    if not all(shlex.split(c)[1].startswith("/") for c in pre):
        fails.append("global: PreToolUse should use absolute paths")
    if any("${CLAUDE_PROJECT_DIR}" in c for c in pre):
        fails.append("global: PreToolUse must not use ${CLAUDE_PROJECT_DIR}")
    if not any("session-health-check.py" in c for c in ss):
        fails.append("global: SessionStart health check not wired")
    # venv must live OUTSIDE the skill dir
    probe = subprocess.run(
        ["python3", "-c",
         "import sys; sys.path.insert(0, sys.argv[1]);"
         "from _bootstrap.paths import MANAGED_VENV_DIR, SKILL_DIR;"
         "print(not str(MANAGED_VENV_DIR).startswith(str(SKILL_DIR)))",
         str(sandbox.skill)],
        env={**os.environ, "HOME": str(home), "CODING_STANDARDS_VENV": ""},
        capture_output=True, text=True,
    )
    if probe.stdout.strip() != "True":
        fails.append("global: managed venv is not outside the skill dir")
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


def check_preserves_unrelated(home: Path, venv: str, tmp: Path) -> list[str]:
    returncode, settings = wire_seeded_project(project_sandbox(home, venv, tmp / "proj"), PRESERVE_SEED)
    fails = [] if returncode == 0 else ["preserve: bootstrap exited nonzero"]
    fails += [
        f"preserve: top-level {key!r} changed"
        for key in ("model", "env")
        if settings.get(key) != PRESERVE_SEED[key]
    ]
    hooks = settings.get("hooks", {})
    if UNRELATED_PRE_TOOL_USE not in hooks.get("PreToolUse", []):
        fails.append("preserve: unrelated PreToolUse entry lost or altered")
    if UNRELATED_STOP not in hooks.get("Stop", []):
        fails.append("preserve: unrelated Stop entry lost or altered")
    return fails + [f"preserve: not wired — {gap}" for gap in missing_wired_scripts(settings)]


def check_upgrade_replaces_ours(home: Path, venv: str, tmp: Path) -> list[str]:
    returncode, settings = wire_seeded_project(project_sandbox(home, venv, tmp / "proj"), UPGRADE_SEED)
    fails = [] if returncode == 0 else ["upgrade: bootstrap exited nonzero"]
    hooks = settings.get("hooks", {})
    pre_tool_use = hooks.get("PreToolUse", [])
    if UNRELATED_PRE_TOOL_USE not in pre_tool_use:
        fails.append("upgrade: unrelated PreToolUse entry lost or altered")
    if sum(map(is_our_entry, pre_tool_use)) != 1:
        fails.append("upgrade: expected exactly one PreToolUse entry of ours")
    if sum(map(is_our_session_entry, hooks.get("SessionStart", []))) != 1:
        fails.append("upgrade: expected exactly one SessionStart entry of ours")
    if OLD_HOOKS_DIR in json.dumps(settings):
        fails.append("upgrade: a command from the older install survived")
    return fails + [f"upgrade: not wired — {gap}" for gap in missing_wired_scripts(settings)]


def check_comment_judge_opt_in(home: Path, venv: str, tmp: Path) -> list[str]:
    sandbox = project_sandbox(home, venv, tmp / "proj")
    fails: list[str] = []
    states: list[bool] = []
    for flags in JUDGE_RUNS:
        if run_bootstrap(sandbox, *flags) != 0:
            fails.append(f"judge: bootstrap {' '.join(flags) or '(no flag)'} exited nonzero")
        states.append(comment_judge_wired(json.loads(sandbox.project_settings.read_text())))
    if states != JUDGE_STATES:
        fails.append(f"judge: wired after each run {states}, want {JUDGE_STATES}")
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
        failures += check_preserves_unrelated(tmp / "h3" / "home", venv, tmp / "u")
        failures += check_upgrade_replaces_ours(tmp / "h4" / "home", venv, tmp / "o")
        failures += check_comment_judge_opt_in(tmp / "h5" / "home", venv, tmp / "j")
    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print("ok — bootstrap-matrix cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
