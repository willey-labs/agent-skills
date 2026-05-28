#!/usr/bin/env python3
"""coding-standards skill — bootstrap.

Wires two things into the correct Claude Code install on first invocation
of the skill:

1. The PreToolUse enforcement hooks → `settings.json`.
2. The `/coding-standards` slash command → `.claude/commands/coding-standards.md`
   (as a symlink to the skill's `commands/coding-standards.md`).

Both are idempotent: re-running upgrades the hook entry to the current list,
refreshes the command symlink, and exits cleanly. Stdlib only.

Detection logic:
- If this file lives under `~/.claude/skills/...`, the skill is installed
  GLOBALLY → target `~/.claude/settings.json` + `~/.claude/commands/`.
- Otherwise, walk up from this file looking for a `.claude/` directory; that
  is the project root → target `<project>/.claude/settings.json` +
  `<project>/.claude/commands/`.

Designed to be invoked exactly once per scope via the SKILL.md Step 0
directive. The agent runs `python3 <skill-dir>/bootstrap.py`; this script
makes the deterministic decisions about scope and merging.
"""

from __future__ import annotations

import json
import os
import shutil
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


def build_hook_entry(scope: str) -> dict:
    """Build the PreToolUse entry that activates every hook in hooks/.

    For project scope, use `${CLAUDE_PROJECT_DIR}/.claude/skills/...` so the
    entry survives moving the project (Claude Code expands the variable).
    For global scope, use the absolute resolved path — no variable available
    that points at the user's home skills dir reliably.
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
                "command": f"python3 {path_prefix}/{name}",
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


def main() -> int:
    scope, settings_path, commands_dir = detect_scope_and_targets()

    # Hooks
    entry = build_hook_entry(scope)
    settings = load_settings(settings_path)
    updated, hooks_action = merge_hook_entry(settings, entry)
    if hooks_action != "noop":
        write_settings(settings_path, updated)

    # Slash command
    cmd_action = install_slash_command(commands_dir)

    # Report
    if hooks_action == "noop" and cmd_action == "noop":
        print(
            f"coding-standards: already installed — {settings_path} ({scope}). "
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
        f"coding-standards: {verb} {len(HOOK_FILES)} PreToolUse hooks into "
        f"{settings_path} ({scope}); /coding-standards command {cmd_verb} "
        f"at {commands_dir / 'coding-standards.md'}.\n"
        f"  Hooks dir: {HOOKS_DIR}\n"
        f"  Restart your agent if hooks or commands don't activate on the next tool call."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
