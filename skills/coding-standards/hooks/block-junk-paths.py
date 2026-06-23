#!/usr/bin/env python3
"""PreToolUse hook — language-agnostic path checks.

Hard-blocks Write/Edit/MultiEdit when the target path itself violates
universal structural rules from references/common/structure.md:

- ST-005:           junk-drawer filenames (utils.ts, helpers.py, common.go, ...)
                    AND junk-drawer folders (a source file under utils/helpers/common/misc).
- ST-005 corollary: top-level mega-files (src/types.ts, src/constants.ts, ...).

Path-only. Does not read file content. Runs for every language the rules
cover (TS/JS, Python, Go, C#, Java/Kotlin, PHP, Ruby, Rust).

Reads the PreToolUse JSON payload from stdin. Exits 2 with a stderr message
to block when violations are found, exits 0 otherwise. Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Add the hooks directory to sys.path so we can import the shared exclusion
# helper. Each hook is invoked as a standalone script via the settings.json
# command entry; this keeps them self-bootstrapping without requiring a package.
sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import (  # noqa: E402
    find_project_root,
    is_excluded_path,
    read_structure_follows,
)

# ST-005 — junk-drawer filenames. Files named for *what they are* instead of
# *what they do*. Everything ends up there because nothing has to.
JUNK_DRAWER_STEMS = {"utils", "helpers", "common", "misc", "lib", "util", "helper"}
# Shared canonical source-extension set, so this universal entry point can't drift
# from the other hooks (ISS-010). Adding a language updates _languages.py only.
from _languages import SOURCE_EXTENSIONS as JUNK_DRAWER_EXTS  # noqa: E402
# ST-005 applies to FOLDERS too ("a file or folder named utils/helpers/common/misc").
# `lib`/`util`/`helper` singular stems stay file-only — `lib/` is a conventional
# infrastructure folder and blocking it would be noise. A junk-drawer *folder*
# collects everything because nothing has to live there; name it by what it holds.
JUNK_DRAWER_FOLDERS = {"utils", "helpers", "common", "misc"}

# .NET uses folders as PascalCase namespaces, so `Common/` under a layer
# (Application/Common/Behaviours) is a structured namespace, not a junk drawer —
# it's the canonical clean-architecture layout (GAP-002 found it blocking 22% of a
# reference repo's files). Exempt the `common` folder for C# ONLY; `common/` in a
# JS/TS project is still a real junk drawer and still blocks.
LANGUAGE_EXEMPT_FOLDERS: dict[str, frozenset[str]] = {".cs": frozenset({"common"})}

# ISS-001 — some published catalog layouts sanction a specific shared folder that
# would otherwise read as junk (bulletproof-react's `src/utils/` and per-feature
# `utils/`). When the project records `follows: <variant>`, the folder names that
# variant publishes are allowed — derived from the adopted standard, not a user
# toggle (same model as ST-003 deep-import). The FILE-stem ban and the src/<name>
# mega-file ban are NOT relaxed: a file literally named `utils.ts` stays junk
# everywhere. Folder allowance only, and only for the variant that publishes it.
STRUCTURE_SANCTIONED_FOLDERS: dict[str, frozenset[str]] = {
    "feature-first": frozenset({"utils"}),
    "route-colocated": frozenset({"utils"}),
}

# ST-005 corollary — generic mega-files directly under a source root: `src/` OR
# `app/` (src-less Next.js), at any depth (`src/types.ts`, `apps/web/src/constants.ts`,
# `app/utils.ts` — ISS-024). These collect knowledge that should live next to the
# capability that owns it. Covers JS/TS/Python paths. Not matched (caught by review,
# not this regex): bare project-root files (`constants.py` with no src/app parent —
# too many legit single-file roots to hard-block) and Go/C#/Java layouts (not
# src/app-rooted). The junk-FILENAME check above still catches `utils.ts` anywhere.
TOP_LEVEL_MEGAFILE_PATTERN = re.compile(
    r"(^|/)(src|app)/(types|constants|utils|helpers|common|misc)\.(ts|tsx|js|jsx|py)$"
)

# shadcn/ui generates `lib/utils.ts` (the `cn()` class-name helper) in nearly
# every Next.js/React project — a near-universal ecosystem convention, not a
# junk drawer. Exempt that exact path from the ST-005 filename ban, the same
# spirit as the `components/ui/**` exclusion. Scope is deliberately narrow
# (`lib/utils.{ts,js}` only): a hand-written junk `lib/utils.ts` is the accepted
# cost; the alternative blocks almost every shadcn project's first file, which the
# GAP-002 corpus confirmed on shadcn's own reference app. Other rules (any,
# Hungarian) still apply to the file — only the junk-FILENAME check is relaxed.
SHADCN_CN_FILE = re.compile(r"(?:^|/)lib/utils\.(?:ts|js)$")


def sanctioned_folders_for(file_path: str) -> frozenset[str]:
    """Folder names a recorded catalog structure publishes (so they aren't junk
    for this project). Empty when no structure is recorded or it sanctions none."""
    root = find_project_root(Path(file_path))
    follows = read_structure_follows(root)
    return STRUCTURE_SANCTIONED_FOLDERS.get(follows or "", frozenset())


def check_path_violations(file_path: str, sanctioned_folders: frozenset[str] = frozenset()) -> list[str]:
    violations: list[str] = []
    p = Path(file_path)
    normalized = file_path.replace("\\", "/")

    is_source = p.suffix.lower() in JUNK_DRAWER_EXTS

    if is_source and p.stem.lower() in JUNK_DRAWER_STEMS and not SHADCN_CN_FILE.search(normalized):
        violations.append(
            f"{file_path} — ST-005: junk-drawer filename `{p.name}`; "
            f"name files by what they do (e.g. format-currency.ts, parse-date.ts)"
        )

    # ST-005 for folders — a source file living under a utils/helpers/common/misc
    # directory. Exact segment match (so `commons/`, `utilities/` don't trip), and
    # only the directory part (the filename is handled above). A folder the recorded
    # catalog structure publishes (sanctioned_folders) is skipped — see ISS-001.
    if is_source:
        lang_exempt = LANGUAGE_EXEMPT_FOLDERS.get(p.suffix.lower(), frozenset())
        junk_dirs = [
            seg for seg in p.parent.parts
            if seg.lower() in JUNK_DRAWER_FOLDERS
            and seg.lower() not in sanctioned_folders
            and seg.lower() not in lang_exempt
        ]
        if junk_dirs:
            violations.append(
                f"{file_path} — ST-005: junk-drawer folder `{junk_dirs[0]}/`; "
                f"name folders by the part of the product they serve, not by kind"
            )

    if TOP_LEVEL_MEGAFILE_PATTERN.search(normalized):
        violations.append(
            f"{file_path} — ST-005 corollary: top-level mega-file forbidden; "
            f"co-locate types/constants with the capability that owns them"
        )

    return violations


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input") or {}
    if tool_name not in {"Write", "Edit", "MultiEdit"}:
        return 0

    # Fire on Edit/MultiEdit as well as Write: a junk-drawer name is a violation
    # however the file got there, and structure-resolution.md promises the *next
    # edit* to such a file is blocked until it's renamed. The `.coding-standards-ignore`
    # file is the escape for a legacy file a team isn't ready to rename yet.
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    # Exclusion check — third-party / generated / vendored code is owned by
    # the tool that produced it, not by the user. Skip silently.
    excluded, _pattern = is_excluded_path(file_path)
    if excluded:
        return 0

    # ST-005 is mandatory in every layout — a `utils.ts` is a junk-drawer name
    # regardless of architecture. No rule has a per-project off switch: the
    # `.coding-standards-structure` file records placement only (follows: / layout:),
    # never a rule toggle.
    violations = check_path_violations(file_path, sanctioned_folders_for(file_path))
    if not violations:
        return 0

    header = (
        "coding-standards hook blocked this write — fix the path and try again.\n"
        "See skills/coding-standards/references/common/structure.md (ST-005).\n"
    )
    sys.stderr.write(header + "\n".join(f"  - {v}" for v in violations) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        # Never let an unexpected internal error block a legitimate write. Fail
        # OPEN: exit 0 so Claude Code proceeds, and note it on stderr for debugging.
        sys.stderr.write(f"coding-standards: block-junk-paths internal error, skipped ({exc})\n")
        sys.exit(0)
