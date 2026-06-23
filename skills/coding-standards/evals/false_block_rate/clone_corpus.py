#!/usr/bin/env python3
"""Clone the pinned corpus repos at their exact SHAs into a cache directory.

Uses a depth-1 fetch of the pinned commit (`git fetch --depth 1 origin <sha>`),
so only that one commit's tree is downloaded — fast even for large repos like
django. Idempotent: a repo already checked out at the recorded SHA is skipped, so
re-running the eval doesn't re-download.

Stdlib only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from corpus import CORPUS, RepoSpec

_REF_MARKER = ".corpus-ref"


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=600,
    )


def _already_cloned(target: Path, ref: str) -> bool:
    marker = target / _REF_MARKER
    return marker.is_file() and marker.read_text(encoding="utf-8").strip() == ref


def clone_one(spec: RepoSpec, cache_dir: Path) -> Path:
    """Clone one repo at its pinned SHA; return the checkout path.

    Raises RuntimeError if the fetch or checkout fails so the caller can report
    which repo could not be retrieved rather than scanning an empty directory.
    """
    target = cache_dir / spec.name
    if _already_cloned(target, spec.ref):
        return target

    target.mkdir(parents=True, exist_ok=True)
    steps = (
        ["init", "-q"],
        ["remote", "add", "origin", spec.url],
        ["fetch", "-q", "--depth", "1", "origin", spec.ref],
        ["checkout", "-q", "FETCH_HEAD"],
    )
    for step in steps:
        result = _git(step, target)
        if result.returncode != 0:
            raise RuntimeError(f"{spec.name}: git {step[0]} failed — {result.stderr.strip()}")

    (target / _REF_MARKER).write_text(spec.ref + "\n", encoding="utf-8")
    return target


def clone_all(cache_dir: Path) -> dict[str, Path]:
    """Clone every corpus repo; return name -> checkout path for successes."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    checkouts: dict[str, Path] = {}
    for spec in CORPUS:
        checkouts[spec.name] = clone_one(spec, cache_dir)
    return checkouts
