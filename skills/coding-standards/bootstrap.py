#!/usr/bin/env python3
"""coding-standards skill — bootstrap entry point.

Wires the PreToolUse enforcement hooks, the `/coding-standards` slash command,
and checks machine readiness on first invocation. Cross-platform (Windows,
Linux, macOS). Stdlib only for the bootstrap itself; the hooks' third-party
dependencies are declared in `_dependencies.REQUIRED_PACKAGES` and are a
REQUIRED install — the skill refuses to wire the hooks until every one loads (no
silent degradation). Today that set is the tree-sitter grammars for the TS/JS
AST checks; the machinery is generic over the list.

This file is the orchestrator and the public entry point. The work lives in the
`_bootstrap/` package — cohesive units, one responsibility each (ST-008/ST-004):

  _bootstrap/paths         filesystem anchors (from this entry script's path)
  _bootstrap/dependencies  REQUIRED_PACKAGES registry + presence checks
  _bootstrap/readiness     host detection + the readiness report
  _bootstrap/install       the mandatory dependency install flow (+ venv fallback)
  _bootstrap/scope         project/global scope detection + the ignore-file template
  _bootstrap/settings      settings.json wiring (hook entry + permissions)
  _bootstrap/command       /coding-standards slash-command install (symlink or copy)

`bootstrap.py` stays at the skill root because SKILL.md Step 0 and the slash
command invoke it by that exact path; `_bootstrap/paths` anchors scope detection
on THIS file's location, so it must not move.

What it does, in order:

1. **Readiness check** (`readiness`) — Python 3.10+, pip, virtualenv, platform,
   and whether every required package imports.
2. **Install the missing required packages** (`install`) — `pip install`
   (`--user` outside venvs), falling back to a dedicated venv on a PEP 668
   refusal. If any still can't load afterward, bootstrap reports a blocking
   issue and exits non-zero WITHOUT wiring the hooks.
3. **Wire hooks** (`settings`) into the correct `settings.json` (project vs
   global, auto-detected from the install path via `scope`).
4. **Symlink the slash command** (`settings`) into `.claude/commands/`.
5. **Seed a `.coding-standards-ignore` template** (`scope`) at the project root.

Idempotent: re-running upgrades hook entries to the current list, refreshes the
symlink, re-checks readiness. Safe to run repeatedly.

Flags:
  --check          Only report readiness; do not install or wire anything.
  --auto-install   Install the missing required packages without the
                   interactive confirm. Implied in non-TTY (agent) contexts —
                   the install is required, so it always proceeds there.
  --verify         Fast read-only check (SKILL.md Step 0 runs this first): exit 0
                   if the skill is already wired for this scope AND the hooks'
                   interpreter can import the required packages; non-zero if a
                   full --auto-install run is needed. Wires/installs nothing.
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from _bootstrap.dependencies import (
    MIN_PYTHON,
    interpreter_has_packages,
    required_packages_available,
)
from _bootstrap.command import install_slash_command
from _bootstrap.install import ensure_global_venv, ensure_required_packages
from _bootstrap.paths import HOOKS_DIR
from _bootstrap.readiness import find_compatible_python, print_readiness, readiness_report
from _bootstrap.scope import IGNORE_FILENAME, detect_scope_and_targets, seed_ignore_template
from _bootstrap.settings import (
    HOOK_FILES,
    build_hook_entry,
    ensure_skill_permissions,
    hook_interpreter,
    interpreter_note,
    is_our_entry,
    load_settings,
    merge_hook_entry,
    warn_project_interpreter_mismatch,
    write_settings,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bootstrap.py",
        description="coding-standards skill bootstrap — readiness check, "
                    "hook wiring, slash command symlink.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true",
        help="Only report readiness; do not install or wire anything.",
    )
    mode.add_argument(
        "--auto-install", action="store_true",
        help="Install the missing required packages without the "
             "interactive confirm (implied in non-TTY agent contexts).",
    )
    mode.add_argument(
        "--verify", action="store_true",
        help="Fast read-only check: exit 0 if the skill is already wired for "
             "this scope and Python is OK (nothing to do); non-zero if a full "
             "--auto-install run is needed. Wires/installs nothing.",
    )
    return parser.parse_args(argv)


@dataclass
class WiringResult:
    """Everything the final summary needs to report what bootstrap wired."""
    scope: str
    settings_path: Path
    commands_dir: Path
    hooks_action: str
    cmd_action: str
    perms_changed: bool
    hook_python: str
    venv_python: Path | None
    ignore_action: str
    ignore_path: Path | None


def report_install_result(result: WiringResult) -> int:
    """Print the post-wiring summary and return the process exit code."""
    if (
        result.hooks_action == "noop"
        and result.cmd_action == "noop"
        and not result.perms_changed
        and result.ignore_action != "created"
    ):
        print(
            f"\ncoding-standards: already installed — {result.settings_path} "
            f"({result.scope}). No changes."
        )
        return 0

    verb = {"added": "Wired", "updated": "Updated", "noop": "Unchanged"}[result.hooks_action]
    cmd_verb = {"created": "linked", "refreshed": "refreshed", "noop": "unchanged"}[result.cmd_action]
    print(
        f"\ncoding-standards: {verb} {len(HOOK_FILES)} PreToolUse hooks into "
        f"{result.settings_path} ({result.scope});\n"
        f"  /coding-standards command {cmd_verb} at "
        f"{result.commands_dir / 'coding-standards.md'}.\n"
        f"  Hook commands use: {result.hook_python}\n"
        f"    ({interpreter_note(result.scope, result.venv_python)}).\n"
        f"  Hooks dir: {HOOKS_DIR}\n"
        f"  Restart your agent if hooks or commands don't activate on the next tool call."
    )
    if result.perms_changed:
        print(
            "  Also pre-approved reading the skill's files + running its scripts "
            "(no permission prompts when it loads references or runs review-files.py)."
        )
    if result.ignore_action == "created" and result.ignore_path is not None:
        print(
            f"  Seeded a {IGNORE_FILENAME} template at {result.ignore_path} — edit it to "
            f"skip project-specific files (it's commented; defaults already cover the usual ones)."
        )
    return 0


def _block_on_missing_packages(report: dict) -> None:
    """Print the blocking-issue summary when required packages can't be loaded."""
    missing = " ".join(report["missing_packages"]) or "required packages"
    print("\n  Blocking issues:")
    print(
        f"    - required packages unavailable ({missing} could not be "
        f"installed or loaded)."
    )
    print(
        f"\n  Install them, then re-run bootstrap:\n"
        f"    {sys.executable} -m pip install {missing}\n"
        f"  Hooks are NOT wired until they load — they back the skill's "
        f"checks (currently the FN-001/FN-005/OD-004 AST checks on TS/JS)."
    )


