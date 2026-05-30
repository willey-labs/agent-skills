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
5. **Seed a `.coding-standards-ignore` template** at the project root (if
   absent) so the opt-out feature is discoverable instead of invisible.

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
from dataclasses import dataclass
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

# When the system Python is externally-managed (PEP 668) and a plain pip install
# is refused, --auto-install creates a dedicated venv HERE — beside the hooks,
# deliberately NOT under any cache dir a cleaner might purge — and pins the hook
# commands to its interpreter. Co-located with the skill: if the skill is
# reinstalled, re-running bootstrap recreates it.
MANAGED_VENV_DIR = HOOKS_DIR.parent / ".venv"

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

# Seeded at the project root on first bootstrap so users DISCOVER the feature —
# an absent file is invisible; people assume the skill can't be told to skip
# anything. Never overwrites an existing file. Patterns here add to the built-in
# defaults in hooks/_exclusions.py (they don't replace them).
IGNORE_FILENAME = ".coding-standards-ignore"
IGNORE_TEMPLATE = """\
# .coding-standards-ignore
#
# Files matched here are skipped by the coding-standards skill — both the
# write-time hooks and review mode. Gitignore-style patterns, one per line.
#
# You usually don't need this file. The skill already excludes node_modules,
# vendored deps, generated code, migrations, build output, and lock files by
# default (see hooks/_exclusions.py -> DEFAULT_EXCLUSIONS). Add a pattern below
# ONLY to skip something project-specific.
#
# Examples — uncomment and edit:
# src/legacy/**          # pre-existing code you're not ready to clean up
# scripts/one-off-*.ts   # throwaway scripts
# **/*.config.js         # config files you don't want flagged
"""

# Project-root markers — mirror hooks/_exclusions.py:find_project_root so the
# template lands at the same root the hooks resolve. Kept local (bootstrap is
# standalone and must not import from hooks/).
PROJECT_ROOT_MARKERS = {
    ".git", "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "composer.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "requirements.txt", "setup.py", "setup.cfg",
}
PROJECT_ROOT_GLOB_MARKERS = ("*.csproj", "*.sln", "*.fsproj")


# ─────────────────────────────────────────────────────────────────────────────
# Readiness check — runs on every invocation, reports the state of the host.
# Cross-platform: Windows, macOS, Linux.
# ─────────────────────────────────────────────────────────────────────────────

# Minimum Python for the stdlib hooks. They use `from __future__ import
# annotations`, so 3.9 is a comfortable supported floor (3.7+ would parse).
MIN_PYTHON = (3, 9)

# Minimum Python for the OPTIONAL tree-sitter AST checks (TS/JS). As of 2025+
# the current `tree-sitter` (>=0.24) and `tree-sitter-javascript` (>=0.24)
# wheels require Python >=3.10 — they dropped the cp39 wheel (only
# `tree-sitter-typescript` still ships one). On 3.9 a plain `pip install`
# resolves to stale grammar versions or fails outright, so we gate the AST
# install at 3.10 and let the stdlib hooks run on 3.9 regardless.
MIN_PYTHON_TREE_SITTER = (3, 10)

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
    """Detect whether the current Python is inside an isolated environment.

    True for venv/virtualenv (base_prefix != prefix, or the legacy real_prefix)
    AND for conda/mamba. Conda does NOT reliably set base_prefix != prefix, so
    it's detected via the CONDA_PREFIX / CONDA_DEFAULT_ENV env markers. False
    for bare system Python. Used to decide whether to add `--user` to pip
    install — inside ANY of these, `--user` errors or installs to the wrong
    place, so it must be omitted.
    """
    if hasattr(sys, "real_prefix"):
        return True
    if hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix:
        return True
    # conda/mamba often don't set base_prefix != prefix; fall back to env vars.
    if os.environ.get("CONDA_PREFIX") or os.environ.get("CONDA_DEFAULT_ENV"):
        return True
    return False


