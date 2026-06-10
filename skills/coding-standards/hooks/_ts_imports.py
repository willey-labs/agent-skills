#!/usr/bin/env python3
"""ST-003 import checks for TypeScript / JavaScript.

Deep-import detection is structure-derived, never toggled: a path is flagged only
when the folder it reaches into actually exposes an index barrel (a public API to
reach past). A barrel-less layout (route-colocated, a flat package) has no front
door, so nothing is flagged. Covers the `@/` and `~/` aliases and relative
(`../…`) imports, plus the 3+-level parent-traversal smell.

Split out of block-ts-violations.py so that file stays one job — the regex
content checks + orchestration (ST-008).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _exclusions import find_project_root  # noqa: E402

# `@/foo/bar` is fine (capability + use case). `@/foo/bar/baz` reaches past. `cap`
# captures the 2-level capability so we can check for a barrel before flagging.
# Both `@/` and `~/` aliases; segments allow any case (some projects use
# PascalCase capability folders) — the barrel gate keeps false positives down.
DEEP_IMPORT_PATTERN = re.compile(
    r"""from\s+['"][@~]/(?P<cap>[\w-]+/[\w-]+)/[\w-]+"""
)
# Relative imports — flagged when the imported file's folder has a barrel and the
# importer lives outside it (see _relative_deep_import).
RELATIVE_IMPORT_PATTERN = re.compile(r"""from\s+['"](?P<spec>\.\.?/[^'"]+)['"]""")
PARENT_TRAVERSAL_PATTERN = re.compile(r"""from\s+['"](\.\./){3,}""")

BARREL_NAMES = (
    "index.ts", "index.tsx", "index.js", "index.jsx",
    "index.mts", "index.cts", "index.mjs", "index.cjs",
)


def _alias_base(project_root: Path) -> Path:
    """Where `@/` / `~/` resolves — `src/` when present, else the project root.
    Covers the dominant convention; an unusual tsconfig mapping just means a barrel
    isn't found and the import isn't flagged (fail open)."""
    src = project_root / "src"
    return src if src.is_dir() else project_root


def _folder_has_barrel(folder: Path) -> bool:
    return folder.is_dir() and any((folder / name).is_file() for name in BARREL_NAMES)


def _capability_has_barrel(project_root: Path | None, capability: str) -> bool:
    """True when the alias capability folder (`foo/bar`) exposes an index barrel."""
    if project_root is None:
        return False
    return _folder_has_barrel(_alias_base(project_root) / capability)


def _relative_deep_import(importer: Path, spec: str) -> bool:
    """True when a relative import reaches past a folder's barrel: the imported
    file's folder exposes an index, the file isn't that index, and the importer
    lives outside that folder (a same-folder/descendant import is fine)."""
    try:
        target = (importer.parent / spec).resolve()
        importer_resolved = importer.resolve()
    except OSError:
        return False
    folder = target.parent
    if target.stem == "index":
        return False
    if not _folder_has_barrel(folder):
        return False
    try:
        importer_resolved.relative_to(folder)
        return False
    except ValueError:
        return True


def iter_import_violations(clean_lines: list[str], file_path: str) -> Iterable[str]:
    project_root = find_project_root(Path(file_path))
    importer = Path(file_path)
    for idx, line in enumerate(clean_lines, start=1):
        alias_match = DEEP_IMPORT_PATTERN.search(line)
        rel_match = RELATIVE_IMPORT_PATTERN.search(line)
        crosses = (
            (alias_match and _capability_has_barrel(project_root, alias_match.group("cap")))
            or (rel_match and _relative_deep_import(importer, rel_match.group("spec")))
        )
        if crosses:
            yield (
                f"{file_path}:{idx} — ST-003: deep import past folder's public API; "
                f"import from the capability's front door (its index) instead"
            )
        if PARENT_TRAVERSAL_PATTERN.search(line):
            yield (
                f"{file_path}:{idx} — parent traversal of 3+ levels; "
                f"use a path alias (e.g. @/) or move the file closer to its caller"
            )