def _wired_hook_interpreter(pre_tool_use: list) -> str | None:
    """The interpreter our wired hook commands run under (first token of the
    command), or None if no entry of ours is present."""
    for entry in pre_tool_use:
        if not (isinstance(entry, dict) and is_our_entry(entry)):
            continue
        for hook in entry.get("hooks") or []:
            command = (hook or {}).get("command", "")
            parts = command.split()
            if parts:
                return parts[0]
    return None


def verify_already_set_up() -> int:
    """`--verify`: 0 if the skill is genuinely ready (wired AND the hooks'
    interpreter can import the required packages); non-zero if a full bootstrap
    run is needed. Read-only — touches no files. Lets the skill skip bootstrap
    when ready without falsely passing a wired-but-broken install (e.g. the
    dedicated venv was wiped by a reinstall)."""
    report = readiness_report()
    if not report["python_version_ok"]:
        return 1
    try:
        scope, settings_path, _commands = detect_scope_and_targets()
        settings = load_settings(settings_path)
    except SystemExit:
        return 1
    hooks_section = settings.get("hooks") if isinstance(settings, dict) else None
    pre_tool_use = hooks_section.get("PreToolUse") if isinstance(hooks_section, dict) else None
    interpreter = _wired_hook_interpreter(pre_tool_use) if isinstance(pre_tool_use, list) else None
    # Wired AND the interpreter those hooks use can actually load the packages.
    # A missing/wiped venv (or a deps-less python3) means the hooks would
    # fail-open — so that must read as "not ready", triggering a real bootstrap.
    if interpreter is not None and interpreter_has_packages(interpreter):
        print(f"coding-standards: already set up ({scope}) — no bootstrap needed.")
        return 0
    return 1