def check_tree_sitter_packages() -> tuple[bool, list[str]]:
    """Detect whether the tree-sitter grammars are available to the hooks.

    Returns (all_present, missing_package_names). Checks the interpreter running
    bootstrap first, then the managed venv — the interpreter the hooks actually
    use when one exists (see `hook_interpreter`). Probing only the system Python
    made an externally-managed host (PEP 668) report 'missing' on every run even
    after a prior run had installed the grammars into the venv, so each re-run
    pointlessly reinstalled and nagged for a session restart.
    """
    missing: list[str] = []
    for module, package in OPTIONAL_TREE_SITTER:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    if not missing:
        return True, []
    if managed_venv_has_tree_sitter():
        return True, []
    return False, missing


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
    # Scope decides which interpreter lands in settings.json: project keeps the
    # portable PATH name, global pins this absolute interpreter. State both —
    # claiming a single "used in settings.json" value here was misleading.
    print(
        f"  Hook interpreter: project scope -> {report['python_command']}, "
        f"global scope -> {sys.executable}"
    )
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


@dataclass
class InstallOutcome:
    """Result of attempting to install the optional tree-sitter packages."""
    ok: bool
    message: str
    externally_managed: bool = False


def install_tree_sitter(report: dict) -> InstallOutcome:
    """Install missing tree-sitter packages via `python -m pip install`.

    Uses `--user` outside virtualenvs to avoid touching the system Python. On a
    PEP 668 externally-managed refusal, returns `externally_managed=True` so the
    caller can fall back to a dedicated venv instead of giving up.
    """
    if not report["install_actions"]:
        return InstallOutcome(ok=True, message="nothing to install")
    if not report["pip_command"]:
        return InstallOutcome(
            ok=False,
            message="pip is unavailable — install pip first, then re-run bootstrap.",
        )

    cmd = [sys.executable, "-m", "pip", "install"]
    if not report["in_venv"]:
        cmd.append("--user")
    cmd.extend(report["install_actions"])

    print(f"  Running: {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=300
        )
        last_line = proc.stdout.strip().splitlines()[-1] if proc.stdout else "installed"
        return InstallOutcome(ok=True, message=last_line)
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        if "externally-managed" in stderr.lower() or "externally managed" in stderr.lower():
            return InstallOutcome(
                ok=False,
                message="pip refused to install into an externally-managed Python (PEP 668).",
                externally_managed=True,
            )
        return InstallOutcome(ok=False, message=f"pip install failed:\n{stderr[-500:]}")
    except subprocess.TimeoutExpired:
        return InstallOutcome(ok=False, message="pip install timed out after 300s")


def managed_venv_python() -> Path:
    """Absolute path to the managed venv's interpreter (cross-platform)."""
    if os.name == "nt":
        return MANAGED_VENV_DIR / "Scripts" / "python.exe"
    return MANAGED_VENV_DIR / "bin" / "python"


def managed_venv_has_tree_sitter() -> bool:
    """True if the dedicated venv exists and can import every tree-sitter grammar.

    This is the interpreter the hooks run under when the venv exists, so it — not
    the (often externally-managed) interpreter running bootstrap — is the one
    whose imports decide whether tree-sitter is really available. Cheap when no
    venv is present: the `.exists()` short-circuit avoids spawning a subprocess.
    """
    venv_python = managed_venv_python()
    if not venv_python.exists():
        return False
    import_line = "import " + ", ".join(module for module, _package in OPTIONAL_TREE_SITTER)
    try:
        subprocess.run(
            [str(venv_python), "-c", import_line],
            check=True, capture_output=True, text=True, timeout=30,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def create_managed_venv() -> tuple[Path | None, str]:
    """Create a dedicated venv beside the hooks and install tree-sitter into it.

    The escape hatch when the running interpreter is externally-managed (PEP
    668): it lets `--auto-install` finish in a single run instead of asking the
    user to build a venv and re-bootstrap. Returns (venv_python, message);
    venv_python is None on failure (callers then keep the regex fallback).
    """
    venv_python = managed_venv_python()
    packages = [package for _module, package in OPTIONAL_TREE_SITTER]
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(MANAGED_VENV_DIR)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", *packages],
            check=True, capture_output=True, text=True, timeout=300,
        )
        return venv_python, f"venv at {MANAGED_VENV_DIR} (tree-sitter installed)"
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "").strip()[-500:]
        return None, f"venv setup failed:\n{detail}"
    except subprocess.TimeoutExpired:
        return None, "venv setup timed out after 300s"


