#!/usr/bin/env python3
"""Verify a coding-standards review report is grounded in a recorded structure.

A review is supposed to resolve the project structure (SKILL.md Step 4) and
record it in `.coding-standards-structure` BEFORE reviewing, so the structural
findings have a baseline to measure against. Nothing at write time can enforce
that — "I asked the user" and "the review finished" are not Write/Edit events a
PreToolUse hook can intercept. This driver closes the gap at the one artifact a
review always produces: the report file.

It reads the report's `Structure baseline:` field and checks it against disk:

    grounded     — the field names a recorded structure file, and that file
                   exists. Exit 0.
    declared-skip — the field says `NOT RECORDED` with a reason (unsupported
                   framework, or a below-threshold review that declined). The
                   skip is honest, but never silent: Exit 1 so the caller
                   surfaces it.
    inconsistent — the field claims a recorded structure but no file is on disk,
                   OR the field is missing/unparseable. The report asserts a
                   baseline that was never written. Exit 2.

The file on disk is ground truth: whatever the report typed in the field, a
review that skipped Step 4 leaves no `.coding-standards-structure`, and this
catches it.

Usage:
    python3 check-review-report.py <report.md> [--root <framework-project-root>]

`--root` is the framework project root that owns `.coding-standards-structure`
(the sub-project root in a monorepo). Omit it for a single-root repo: the root
is derived from the report path (`<root>/.coding-standards/reviews/<ts>.md`).
A relative recorded path in the field is resolved against that root.

Stdlib only.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

GROUNDED = 0
DECLARED_SKIP = 1
INCONSISTENT = 2

_BASELINE_LINE = re.compile(
    r"(?im)^\s*[-*]\s*\*\*\s*structure baseline\s*:\s*\*\*\s*(?P<body>.+?)\s*$"
)
_REASON = re.compile(r"\(([^)]*)\)")


@dataclass(frozen=True)
class StructureClaim:
    """What the report's `Structure baseline:` field asserts."""

    state: str  # "recorded" | "not_recorded" | "missing"
    target: str | None  # e.g. "follows feature-first" / "custom"
    recorded_path: str | None  # the path the field names, verbatim
    reason: str | None  # the declared reason, when NOT RECORDED


@dataclass(frozen=True)
class Verdict:
    exit_code: int
    message: str


def parse_baseline(report_text: str) -> StructureClaim:
    """Extract the structure-baseline claim from a review report's Markdown."""
    match = _BASELINE_LINE.search(report_text)
    if match is None:
        return StructureClaim("missing", None, None, None)

    body = match.group("body").strip()
    if "NOT RECORDED" in body.upper():
        reason_match = _REASON.search(body)
        reason = reason_match.group(1).strip() if reason_match else None
        return StructureClaim("not_recorded", None, None, reason)

    marker = "recorded at"
    lowered = body.lower()
    if marker in lowered:
        cut = lowered.index(marker) + len(marker)
        target = body[: lowered.index(marker)].rstrip(" —-").strip()
        recorded_path = body[cut:].strip().strip("`").rstrip(".").strip()
        return StructureClaim("recorded", target or None, recorded_path or None, None)

    # Field present but neither "NOT RECORDED" nor a "recorded at <path>" — can't
    # confirm anything from it. Treated as missing so it fails loudly.
    return StructureClaim("missing", None, None, None)


def derive_root(report_path: Path, override: Path | None) -> Path:
    """The framework project root that owns `.coding-standards-structure`.

    `--root` wins (the caller knows the sub-project root in a monorepo).
    Otherwise infer from the report's canonical location,
    `<root>/.coding-standards/reviews/<ts>.md` → three levels up.
    """
    if override is not None:
        return override.resolve()
    resolved = report_path.resolve()
    parents = resolved.parents
    # parents[0]=reviews, [1]=.coding-standards, [2]=root (the canonical layout).
    if len(parents) >= 3 and parents[1].name == ".coding-standards":
        return parents[2]
    return resolved.parent


def resolve_record(claim_path: str, root: Path) -> Path:
    candidate = Path(claim_path)
    return candidate if candidate.is_absolute() else (root / candidate)


def evaluate(report_path: Path, root_override: Path | None) -> Verdict:
    if not report_path.is_file():
        return Verdict(INCONSISTENT, f"report not found: {report_path}")

    claim = parse_baseline(report_path.read_text(encoding="utf-8", errors="replace"))
    root = derive_root(report_path, root_override)

    if claim.state == "missing":
        return Verdict(
            INCONSISTENT,
            "review report has no parseable `Structure baseline:` field — the "
            "structure step (SKILL.md Step 4) was not recorded in the report. "
            "Resolve + record the structure, then rewrite the report.",
        )

    if claim.state == "not_recorded":
        reason = claim.reason or "no reason given"
        return Verdict(
            DECLARED_SKIP,
            f"structure baseline NOT RECORDED ({reason}) — structural review is "
            "not grounded. Legitimate only for an unsupported framework or a "
            "declined below-threshold review; otherwise Step 4 was skipped.",
        )

    record = resolve_record(claim.recorded_path or "", root)
    if record.is_file():
        return Verdict(
            GROUNDED,
            f"structure baseline grounded: {claim.target or 'recorded'} "
            f"({record}).",
        )
    return Verdict(
        INCONSISTENT,
        f"report claims a recorded structure ({claim.target or 'recorded'}) at "
        f"{record}, but no such file exists — the structure was never recorded. "
        "Resolve + record the structure (SKILL.md Step 4), then rewrite the report.",
    )


def parse_args(argv: list[str]) -> tuple[Path, Path | None]:
    report: Path | None = None
    root: Path | None = None
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--root":
            if index + 1 >= len(argv):
                raise SystemExit("--root needs a path argument")
            root = Path(argv[index + 1])
            index += 2
            continue
        if report is not None:
            raise SystemExit(f"unexpected extra argument: {token}")
        report = Path(token)
        index += 1
    if report is None:
        raise SystemExit("usage: check-review-report.py <report.md> [--root <dir>]")
    return report, root


def main() -> int:
    report, root = parse_args(sys.argv[1:])
    verdict = evaluate(report, root)
    stream = sys.stdout if verdict.exit_code == GROUNDED else sys.stderr
    print(verdict.message, file=stream)
    return verdict.exit_code


if __name__ == "__main__":
    sys.exit(main())
