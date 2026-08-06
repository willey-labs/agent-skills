#!/usr/bin/env python3
"""Regression test — CM-004/005/006 comment-slop advisory.

Asserts three things the hook lives or dies by: it flags the mechanical tells, it
stays silent on a legitimate rationale comment (precision is the whole bar for a
prose check), and it never exits 2 — every finding is an advisory.

`harness.run_cases` asserts exit codes, so this test drives the hook directly and
borrows only the harness reporter: the signal here is the rule code in the context
the hook hands Claude, not the exit status.

    python3 hooks/tests/test-comment-slop.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import report_failures  # noqa: E402

HOOKS_DIR = Path(__file__).resolve().parent.parent
HOOK = HOOKS_DIR / "advise-comment-slop.py"

sys.path.insert(0, str(HOOKS_DIR))
from _hook_run import advisory_text  # noqa: E402


@dataclass
class Case:
    """One advisory case. `rule` is the code expected in the message, or None for a
    file that must come back silent."""

    name: str
    file_path: str
    content: str
    rule: str | None


FLAGGED = [
    Case("emoji", "/tmp/cs/src/a.ts", "// 🚀 ship it\nexport const x = 1\n", "CM-005"),
    Case("bang", "/tmp/cs/src/b.ts", "// never call this twice!\nexport const x = 1\n", "CM-005"),
    Case("edit label", "/tmp/cs/src/c.ts", "// NEW: cursor paging\nexport const x = 1\n", "CM-005"),
    Case(
        "edit sentence",
        "/tmp/cs/src/d.go",
        "// Updated to handle the empty slice\nfunc f() {}\n",
        "CM-005",
    ),
    Case("was/now", "/tmp/cs/src/e.go", "// was 3, now 5 retries\nfunc f() {}\n", "CM-005"),
    Case(
        "history",
        "/tmp/cs/src/f.py",
        "# this used to be a lock, before the change\nx = 1\n",
        "CM-005",
    ),
    Case("filler", "/tmp/cs/src/g.py", "# Note: run this before init\nx = 1\n", "CM-005"),
    Case("banner", "/tmp/cs/src/h.py", "# ===== helpers =====\nx = 1\n", "CM-004"),
    Case(
        "reader address",
        "/tmp/cs/src/i.py",
        '"""As requested, totals the invoice lines."""\nx = 1\n',
        "CM-006",
    ),
    Case(
        "first person",
        "/tmp/cs/src/J.java",
        "/** I think a map reads better here. */\nclass J {}\n",
        "CM-006",
    ),
    Case(
        "deliberation",
        "/tmp/cs/src/k.php",
        "<?php\n# not sure if this handles an empty cart\n",
        "CM-006",
    ),
    Case("bare todo", "/tmp/cs/src/l.ts", "// TODO: tidy this up later\nexport const x = 1\n", "CM-006"),
]

CLEAN = [
    Case(
        "rationale comment",
        "/tmp/cs/src/m.py",
        "# the gateway rounds half-to-even; invoices round half-up (FIN-2231)\nx = 1\n",
        None,
    ),
    Case(
        "tracked todo",
        "/tmp/cs/src/n.ts",
        "// TODO ABC-412: drop the shim once v3 lands\nexport const x = 1\n",
        None,
    ),
    Case("linter directive", "/tmp/cs/src/o.py", "# noqa: E501\nx = 1\n", None),
    Case("shebang", "/tmp/cs/src/p.py", "#!/usr/bin/env python3\nx = 1\n", None),
    Case(
        "chat inside a string, not a comment",
        "/tmp/cs/src/q.ts",
        'export const msg = "as we discussed, I think #1 wins!"\n',
        None,
    ),
    Case(
        "prompt template is not a docstring",
        "/tmp/cs/src/r.py",
        'PROMPT = """\n----- FILE -----\nNote: I think you should fix it!\n"""\n',
        None,
    ),
    Case("C# preprocessor region", "/tmp/cs/src/S.cs", "#region Note: helpers\nclass S {}\n", None),
    Case(
        "domain use of a trigger word",
        "/tmp/cs/src/t.go",
        "// tokens issued previously stay valid until their expiry\nfunc f() {}\n",
        None,
    ),
]


def run(case: Case) -> tuple[int, str]:
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": case.file_path, "content": case.content}}
    )
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True
    )
    return proc.returncode, advisory_text(proc.stdout) + proc.stderr


def check(case: Case) -> str | None:
    code, message = run(case)
    if code != 0:
        return f"{case.name}: advisory must exit 0, got {code}"
    if case.rule is None:
        return f"{case.name}: expected silence, got {message.strip()}" if message.strip() else None
    if case.rule not in message:
        return f"{case.name}: expected {case.rule} in the message, got {message.strip() or '<silence>'}"
    return None


def cap_failure() -> str | None:
    """The per-file finding cap keeps a chatty file from flooding the transcript."""
    content = "".join(f"// TODO: item {i}\n" for i in range(20))
    _code, message = run(Case("cap", "/tmp/cs/src/u.ts", content, "CM-006"))
    if "(+5 more" not in message:
        return f"cap: expected 15 findings plus a '+5 more' tail, got {message.strip()}"
    return None


def main() -> int:
    cases = FLAGGED + CLEAN
    failures = [f for f in (check(case) for case in cases) if f]
    cap = cap_failure()
    if cap:
        failures.append(cap)
    return report_failures("comment-slop", failures, len(cases) + 1)


if __name__ == "__main__":
    sys.exit(main())