# Env sentinel so a re-exec can't loop (set before exec, checked on entry).
_REEXEC_FLAG = "_CODING_STANDARDS_REEXEC"


def reexec_under_compatible_python() -> None:
    """If the running Python is below the floor but a compatible one exists on
    the machine, re-launch bootstrap under it — same argv/cwd/env, so scope
    detection sees identical inputs and everything downstream (venv build,
    readiness) runs on a Python that can install the required packages.

    No-op when already compatible, already re-exec'd once, or none is found
    (readiness then reports the block — bootstrap never installs an interpreter).
    """
    if sys.version_info[:2] >= MIN_PYTHON or os.environ.get(_REEXEC_FLAG):
        return
    better = find_compatible_python()
    if not better or os.path.realpath(better) == os.path.realpath(sys.executable):
        return
    print(
        f"  Python {sys.version_info[0]}.{sys.version_info[1]} is below the "
        f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} floor — re-running bootstrap under "
        f"{better}…"
    )
    os.environ[_REEXEC_FLAG] = "1"
    # Flush before execv — it replaces the process image immediately, so any
    # buffered stdout/stderr (the line above) would otherwise be lost.
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        os.execv(better, [better, *sys.argv])
    except OSError:
        pass  # fall through; readiness will report the block as usual


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # Recover from an old launcher Python by re-running under a compatible one
    # already on the machine (does not return if it re-execs).
    reexec_under_compatible_python()

    if args.verify:
        return verify_already_set_up()

    # ── Step 1: Readiness check ────────────────────────────────────────────
    report = readiness_report()
    print_readiness(report)
    if report["blocking_issues"]:
        print("\n  Blocking issues:")
        for issue in report["blocking_issues"]:
            print(f"    - {issue}")
        print("\n  Resolve the blocking issues above and re-run bootstrap.")
        return 1
    if args.check:
        return 0

    # ── Step 2: Detect scope (needed to choose the install strategy) ─────────
    scope, settings_path, commands_dir = detect_scope_and_targets()

    # ── Step 3: Install the required packages (may create a venv) ────────────
    # Global installs own a dedicated venv (stable, independent of whatever
    # python3 is first on PATH); project installs keep the portable `python3`
    # so the committed settings.json works across teammates' machines.
    if scope == "global":
        report, venv_python = ensure_global_venv(report, args)
    else:
        report, venv_python = ensure_required_packages(report, args)
    if not required_packages_available(report, venv_python):
        _block_on_missing_packages(report)
        return 1

    # ── Step 4: Wire hooks + slash command ──────────────────────────────────
    warn_project_interpreter_mismatch(scope, report, venv_python)
    hook_python = hook_interpreter(scope, report["python_command"], venv_python)
    entry = build_hook_entry(scope, hook_python)
    settings = load_settings(settings_path)
    updated, hooks_action = merge_hook_entry(settings, entry)
    perms_changed = ensure_skill_permissions(updated)
    if hooks_action != "noop" or perms_changed:
        write_settings(settings_path, updated)
    cmd_action = install_slash_command(commands_dir)
    ignore_action, ignore_path = seed_ignore_template(scope, settings_path)

    return report_install_result(WiringResult(
        scope=scope,
        settings_path=settings_path,
        commands_dir=commands_dir,
        hooks_action=hooks_action,
        cmd_action=cmd_action,
        perms_changed=perms_changed,
        hook_python=hook_python,
        venv_python=venv_python,
        ignore_action=ignore_action,
        ignore_path=ignore_path,
    ))


if __name__ == "__main__":
    sys.exit(main())
