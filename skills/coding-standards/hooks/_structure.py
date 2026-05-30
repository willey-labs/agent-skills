"""Read the project's `.coding-standards-structure` to decide which
structure-dependent checks the hooks enforce.

Only a CUSTOM layout writes this file (a project on a catalog standard has no
file — its structure is recognised from its folders, per SKILL.md Step 1.4).
The file may carry a `hooks:` block that toggles the structure-dependent
checks the hooks would otherwise hard-block:

    variant: current
    hooks:
      deep-import: off       # ST-003 — off when the project uses no barrels
      junk-drawer: off       # ST-005 — off when the project already uses utils.ts
      tests-colocated: on

Rules:
- No file, or the file does not mention a given check → the check is ENABLED
  (the hook's normal behaviour). Absence NEVER silently disables a check.
- Only an explicit `<check>: off` (or false/no/disabled) turns a check off.

This is the deterministic half of the structure feature: the choice recorded
in the file actually changes what the hooks block at write time, instead of
relying on the model to remember.

Stdlib only.
"""

from __future__ import annotations

import re
from pathlib import Path

# Reuse the same project-root walk the exclusion logic uses, so the structure
# file is found at the same root as `.coding-standards-ignore`.
from _exclusions import find_project_root

STRUCTURE_FILENAME = ".coding-standards-structure"

# Toggle lines anywhere in the file, e.g. `  deep-import: off`. We don't need a
# full YAML parser (the hooks ship stdlib-only) — a flat line scan for the known
# keys is robust because the keys are unique.
_TOGGLE_LINE = re.compile(
    r"^\s*(deep-import|junk-drawer|tests-colocated|god-file)\s*:\s*"
    r"(on|off|true|false|yes|no|enable|enabled|disable|disabled)\s*$",
    re.IGNORECASE,
)

# ST-008 numeric overrides, e.g. `  god-file-max-lines: 600`.
_GOD_FILE_NUM_LINE = re.compile(
    r"^\s*(god-file-max-lines|god-file-max-decls)\s*:\s*(\d+)\s*$",
    re.IGNORECASE,
)

GOD_FILE_DEFAULT_MAX_LINES = 400
GOD_FILE_DEFAULT_MAX_DECLS = 10
_TRUE_WORDS = {"on", "true", "yes", "enable", "enabled"}
_FALSE_WORDS = {"off", "false", "no", "disable", "disabled"}

# Cache per project root so repeated checks in one hook run don't re-read disk.
_TOGGLE_CACHE: dict[str, dict[str, bool]] = {}


def _parse_toggles(text: str) -> dict[str, bool]:
    toggles: dict[str, bool] = {}
    for line in text.splitlines():
        match = _TOGGLE_LINE.match(line)
        if not match:
            continue
        key = match.group(1).lower()
        word = match.group(2).lower()
        if word in _TRUE_WORDS:
            toggles[key] = True
        elif word in _FALSE_WORDS:
            toggles[key] = False
    return toggles


def load_structure_toggles(file_path: str) -> dict[str, bool]:
    """Return the structure-check toggles for the project owning `file_path`.

    Empty dict when there is no `.coding-standards-structure` (a catalog-standard
    project, or none configured).
    """
    root = find_project_root(Path(file_path))
    if root is None:
        return {}
    cache_key = str(root)
    if cache_key in _TOGGLE_CACHE:
        return _TOGGLE_CACHE[cache_key]
    structure_file = root / STRUCTURE_FILENAME
    toggles: dict[str, bool] = {}
    if structure_file.exists():
        try:
            toggles = _parse_toggles(structure_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            toggles = {}
    _TOGGLE_CACHE[cache_key] = toggles
    return toggles


def is_check_enabled(check_name: str, file_path: str) -> bool:
    """Whether a structure-dependent check should run for this file's project.

    Defaults to True (enforce) when the project has no `.coding-standards-structure`
    or the file does not mention this check — so absence never silently disables a
    check; only an explicit `<check>: off` does.
    """
    return load_structure_toggles(file_path).get(check_name, True)


def load_god_file_config(file_path: str) -> dict[str, object]:
    """ST-008 soft-warning config for the project owning `file_path`.

    Returns {"enabled": bool, "max_lines": int, "max_decls": int}. Defaults:
    enabled True (warn), 400 lines, 10 top-level declarations. Only an explicit
    `god-file: off` disables; numeric keys override the thresholds.
    """
    enabled = is_check_enabled("god-file", file_path)
    max_lines = GOD_FILE_DEFAULT_MAX_LINES
    max_decls = GOD_FILE_DEFAULT_MAX_DECLS
    root = find_project_root(Path(file_path))
    if root is not None:
        structure_file = root / STRUCTURE_FILENAME
        if structure_file.exists():
            try:
                for line in structure_file.read_text(encoding="utf-8").splitlines():
                    m = _GOD_FILE_NUM_LINE.match(line)
                    if not m:
                        continue
                    key, value = m.group(1).lower(), int(m.group(2))
                    if key == "god-file-max-lines":
                        max_lines = value
                    elif key == "god-file-max-decls":
                        max_decls = value
            except (OSError, UnicodeDecodeError, ValueError):
                pass
    return {"enabled": enabled, "max_lines": max_lines, "max_decls": max_decls}
