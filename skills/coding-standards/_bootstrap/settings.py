#!/usr/bin/env python3
"""Wire the skill into the agent's settings.json.

Owns the PreToolUse + SessionStart hook entries (build, recognize, merge), the
settings.json read/write with a rolling backup, and the skill-permission grants.
The list of hook scripts to wire (HOOK_FILES) lives here too — it's the identity
of "our" entry on re-run. Interpreter-choice helpers live in the sibling
`interpreter.py`; the `/coding-standards` slash-command install in `command.py`
(ST-008: one job per file).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .paths import HOOKS_DIR

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

# SessionStart health-check script (ISS-006). Wired under a stable `python3`, NOT
# the venv it polices, so a wiped venv can't take the check down with it. `startup`
# is the verified matcher value for a new session — the case where silently-dead
# enforcement does the most damage (a whole session of unchecked writes).
SESSION_HEALTH_SCRIPT = "session-health-check.py"
SESSION_START_MATCHER = "startup"
SESSION_START_INTERPRETER = "python3"


def build_hook_entry(scope: str, hook_python: str) -> dict:
    """Build the PreToolUse entry that activates every hook in hooks/.

    Project scope uses `${CLAUDE_PROJECT_DIR}/...` so the entry survives moving
    the project (Claude Code expands the variable); global scope uses the
    absolute resolved hooks dir. The interpreter is resolved by
    `interpreter.hook_interpreter()` and passed in as `hook_python`. The matcher
    includes `MultiEdit` for backward compatibility with older Claude Code
    versions that still expose it; on current versions it harmlessly never matches.
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


def build_session_start_entry(scope: str) -> dict:
    """Build the SessionStart entry that runs the enforcement health check.

    Uses the SAME path prefix as the PreToolUse hooks so scope detection inside
    the spawned `bootstrap.py --verify` works: project scope keeps the
    `${CLAUDE_PROJECT_DIR}/...` (`.claude`-bearing) path; global uses the resolved
    hooks dir (the scope.py global symlink-back fallback recovers it). The
    interpreter is a stable `python3`, never the venv (a wiped venv must not also
    kill the check). See SessionStart hook docs: stdout → Claude context, exit 2
    → stderr to user, never blocks.
    """
    if scope == "project":
        path_prefix = "${CLAUDE_PROJECT_DIR}/.claude/skills/coding-standards/hooks"
    else:
        path_prefix = str(HOOKS_DIR)
    return {
        "matcher": SESSION_START_MATCHER,
        "hooks": [
            {
                "type": "command",
                "command": f"{SESSION_START_INTERPRETER} {path_prefix}/{SESSION_HEALTH_SCRIPT}",
            }
        ],
    }


def is_our_session_entry(entry: dict) -> bool:
    """A SessionStart entry is ours if every command runs our health-check script."""
    hooks = entry.get("hooks") or []
    if not hooks:
        return False
    return all(SESSION_HEALTH_SCRIPT in (hook or {}).get("command", "") for hook in hooks)


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


def _merge_entry(settings: dict, section: str, new_entry: dict, is_ours) -> str:
    """Merge `new_entry` into `hooks.<section>` in place (creating `hooks` and the
    section if absent). Replaces our existing entry — dropping any duplicates —
    or appends; unrelated entries are untouched. Returns 'noop'|'added'|'updated'.
    Shared by PreToolUse and SessionStart so the two stay identical (DP-007)."""
    hooks_section = settings.get("hooks")
    if not isinstance(hooks_section, dict):
        hooks_section = {}
        settings["hooks"] = hooks_section
    entries = hooks_section.get(section)
    if not isinstance(entries, list):
        entries = []
        hooks_section[section] = entries

    existing_indexes = [
        i for i, entry in enumerate(entries) if isinstance(entry, dict) and is_ours(entry)
    ]
    if existing_indexes:
        first = existing_indexes[0]
        previous = entries[first]
        entries[first] = new_entry
        for idx in reversed(existing_indexes[1:]):  # reverse keeps indexes valid
            del entries[idx]
        return "noop" if previous == new_entry else "updated"
    entries.append(new_entry)
    return "added"


def merge_hook_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our PreToolUse entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "PreToolUse", new_entry, is_our_entry)


def merge_session_start_entry(settings: dict, new_entry: dict) -> tuple[dict, str]:
    """Merge our SessionStart entry. Returns (settings, 'noop'|'added'|'updated')."""
    return settings, _merge_entry(settings, "SessionStart", new_entry, is_our_session_entry)


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
