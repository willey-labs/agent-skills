#!/usr/bin/env python3
"""Wire the skill into the agent's settings.json.

Owns the PreToolUse hook entry (build, recognize, merge), the settings.json
read/write with a rolling backup, the skill-permission grants, and the
interpreter-choice helpers. The list of hook scripts to wire (HOOK_FILES) lives
here too — it's the identity of "our" entry on re-run. The `/coding-standards`
slash-command install lives in the sibling `command.py` (ST-008: one job per file).
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from .paths import HOOKS_DIR, SKILL_DIR

# Identification of our hooks block — every command we add references one of
# these scripts by basename, so we can find (and replace) our previous entry on
# re-run without disturbing unrelated PreToolUse hooks the user has configured.
HOOK_FILES = [
    "block-junk-paths.py",
    "block-ts-violations.py",
    "block-py-violations.py",
    "block-go-violations.py",
    "block-csharp-violations.py",
    "block-php-violations.py",
    "block-jvm-violations.py",
    "block-god-file.py",
    "block-swallowed-errors.py",
    "block-debug-artifacts.py",
    "block-structure-file-violations.py",
]

# Basenames shipped by PAST versions and since retired/renamed. Listed ONLY so
# is_our_entry still recognises (and replaces) an older wired block on upgrade —
# never wired anew. warn-god-file.py was renamed to block-god-file.py when the
# god-file check gained a blocking path.
RETIRED_HOOK_FILES = [
    "warn-god-file.py",
]


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
    known = HOOK_FILES + RETIRED_HOOK_FILES  # recognise older wired blocks too
    for hook in hooks:
        cmd = (hook or {}).get("command", "")
        if not any(name in cmd for name in known):
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


def interpreter_note(scope: str, venv_python: Path | None) -> str:
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
    if scope != "project" or venv_python is not None or not report["packages_ok"]:
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
