#!/usr/bin/env python3
"""PreToolUse hook — language-agnostic path checks.

Hard-blocks Write/Edit/MultiEdit when the target path itself violates
universal structural rules from references/common/structure.md:

- ST-005:           junk-drawer filenames (utils.ts, helpers.py, common.go, ...).
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
from _exclusions import is_excluded_path  # noqa: E402

# ST-005 — junk-drawer filenames. Files named for *what they are* instead of
# *what they do*. Everything ends up there because nothing has to.
JUNK_DRAWER_STEMS = {"utils", "helpers", "common", "misc", "lib", "util", "helper"}
JUNK_DRAWER_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs",
    ".py", ".go", ".cs", ".java", ".kt", ".php", ".rb", ".rs",
}
# ST-005 is absolute — a junk-drawer stem is wrong in every directory, including
# shared-utility homes like shared/lib/. A project that must keep such a file uses
# `.coding-standards-ignore`, not a hard-coded global whitelist.

# ST-005 corollary — generic mega-files directly under a `src/` directory
# (root-level `src/types.ts` OR a nested one like `apps/web/src/constants.ts` —
# the pattern matches `src/<name>` at any depth). These collect knowledge that
# should live next to the capability that owns it. Covers JS/TS/Python paths;
# Go/C#/Java equivalents aren't `src/`-rooted so they aren't matched here.
TOP_LEVEL_MEGAFILE_PATTERN = re.compile(
    r"(^|/)src/(types|constants|utils|helpers|common|misc)\.(ts|tsx|js|jsx|py)$"
)


def check_path_violations(file_path: str) -> list[str]:
    violations: list[str] = []
    p = Path(file_path)
    normalized = file_path.replace("\\", "/")

    if p.suffix.lower() in JUNK_DRAWER_EXTS and p.stem.lower() in JUNK_DRAWER_STEMS:
        violations.append(
            f"{file_path} — ST-005: junk-drawer filename `{p.name}`; "
            f"name files by what they do (e.g. format-currency.ts, parse-date.ts)"
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

    # Path checks only fire on Write — Edit/MultiEdit operate on existing files
    # whose path was already accepted, so we only police newly-created paths.
    if tool_name != "Write":
        return 0

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
    violations = check_path_violations(file_path)
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
