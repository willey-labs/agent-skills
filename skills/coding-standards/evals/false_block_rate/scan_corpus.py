#!/usr/bin/env python3
"""Run every content hook over the corpus and record what blocks.

For each source file we build the same synthetic `Write` payload the hooks see at
write time (file path + current content) and run each content hook against
it — individually, so every block is attributed to the specific hook that fired
(review-files.py merges hooks and loses that attribution, which the per-hook rate
needs). A hook exiting 2 is a hard block; exiting 0 with stderr is an advisory.

The interpreter passed in MUST be able to import tree-sitter, or the TS/JS AST
checks silently no-op and the TS rate is understated — the runner is responsible
for handing in a grammar-capable interpreter.

Stdlib only.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from corpus import RepoSpec, SKIP_DIR_NAMES, is_test_file

# review-files.py's HOOK_FILES plus the write-only comment-block limit.
HOOK_FILES: tuple[str, ...] = (
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
    "advise-comment-slop.py",
    "block-added-comments.py",
)

# These subtract the file on disk, so each file reaches them as a brand-new write.
NEW_FILE_HOOKS: frozenset[str] = frozenset({"block-added-comments.py"})

_RULE_CODE = re.compile(r"\b(?:FN|NM|OD|ST|EH|FMT|DP|CM)-\d+\b")


@dataclass(frozen=True)
class ScanContext:
    """Everything a scan needs that isn't the file itself."""

    interpreter: str
    hook_dir: Path
    max_files: int


@dataclass(frozen=True)
class BlockRecord:
    """One hook firing on one file."""

    repo: str
    framework: str
    file: str  # path relative to the repo root
    hook: str
    rule_code: str
    message: str
    is_advisory: bool


@dataclass
class RepoScan:
    """The outcome of scanning one repo."""

    name: str
    framework: str
    files_total: int
    files_scanned: int
    blocks: list[BlockRecord] = field(default_factory=list)


def _rule_code_of(message: str) -> str:
    match = _RULE_CODE.search(message)
    return match.group(0) if match else "any-ban"


def _bullets(stderr: str) -> list[str]:
    out: list[str] = []
    for line in stderr.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            out.append(stripped[2:].strip())
    return out


def iter_source_files(root: Path, extensions: tuple[str, ...]) -> list[Path]:
    """Every source file under root, skipping test/build/dep dirs, sorted."""
    found: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in extensions:
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIR_NAMES for part in rel_parts):
            continue
        if is_test_file(path.name):
            continue
        found.append(path)
    return sorted(found)


def _run_hook(context: ScanContext, hook: str, payload: str) -> tuple[int, list[str]]:
    proc = subprocess.run(
        [context.interpreter, str(context.hook_dir / hook)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, _bullets(proc.stderr)


def _write_payload(file_path: Path, content: str) -> str:
    return json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": str(file_path), "content": content}}
    )


def scan_file(context: ScanContext, file_path: Path, spec: RepoSpec, root: Path) -> list[BlockRecord]:
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    rel = str(file_path.relative_to(root))
    unwritten_path = root.with_name(f"{root.name}.unwritten") / rel
    rewrite_payload = _write_payload(file_path, content)
    new_file_payload = _write_payload(unwritten_path, content)
    records: list[BlockRecord] = []
    for hook in HOOK_FILES:
        payload = new_file_payload if hook in NEW_FILE_HOOKS else rewrite_payload
        code, bullets = _run_hook(context, hook, payload)
        if not bullets:
            continue
        is_advisory = code != 2
        for message in bullets:
            records.append(
                BlockRecord(
                    repo=spec.name,
                    framework=spec.framework,
                    file=rel,
                    hook=hook,
                    rule_code=_rule_code_of(message),
                    message=message,
                    is_advisory=is_advisory,
                )
            )
    return records


def scan_repo(context: ScanContext, spec: RepoSpec, root: Path) -> RepoScan:
    files = iter_source_files(root, spec.extensions)
    scanned = files[: context.max_files]
    result = RepoScan(
        name=spec.name,
        framework=spec.framework,
        files_total=len(files),
        files_scanned=len(scanned),
    )
    for file_path in scanned:
        result.blocks.extend(scan_file(context, file_path, spec, root))
    return result