def _print_tree_sitter_python_floor(report: dict) -> None:
    """Explain why the AST install is skipped on Python below the floor."""
    ver = ".".join(str(x) for x in report["python_version"])
    floor = f"{MIN_PYTHON_TREE_SITTER[0]}.{MIN_PYTHON_TREE_SITTER[1]}"
    print(
        f"  tree-sitter AST checks need Python {floor}+ (current wheels dropped "
        f"3.9); you're on {ver}. Skipping the AST install — TS/JS hooks use the "
        f"regex fallback. All stdlib hooks (Python AST, path/junk, Go/C#/PHP/JVM) "
        f"work normally."
    )


def _print_install_skipped(report: dict) -> None:
    """Print the post-skip hint, tailored to interactive vs agent context."""
    packages = " ".join(report["missing_tree_sitter"])
    if sys.stdin.isatty():
        print(
            f"  Skipped tree-sitter install. Re-run with --auto-install, or "
            f"`pip install {packages}` manually."
        )
    else:
        print(
            f"  To install: {sys.executable} -m pip install {packages}\n"
            f"  Or re-run bootstrap with --auto-install."
        )


def _install_into_managed_venv() -> Path | None:
    """Create the dedicated venv and report it. Returns its interpreter path, or
    None if creation failed (hooks then keep the regex fallback)."""
    print(
        "  System Python is externally-managed (PEP 668). Creating a dedicated "
        "venv so the AST checks install in this one run…"
    )
    venv_python, message = create_managed_venv()
    if venv_python is not None:
        print(f"  Install OK: {message}\n  Hooks will use this venv's Python.\n")
    else:
        print(f"  {message}")
        print("  Hooks wired anyway — TS/JS uses the regex fallback.")
    return venv_python


def _run_tree_sitter_install(report: dict) -> tuple[dict, Path | None]:
    """Run the install; fall back to a managed venv on PEP 668. Returns the
    (possibly refreshed) report and the venv interpreter path (None if unused)."""
    outcome = install_tree_sitter(report)
    if outcome.ok:
        print(f"  Install OK: {outcome.message}\n")
        return readiness_report(), None
    if outcome.externally_managed:
        return report, _install_into_managed_venv()
    print(f"  Install failed: {outcome.message}")
    print(
        "  Hooks will still be wired — TS/JS will fall back to regex checks.\n"
        f"  Install manually later with: {sys.executable} -m pip install "
        + " ".join(report["missing_tree_sitter"])
    )
    return report, None


def ensure_tree_sitter(report: dict, args: argparse.Namespace) -> tuple[dict, Path | None]:
    """Install the optional tree-sitter AST grammars when they're missing.

    The single entry point for Step 2: honours --skip-install, the Python floor,
    and the interactive prompt, then installs — falling back to a managed venv
    when the system Python is externally-managed so the agent never has to
    re-run. Returns the (possibly refreshed) report and a managed-venv
    interpreter path (None when no venv was created).
    """
    # A previous run already built the managed venv with the grammars: reuse it
    # so the hooks stay pointed at the only interpreter that has them, but don't
    # reinstall or print the restart nag. Without this, a re-run that skipped the
    # install would rewire the hooks to a system Python that lacks tree-sitter.
    if managed_venv_has_tree_sitter():
        return report, managed_venv_python()
    if not report["missing_tree_sitter"] or args.skip_install:
        return report, None
    if report["python_version"] < MIN_PYTHON_TREE_SITTER:
        _print_tree_sitter_python_floor(report)
        return report, None
    should_install = args.auto_install or prompt_user_for_install(report["missing_tree_sitter"])
    if not should_install:
        _print_install_skipped(report)
        return report, None
    return _run_tree_sitter_install(report)


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


