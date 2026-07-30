#!/usr/bin/env python3
"""Asking a separate model to judge comment prose, and rendering its verdicts.

The judge runs as its own process with no tools, no MCP servers, no hooks and one
turn: it receives the rules and the comment blocks as text and answers with JSON.
Being a separate call is the point — the pass that wrote a comment is the worst judge
of whether it earns its place.

Every failure path returns None or an empty list. A judge that cannot answer must
leave the turn alone rather than guess.

Stdlib only; the model is reached through the installed CLI.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from _comment_blocks import CommentBlock

GUARD_ENV = "CODING_STANDARDS_COMMENT_JUDGE"
MODEL_ENV = "CODING_STANDARDS_JUDGE_MODEL"
DEFAULT_MODEL = "sonnet"
TIMEOUT_SECONDS = 120

RULES = """You are reviewing COMMENT PROSE in source code against a standard whose
default is: write no comment.

A comment earns its place ONLY by carrying what the code itself cannot say:
- a constraint or invariant that is not visible in the syntax
- the reason a non-obvious choice was made
- a link to an external spec, ticket, or bug
- a warning about a sharp edge
- an API doc on a public surface that adds information the signature does not

Everything else goes. Flag:
- narration: the comment restates what the lines below it plainly do
- naming failures: it explains WHAT a value or function is (the fix is the name)
- redundant docstrings that restate the signature; banner or divider comments
- filler preambles (Note:, Important:, Basically, Here's how this works)
- narration of the edit or of history (updated to..., was X now Y, used to be...)
- chat left in the file: text addressed to a person, first-person deliberation,
  alternatives weighed inline, questions left in place, TODO with nothing tracking it
- length: several lines where one carries the only fact the reader needs, or where
  the rest argues the author's case to a reviewer

Be strict, and judge line by line. The bar is not "does this contain something
true" — it is "does every line carry a fact the next reader cannot get from the
code". A block over two lines is a defect unless each line carries a distinct such
fact; if one line can carry it, the verdict is "shorten" with that line, however
correct the rest is.

Two things that look like rationale but are not: explaining the change to a reviewer,
and arguing that a branch is justified. Keep the fact a reader needs to avoid
breaking the code; cut the argument for the author's decision.

Verdicts: "delete" (carries nothing the code cannot say), "shorten" (a fact is worth
keeping — give the one replacement line), "keep" (every line earns its place as
written). Judge only the prose you are shown; assume the code is correct.

Reply with JSON only, no prose and no code fence:
{"findings":[{"id":<block id>,"verdict":"delete|shorten|keep","why":"<one short line>","replacement":"<single comment line, only for shorten>"}]}
Return one entry per block id you were given."""


@dataclass(frozen=True)
class Finding:
    """One judged block that has to change."""

    file_path: str
    line: int
    verdict: str
    why: str
    replacement: str


def build_prompt(blocks: list[CommentBlock]) -> str:
    """The rules plus every block, as one prompt."""
    parts = [RULES, ""]
    for block in blocks:
        parts.append(f"--- BLOCK {block.block_id} — {block.file_path}:{block.line}")
        parts.append("COMMENT:")
        parts.append(block.comment)
        parts.append("CODE BELOW IT:")
        parts.append(block.code or "(end of file)")
        parts.append("")
    return "\n".join(parts)


def _extract_json(text: str) -> dict | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _command(cli: str) -> list[str]:
    """The judge invocation: one turn, no tools, no MCP, no hooks."""
    return [
        cli,
        "-p",
        "--model",
        os.environ.get(MODEL_ENV) or DEFAULT_MODEL,
        "--disallowedTools",
        "*",
        "--max-turns",
        "1",
        "--strict-mcp-config",
        "--settings",
        '{"hooks":{}}',
    ]


def ask_judge(prompt: str) -> dict | None:
    """Run the separate model call. None on any failure — the judge fails open."""
    cli = shutil.which("claude")
    if not cli:
        return None
    env = dict(os.environ)
    env[GUARD_ENV] = "running"
    try:
        with tempfile.TemporaryDirectory() as workdir:
            proc = subprocess.run(
                _command(cli),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                env=env,
                cwd=workdir,
            )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return _extract_json(proc.stdout)


def findings_from(answer: dict, blocks: list[CommentBlock]) -> list[Finding]:
    """The delete/shorten verdicts, matched back to the blocks that were sent."""
    by_id = {block.block_id: block for block in blocks}
    found: list[Finding] = []
    for row in answer.get("findings") or []:
        if not isinstance(row, dict):
            continue
        block = by_id.get(row.get("id"))
        verdict = str(row.get("verdict") or "").lower()
        if block is None or verdict not in {"delete", "shorten"}:
            continue
        found.append(
            Finding(
                file_path=block.file_path,
                line=block.line,
                verdict=verdict,
                why=str(row.get("why") or "").strip(),
                replacement=str(row.get("replacement") or "").strip(),
            )
        )
    return found


def render(findings: list[Finding]) -> str:
    """The instruction a held-open turn is given."""
    lines = [
        "coding-standards comment judge (CM-001..CM-006) — these comments must change "
        "before this turn ends.",
        "Apply each edit now (deleting or trimming a comment cannot change behaviour), "
        "then finish. If a specific finding is wrong, keep that comment and say why in "
        "your reply.",
    ]
    for finding in findings:
        where = f"{finding.file_path}:{finding.line}"
        if finding.verdict == "shorten" and finding.replacement:
            lines.append(f"  - {where} — replace the block with: {finding.replacement}")
            lines.append(f"      ({finding.why})")
        else:
            lines.append(f"  - {where} — delete: {finding.why}")
    return "\n".join(lines) + "\n"
