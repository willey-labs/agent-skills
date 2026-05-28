#!/usr/bin/env python3
"""coding-standards skill — bootstrap.

Wires the PreToolUse enforcement hooks, the `/coding-standards` slash
command, and checks machine readiness on first invocation. Cross-platform
(Windows, Linux, macOS). Stdlib only for the bootstrap itself; tree-sitter
is an optional install for TS/JS AST checks.

What it does, in order:

1. **Readiness check** — Python version, Python command (`python`/`python3`),
   pip availability, virtualenv detection, platform, tree-sitter packages.
2. **Auto-install missing deps** — if invoked with `--auto-install` or
   the user confirms interactively, runs `python -m pip install` for
   tree-sitter packages (`--user` outside venvs).
3. **Wire hooks** into the correct `settings.json` (project vs global is
   auto-detected from the SKILL.md install path).
4. **Symlink the slash command** into `.claude/commands/`.

Idempotent: re-running upgrades hook entries to the current list, refreshes
the symlink, re-checks readiness. Safe to run repeatedly.

Detection logic:
- If this file lives under `~/.claude/skills/...`, the skill is installed
  GLOBALLY → target `~/.claude/settings.json` + `~/.claude/commands/`.
- Otherwise, walk up looking for a `.claude/` directory; its parent is the
  project root → target `<project>/.claude/settings.json` + commands.

Flags:
  --check          Only report readiness; do not install or wire anything.
  --auto-install   Install missing tree-sitter packages without prompting.
                   Use this when invoking from an agent (non-TTY).
  --skip-install   Skip the tree-sitter install offer entirely.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Use absolute() not resolve() — the skill is symlinked from a canonical
# install location into ~/.claude/skills/<name>/ or <project>/.claude/skills/<name>/.
# Following the symlink (resolve) would land on the canonical path, which
# has no `.claude` ancestor, breaking scope detection. We need the path
# as the agent sees it — through the symlink.
SCRIPT_PATH = Path(__file__).absolute()
SKILL_DIR = SCRIPT_PATH.parent
# Hooks dir must resolve to the real location so the command paths in
# settings.json work from any cwd.
HOOKS_DIR = (SKILL_DIR / "hooks").resolve()

# Identification of our hooks block — every command we add starts with this
# path prefix, so we can find (and replace) our previous entry on re-run
# without disturbing unrelated PreToolUse hooks the user has configured.
HOOK_FILES = [
    "block-junk-paths.py",
    "block-ts-violations.py",
    "block-py-violations.py",
    "block-go-violations.py",
    "block-csharp-violations.py",
    "block-php-violations.py",
    "block-jvm-violations.py",
]


# ─────────────────────────────────────────────────────────────────────────────
# Readiness check — runs on every invocation, reports the state of the host.
# Cross-platform: Windows, macOS, Linux.
# ─────────────────────────────────────────────────────────────────────────────

# Minimum Python version. The hooks use modern syntax (PEP 604 generics
# without `from __future__`, etc. — actually we DO use `__future__ annotations`,
# so 3.7+ would work, but tree-sitter wheels target 3.9+).
MIN_PYTHON = (3, 9)

# Optional tree-sitter packages for AST checks on TS/JS.
OPTIONAL_TREE_SITTER = [
    ("tree_sitter", "tree-sitter"),
    ("tree_sitter_typescript", "tree-sitter-typescript"),
    ("tree_sitter_javascript", "tree-sitter-javascript"),
]


def detect_python_command() -> str:
    """Find a `python` invocation that works across Linux / macOS / Windows.

    Returns the command to put in settings.json hook entries. Prefers
    `python3` (canonical on Linux/macOS), falls back to `python` (Windows),
    then to the absolute path of the currently-running interpreter as a
    last resort.
    """
    for candidate in ("python3", "python"):
        if shutil.which(candidate):
            return candidate
    # No `python`/`python3` on PATH — use the absolute path to this script's
    # interpreter. Works in venvs and on systems where Python is installed
    # in a non-standard location.
    return sys.executable


def detect_pip_command() -> str | None:
    """Return the canonical pip invocation (`<python> -m pip`).

    Using `<python> -m pip` instead of `pip` ensures we install into the
    same interpreter that's running the hooks. Returns None if pip isn't
    importable at all (rare — typical only on stripped-down distros).
    """
    py = sys.executable
    try:
        subprocess.run(
            [py, "-m", "pip", "--version"],
            check=True, capture_output=True, timeout=10,
        )
        return f"{py} -m pip"
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None


def in_virtualenv() -> bool:
    """Detect whether the current Python is inside a venv/virtualenv.

    True for venv, virtualenv, conda. False for system Python.
    Used to decide whether to add `--user` to pip install.
    """
    return (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )


def check_tree_sitter_packages() -> tuple[bool, list[str]]:
    """Detect which tree-sitter packages are installed.

    Returns (all_present, missing_package_names).
    """
    missing: list[str] = []
    for module, package in OPTIONAL_TREE_SITTER:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return len(missing) == 0, missing


def readiness_report() -> dict:
    """Return a structured readiness report.

    Keys:
      python_version_ok: bool
      python_version:    tuple[int, int, int]
      python_command:    str (the command to put in settings.json)
      pip_command:       str | None
      in_venv:           bool
      platform:          str ('linux' | 'darwin' | 'windows' | other)
      tree_sitter_ok:    bool
      missing_tree_sitter: list[str]
      blocking_issues:   list[str] (deal-breakers that prevent skill from working)
      install_actions:   list[str] (suggested pip-install package names)
    """
    py_version = sys.version_info[:3]
    py_ok = py_version >= MIN_PYTHON
    py_cmd = detect_python_command()
    pip_cmd = detect_pip_command()
    venv = in_virtualenv()
    plat = sys.platform  # 'linux', 'darwin', 'win32'
    ts_ok, ts_missing = check_tree_sitter_packages()

    blocking: list[str] = []
    if not py_ok:
        blocking.append(
            f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; found "
            f"{py_version[0]}.{py_version[1]}.{py_version[2]}"
        )

    return {
        "python_version_ok": py_ok,
        "python_version": py_version,
        "python_command": py_cmd,
        "pip_command": pip_cmd,
        "in_venv": venv,
        "platform": plat,
        "platform_pretty": platform.platform(),
        "tree_sitter_ok": ts_ok,
        "missing_tree_sitter": ts_missing,
        "blocking_issues": blocking,
        "install_actions": ts_missing,  # only tree-sitter is auto-installable
    }


def print_readiness(report: dict) -> None:
    """Print a human-readable readiness summary."""
    plat_map = {"linux": "Linux", "darwin": "macOS", "win32": "Windows"}
    plat = plat_map.get(report["platform"], report["platform"])
    py = ".".join(str(x) for x in report["python_version"])
    venv = " (venv)" if report["in_venv"] else ""

    print("coding-standards readiness check:")
    py_mark = "OK" if report["python_version_ok"] else "FAIL"
    print(f"  Python {py}{venv}                 [{py_mark}]")
    print(f"  Python command: {report['python_command']:<20} [used in settings.json]")
    pip_mark = "OK" if report["pip_command"] else "MISSING"
    pip_str = report["pip_command"] or "(not found)"
    print(f"  pip: {pip_str:<37} [{pip_mark}]")
    print(f"  Platform: {plat:<30} [{report['platform_pretty']}]")
    ts_mark = "OK" if report["tree_sitter_ok"] else "missing"
    if report["tree_sitter_ok"]:
        print(f"  tree-sitter (TS/JS AST): all present       [OK]")
    else:
        print(f"  tree-sitter (TS/JS AST): missing           [{ts_mark}]")
        for pkg in report["missing_tree_sitter"]:
            print(f"    - {pkg}")


def install_tree_sitter(report: dict) -> tuple[bool, str]:
    """Install missing tree-sitter packages via `python -m pip install`.

    Uses `--user` outside virtualenvs to avoid touching the system Python.
    Returns (success, message).
    """
    if not report["install_actions"]:
        return True, "nothing to install"
    if not report["pip_command"]:
        return False, (
            "pip is not available — cannot auto-install. "
            "Install pip first, then re-run bootstrap."
        )

    py = sys.executable
    cmd = [py, "-m", "pip", "install"]
    if not report["in_venv"]:
        cmd.append("--user")
    cmd.extend(report["install_actions"])

    print(f"  Running: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=300
        )
        return True, proc.stdout.strip().splitlines()[-1] if proc.stdout else "installed"
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()[-500:]
        return False, f"pip install failed:\n{stderr}"
    except subprocess.TimeoutExpired:
        return False, "pip install timed out after 300s"


def prompt_user_for_install(missing: list[str]) -> bool:
    """Ask the user interactively whether to install missing tree-sitter
    packages. Returns True if user agreed, False otherwise.

    If stdin is not a TTY (agent invocation), returns False — the agent
    should re-invoke bootstrap with `--auto-install` after asking the user
    via its own AskUserQuestion tool.
    """
    if not sys.stdin.isatty():
        return False
    pkg_list = ", ".join(missing)
    print(
        f"\n  Optional: install {pkg_list} for AST-level TS/JS checks?"
    )
    print(
        f"  This unlocks FN-001 function length, FN-005 precise arg count, "
        f"OD-004 hybrid class detection on .ts/.tsx/.js/.jsx files."
    )
    print(f"  Without it, TS/JS hooks fall back to regex (still works, less precise).")
    try:
        answer = input("  Install now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer in ("", "y", "yes")


def detect_scope_and_targets() -> tuple[str, Path, Path]:
    """Return (scope, settings_json_path, commands_dir_path).

    scope is "global" or "project".
    """
    home_claude = Path.home() / ".claude"
    try:
        # Use the unresolved path — the skill may be symlinked from the
        # canonical install location into ~/.claude/skills/<name>/ or
        # <project>/.claude/skills/<name>/. Both forms still place the
        # symlink itself under one of those `.claude/skills/` parents,
        # which is what we use for scope detection.
        if str(SCRIPT_PATH).startswith(str(home_claude) + os.sep):
            return "global", home_claude / "settings.json", home_claude / "commands"
    except Exception:
        pass

    # Walk up looking for `.claude/skills/<our-skill>/...` — the `.claude`
    # directory's parent is the project root.
    for parent in SCRIPT_PATH.parents:
        if parent.name == ".claude":
            return "project", parent / "settings.json", parent / "commands"

    # No `.claude` ancestor found. Refuse to guess — writing to an
    # unexpected location is worse than asking the user to install correctly.
    raise SystemExit(
        f"bootstrap: cannot determine install scope. This script must be invoked\n"
        f"through a `.claude/skills/coding-standards/bootstrap.py` symlink (project\n"
        f"or global). Got: {SCRIPT_PATH}\n"
        f"Install via `npx skills add willey-labs/agent-skills` and try again."
    )


def build_hook_entry(scope: str, python_command: str) -> dict:
    """Build the PreToolUse entry that activates every hook in hooks/.

    For project scope, use `${CLAUDE_PROJECT_DIR}/.claude/skills/...` so the
    entry survives moving the project (Claude Code expands the variable).
    For global scope, use the absolute resolved path — no variable points at
    the user's home skills dir reliably.

    `python_command` is detected at bootstrap time so the command works on
    Windows (`python`) and Linux/macOS (`python3`).
    """
    if scope == "project":
        path_prefix = "${CLAUDE_PROJECT_DIR}/.claude/skills/coding-standards/hooks"
    else:
        path_prefix = str(HOOKS_DIR)

    return {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
            {
                "type": "command",
                "command": f"{python_command} {path_prefix}/{name}",
            }
            for name in HOOK_FILES
        ],
    }


def is_our_entry(entry: dict) -> bool:
    """An existing PreToolUse entry is "ours" if every command references
    `coding-standards/hooks/`. We replace such entries on re-run; other
    entries are left untouched.
    """
    hooks = entry.get("hooks") or []
    if not hooks:
        return False
    for hook in hooks:
        cmd = (hook or {}).get("command", "")
        if "coding-standards/hooks/" not in cmd:
            return False
    return True


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise SystemExit(
            f"bootstrap: cannot parse {path} as JSON ({e}). "
            f"Aborting to avoid corrupting your settings — paste the hooks block manually."
        )
    if not isinstance(data, dict):
        raise SystemExit(
            f"bootstrap: {path} is not a JSON object. "
            f"Aborting to avoid corrupting your settings."
        )
    return data


def merge_hook_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Return (updated_settings, action). action ∈ {'noop', 'added', 'updated'}."""
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        hooks_section = {}
        settings["hooks"] = hooks_section

    pre_tool_use = hooks_section.get("PreToolUse")
    if not isinstance(pre_tool_use, list):
        pre_tool_use = []
        hooks_section["PreToolUse"] = pre_tool_use

    # Find any existing entry of ours.
    existing_indexes = [
        i for i, entry in enumerate(pre_tool_use) if isinstance(entry, dict) and is_our_entry(entry)
    ]

    if existing_indexes:
        # Replace the first match, drop any duplicates.
        first = existing_indexes[0]
        previous = pre_tool_use[first]
        pre_tool_use[first] = new_entry
        # Remove dupes (walk in reverse so indexes stay valid).
        for idx in reversed(existing_indexes[1:]):
            del pre_tool_use[idx]
        if previous == new_entry:
            return settings, "noop"
        return settings, "updated"

    pre_tool_use.append(new_entry)
    return settings, "added"