def _find_project_root_from(start: Path) -> Path | None:
    """Walk up from `start` to the first directory holding a project-root marker.

    Used only for GLOBAL-scope installs, where there is no project tied to the
    skill location — so we fall back to the cwd the agent ran bootstrap from.
    Returns None if no marker is found within 20 levels.
    """
    current = start if start.is_dir() else start.parent
    for _ in range(20):
        if any((current / marker).exists() for marker in PROJECT_ROOT_MARKERS):
            return current
        if any(next(current.glob(pattern), None) is not None for pattern in PROJECT_ROOT_GLOB_MARKERS):
            return current
        if current.parent == current:
            return None
        current = current.parent
    return None


def seed_ignore_template(scope: str, settings_path: Path) -> tuple[str, Path | None]:
    """Drop a commented `.coding-standards-ignore` template at the project root.

    Discovery, not enforcement: an absent file is invisible, so users assume the
    skill can't be told to skip anything. Project scope roots at the `.claude`
    parent; global scope falls back to the cwd's project root. Never overwrites
    an existing file. Returns (action, path) with action in
    {'created', 'exists', 'no-project'}.
    """
    if scope == "project":
        project_root: Path | None = settings_path.parent.parent
    else:
        project_root = _find_project_root_from(Path.cwd())
    if project_root is None:
        return "no-project", None
    target = project_root / IGNORE_FILENAME
    if target.exists():
        return "exists", target
    try:
        target.write_text(IGNORE_TEMPLATE, encoding="utf-8")
    except OSError:
        return "no-project", None
    return "created", target


def hook_interpreter(scope: str, python_command: str, venv_python: Path | None) -> str:
    """The interpreter string written into each hook command.

    A managed venv (created when the system Python is externally-managed) wins
    for both scopes — it's the only interpreter with the tree-sitter grammars.
    Otherwise project scope keeps the portable PATH name (`python3`) so the
    committed settings.json works on any teammate's machine; global scope pins
    the running interpreter's absolute path so the hooks can import the grammars
    pip installed into it (avoids the PATH-`python3`-vs-`sys.executable` mismatch
    that silently drops AST checks to regex).
    """
    if venv_python is not None:
        return str(venv_python)
    return python_command if scope == "project" else sys.executable


