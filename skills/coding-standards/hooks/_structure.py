"""Read the project's `.coding-standards-structure` to decide which
structure-dependent checks the hooks enforce.

The file lives at the **framework project root** — the nearest ancestor of the
edited file holding a project marker (`package.json`, `go.mod`, `pyproject.toml`,
`.git`, `*.csproj`, ...), located by `find_project_root` below. In a single
project that's the repo root; in a monorepo it is the individual sub-project
(`apps/web/`, `services/api/`), so a Next.js app and a Hono service in one repo
resolve to their own separate files.

A CUSTOM layout writes this file with its learned layout and an optional
`hooks:` block. A custom project that instead *adopts* a standard writes the
same file carrying a `follows: <standard>` line. A project whose folders already
match a standard has no file at all — its structure is recognised from its
folders (per SKILL.md Step 1.4).

This module reads only the `hooks:` toggles below; it ignores `follows:` and any
layout body. A `follows:`-only file therefore yields no toggles, so every check
stays ENABLED.

Only TWO checks are toggleable, and only because each has a structural
precondition a layout can genuinely lack:

    variant: current
    hooks:
      deep-import: off       # ST-003 — off ONLY when the layout has no barrels by design
      #   god-file: off            # ST-008 — silence the (advisory, never-blocking) size warning
      #   god-file-max-lines: 600  # raise the advisory line threshold (default 400)
      #   god-file-max-decls: 15   # raise the top-level-declaration threshold (default 10)

Everything else is MANDATORY and has no off switch. `junk-drawer` (ST-005:
`utils.ts` / `helpers.py`), no-`any`, naming and arg-count are universal — they
are not toggle keys at all. `tests-colocated` (ST-007) is likewise not a toggle
(no hook reads it at write time). The parser recognises only `deep-import` and
`god-file`; any other `<key>: off` line is unrecognised and ignored — there is
no way to switch ST-005 off.

Rules:
- No file, or the file does not mention a given check → the check is ENABLED
  (the hook's normal behaviour). Absence NEVER silently disables a check.
- Only an explicit `<check>: off` (or false/no/disabled) on a recognised key
  (`deep-import`, `god-file`) turns that check off.

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
# keys is robust because the keys are unique. Only the two checks with a genuine
# structural precondition are recognised: `deep-import` (ST-003, off when a layout
# has no barrels) and `god-file` (ST-008, an advisory). `junk-drawer` (ST-005) and
# `tests-colocated` (ST-007) are intentionally NOT here — ST-005 is mandatory in
# every layout, and no hook reads ST-007 at write time.
_TOGGLE_LINE = re.compile(
    r"^\s*(deep-import|god-file)\s*:\s*"
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
_NUM_CACHE: dict[str, dict[str, int]] = {}


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


def _parse_numeric_overrides(text: str) -> dict[str, int]:
    nums: dict[str, int] = {}
    for line in text.splitlines():
        m = _GOD_FILE_NUM_LINE.match(line)
        if not m:
            continue
        nums[m.group(1).lower()] = int(m.group(2))
    return nums


def load_structure_toggles(file_path: str) -> dict[str, bool]:
    """Return the structure-check toggles for the project owning `file_path`.

    Empty dict when there is no `.coding-standards-structure` (a catalog-standard
    project, or none configured).

    Side-effect: also populates `_NUM_CACHE` for the same root so numeric
    overrides (e.g. god-file thresholds) are parsed in the same single read.
    """
    root = find_project_root(Path(file_path))
    if root is None:
        return {}
    cache_key = str(root)
    if cache_key in _TOGGLE_CACHE:
        return _TOGGLE_CACHE[cache_key]
    structure_file = root / STRUCTURE_FILENAME
    toggles: dict[str, bool] = {}
    nums: dict[str, int] = {}
    if structure_file.exists():
        try:
            text = structure_file.read_text(encoding="utf-8")
            toggles = _parse_toggles(text)
            nums = _parse_numeric_overrides(text)
        except (OSError, UnicodeDecodeError):
            toggles = {}
            nums = {}
    _TOGGLE_CACHE[cache_key] = toggles
    _NUM_CACHE[cache_key] = nums
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

    Calls `load_structure_toggles` which populates both `_TOGGLE_CACHE` and
    `_NUM_CACHE` in a single disk read; subsequent calls are cache-only.
    """
    enabled = is_check_enabled("god-file", file_path)
    root = find_project_root(Path(file_path))
    cache_key = str(root) if root is not None else None
    nums = _NUM_CACHE.get(cache_key, {}) if cache_key is not None else {}
    max_lines = nums.get("god-file-max-lines", GOD_FILE_DEFAULT_MAX_LINES)
    max_decls = nums.get("god-file-max-decls", GOD_FILE_DEFAULT_MAX_DECLS)
    return {"enabled": enabled, "max_lines": max_lines, "max_decls": max_decls}