def write_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup = path.with_suffix(path.suffix + f".bak.{int(time.time())}")
        shutil.copy2(path, backup)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def install_slash_command(commands_dir: Path) -> str:
    """Symlink the slash command into the agent's commands/ directory.

    Returns the action taken: 'noop', 'created', or 'refreshed'.
    """
    source = (SKILL_DIR / "commands" / "coding-standards.md").resolve()
    if not source.exists():
        # No command file shipped (older skill version). Skip silently.
        return "noop"

    commands_dir.mkdir(parents=True, exist_ok=True)
    target = commands_dir / "coding-standards.md"

    if target.is_symlink():
        if target.resolve() == source:
            return "noop"
        target.unlink()
        target.symlink_to(source)
        return "refreshed"

    if target.exists():
        # Plain file lives there — don't clobber. The user may have
        # customized it; warn rather than overwrite.
        print(
            f"coding-standards: skipped /coding-standards command — {target} "
            f"exists and is not a symlink. Remove it manually if you want the "
            f"bootstrap-managed version."
        )
        return "noop"

    target.symlink_to(source)
    return "created"


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
        help="Install missing tree-sitter packages without prompting "
             "(use this when invoking from a non-TTY agent context).",
    )
    mode.add_argument(
        "--skip-install", action="store_true",
        help="Skip the tree-sitter install offer entirely.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    # ── Step 1: Readiness check ────────────────────────────────────────────
    report = readiness_report()
    print_readiness(report)

    # Blocking issues (Python too old, etc.) → abort.
    if report["blocking_issues"]:
        print("\n  Blocking issues:")
        for issue in report["blocking_issues"]:
            print(f"    - {issue}")
        print("\n  Resolve the blocking issues above and re-run bootstrap.")
        return 1

    # Check-only mode: stop here.
    if args.check:
        return 0

    # ── Step 2: Install missing tree-sitter (optional) ──────────────────────
    if report["missing_tree_sitter"] and not args.skip_install:
        if args.auto_install:
            should_install = True
        else:
            should_install = prompt_user_for_install(report["missing_tree_sitter"])

        if should_install:
            ok, msg = install_tree_sitter(report)
            if ok:
                print(f"  Install OK: {msg}\n")
                # Refresh report so the next sections see the new state.
                report = readiness_report()
            else:
                print(f"  Install failed: {msg}")
                print(
                    "  Hooks will still be wired — TS/JS will fall back to "
                    "regex checks. Install manually later with:\n"
                    f"    {sys.executable} -m pip install "
                    + " ".join(report["missing_tree_sitter"])
                )
        elif sys.stdin.isatty():
            print(
                "  Skipped tree-sitter install. Run with --auto-install to "
                "install later, or `pip install "
                + " ".join(report["missing_tree_sitter"])
                + "` manually."
            )
        else:
            # Non-TTY (agent) invocation without --auto-install. Print the
            # install hint and continue.
            print(
                f"  To install: {sys.executable} -m pip install "
                + " ".join(report["missing_tree_sitter"])
                + "\n  Or re-run bootstrap with --auto-install."
            )

    # ── Step 3: Wire hooks + slash command ──────────────────────────────────
    scope, settings_path, commands_dir = detect_scope_and_targets()

    entry = build_hook_entry(scope, report["python_command"])
    settings = load_settings(settings_path)
    updated, hooks_action = merge_hook_entry(settings, entry)
    if hooks_action != "noop":
        write_settings(settings_path, updated)

    cmd_action = install_slash_command(commands_dir)

    # ── Report ──────────────────────────────────────────────────────────────
    if hooks_action == "noop" and cmd_action == "noop":
        print(
            f"\ncoding-standards: already installed — {settings_path} ({scope}). "
            f"No changes."
        )
        return 0

    verb = {"added": "Wired", "updated": "Updated", "noop": "Unchanged"}[hooks_action]
    cmd_verb = {
        "created": "linked",
        "refreshed": "refreshed",
        "noop": "unchanged",
    }[cmd_action]
    print(
        f"\ncoding-standards: {verb} {len(HOOK_FILES)} PreToolUse hooks into "
        f"{settings_path} ({scope});\n"
        f"  /coding-standards command {cmd_verb} at "
        f"{commands_dir / 'coding-standards.md'}.\n"
        f"  Hook commands use: {report['python_command']} "
        f"(detected at bootstrap time).\n"
        f"  Hooks dir: {HOOKS_DIR}\n"
        f"  Restart your agent if hooks or commands don't activate on the next tool call."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