def build_hook_entry(scope: str, hook_python: str) -> dict:
    """Build the PreToolUse entry that activates every hook in hooks/.

    Project scope uses `${CLAUDE_PROJECT_DIR}/...` so the entry survives moving
    the project (Claude Code expands the variable); global scope uses the
    absolute resolved hooks dir. The interpreter is resolved by
    `hook_interpreter()` and passed in as `hook_python`. The matcher includes
    `MultiEdit` for backward compatibility with older Claude Code versions that
    still expose it; on current versions it harmlessly never matches.
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
                "command": f"{hook_python} {path_prefix}/{name}",
            }
            for name in HOOK_FILES
        ],
    }


def is_our_entry(entry: dict) -> bool:
    """An existing PreToolUse entry is "ours" if every command references one of
    our hook scripts by filename (e.g. `.../block-junk-paths.py`).

    We match on the HOOK_FILES basenames rather than a fixed
    `coding-standards/hooks/` substring, because the GLOBAL-scope command path
    is the RESOLVED canonical install dir — which (when the skill is symlinked
    from e.g. an npm cache) may not contain the string `coding-standards`. The
    old substring check failed to recognize global entries bootstrap had just
    written, so re-runs appended a duplicate hook block on every invocation.
    We replace recognized entries on re-run; unrelated entries are untouched.
    """
    hooks = entry.get("hooks") or []
    if not hooks:
        return False
    for hook in hooks:
        cmd = (hook or {}).get("command", "")
        if not any(name in cmd for name in HOOK_FILES):
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
        # Single rolling backup — overwrite, rather than accumulating one
        # timestamped .bak per run (which grew unbounded across re-installs).
        backup = path.with_suffix(path.suffix + ".bak")
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


def ensure_skill_permissions(settings: dict) -> bool:
    """Pre-approve reading the skill's own files and running its scripts.

    Without this, the agent hits a Claude Code permission prompt for every
    reference file it loads (the skill dir is outside the user's project on a
    global install) and for each `bootstrap.py` / `hooks/review-files.py` run.
    We add the skill directory to `permissions.additionalDirectories` (file
    access beyond the project root) plus narrow Bash allow-rules for the skill's
    Python scripts. Idempotent; preserves existing permission entries. Returns
    True if anything changed.
    """
    perms = settings.get("permissions")
    if not isinstance(perms, dict):
        perms = {}
        settings["permissions"] = perms
    changed = False

    # Read access to the skill's files. Grant both the path the agent reads
    # through (the symlink) and its resolved target, in case Claude Code
    # resolves symlinks before the access check.
    dirs = perms.get("additionalDirectories")
    if not isinstance(dirs, list):
        dirs = []
        perms["additionalDirectories"] = dirs
    for candidate in (str(SKILL_DIR), str(SKILL_DIR.resolve())):
        if candidate not in dirs:
            dirs.append(candidate)
            changed = True

    # Run the skill's own scripts without a Bash prompt (cover python3 + python).
    allow = perms.get("allow")
    if not isinstance(allow, list):
        allow = []
        perms["allow"] = allow
    for py in ("python3", "python"):
        for script in ("bootstrap.py", "hooks/review-files.py"):
            rule = f"Bash({py} {SKILL_DIR}/{script}*)"
            if rule not in allow:
                allow.append(rule)
                changed = True

    return changed


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


def _interpreter_note(scope: str, venv_python: Path | None) -> str:
    """One line explaining why the hook commands use this interpreter."""
    if venv_python is not None:
        return "dedicated venv — pinned to this machine; re-run bootstrap per machine"
    if scope == "project":
        return "PATH name — portable across teammates"
    return "absolute path — pinned to this machine"


def warn_project_interpreter_mismatch(
    scope: str, report: dict, venv_python: Path | None
) -> None:
    """Warn when project-scope hooks may run under an interpreter lacking tree-sitter.

    Project hook commands use the portable PATH name; if that resolves to a
    different interpreter than the one tree-sitter was installed into, TS/JS AST
    checks silently fall back to regex. A managed venv (venv_python) sidesteps
    this, and global scope pins sys.executable — so neither needs the warning.
    """
    if scope != "project" or venv_python is not None or not report["tree_sitter_ok"]:
        return
    resolved = shutil.which(report["python_command"])
    try:
        same = resolved is not None and os.path.realpath(resolved) == os.path.realpath(sys.executable)
    except OSError:
        same = True
    if same:
        return
    print(
        f"  Note: project hook commands use '{report['python_command']}' "
        f"(resolves to {resolved or '(not found)'}), but tree-sitter is installed "
        f"in {sys.executable}. If these differ, TS/JS AST checks fall back to "
        f"regex — install tree-sitter into the PATH interpreter or run bootstrap "
        f"with it."
    )


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
        f"    ({_interpreter_note(result.scope, result.venv_python)}).\n"
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


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

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

    # ── Step 2: Install missing tree-sitter (optional; may create a venv) ────
    report, venv_python = ensure_tree_sitter(report, args)

    # ── Step 3: Wire hooks + slash command ──────────────────────────────────
    scope, settings_path, commands_dir = detect_scope_and_targets()
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
