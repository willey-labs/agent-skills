#!/usr/bin/env python3
"""Stop hook — a second reader judges the comments a turn wrote, and holds it open.

The CM-* rules are prose judgement: no regex separates a constraint the reader needs
from an author defending an edit, which is why the write-time hook catches only the
mechanical tells. The judgement needs a reader, and it has to be a *different* reader
than the one that wrote the comment — a pass that just wrote a paragraph of
self-justification will also approve it.

So when a turn tries to end, the comments it added go to a separate model call, and a
delete or shorten verdict exits 2 — which the hook contract turns into "prevents
Claude from stopping", with the findings fed back as the instruction to fix them.
Deleting or trimming a comment cannot change behaviour, so the fix needs no approval.

Bounds, because a judge that keeps disagreeing must not trap a session: an active Stop
hook or our own nested call exits at once; a session is held open at most MAX_ROUNDS
times, after which findings are reported and the turn ends; every failure — no CLI,
timeout, unparseable answer — exits 0 in silence.

Exit 2 holds the turn open, 0 lets it end.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _comment_blocks import collect_blocks  # noqa: E402
from _comment_judge import GUARD_ENV, ask_judge, build_prompt, findings_from, render  # noqa: E402
from _hook_run import read_payload  # noqa: E402
from _touched_ledger import drain, rounds_spent, session_key, spend_round  # noqa: E402

MAX_ROUNDS = 2


def main() -> int:
    payload = read_payload()
    if payload is None or payload.get("stop_hook_active") or os.environ.get(GUARD_ENV):
        return 0

    key = session_key(payload)
    blocks = collect_blocks(drain(key))
    if not blocks:
        return 0

    answer = ask_judge(build_prompt(blocks))
    if answer is None:
        return 0
    findings = findings_from(answer, blocks)
    if not findings:
        return 0

    if rounds_spent(key) >= MAX_ROUNDS:
        sys.stdout.write(
            "coding-standards comment judge still reports comments to fix, and has already "
            f"held this session open {MAX_ROUNDS} times — reporting instead of blocking:\n"
            + render(findings)
        )
        return 0

    spend_round(key)
    sys.stderr.write(render(findings))
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"coding-standards: judge-comments skipped ({exc})\n")
        sys.exit(0)
