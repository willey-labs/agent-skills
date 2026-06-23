#!/usr/bin/env python3
"""The block-message cases for the recovery eval.

Each case is a minimal file that a hook hard-blocks for one rule. The eval hands a
model the file plus the hook's stderr and asks for a fix, testing whether the block
message alone is enough to recover. Cases cover the distinct content-fixable
messages, one per message, across languages.

The violation bodies live in `fixtures.json`, not inline: a file embedding
`except: pass` or `: any` as source would trip the very hooks under test. JSON is a
suffix no hook scans, so the module stays clean and the fixtures stay exact.

Rules whose fix is a rename or a multi-file split are out of scope — they don't fit
the "return the corrected file" loop.

`intent_marker` is a token that must survive a real fix (the function/class name).
If the block clears but the marker is gone, the model deleted the code instead of
fixing it — an evasion, not a recovery.

Stdlib only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_FIXTURES_PATH = Path(__file__).resolve().parent / "fixtures.json"


@dataclass(frozen=True)
class RecoveryCase:
    case_id: str
    rule: str
    file_name: str
    intent_marker: str


CASES: tuple[RecoveryCase, ...] = (
    RecoveryCase("fn005-ts", "FN-005", "create-order.ts", "createOrder"),
    RecoveryCase("fn005-py", "FN-005", "register_user.py", "register_user"),
    RecoveryCase("fn005-go", "FN-005", "charge.go", "Charge"),
    RecoveryCase("nm006-ts", "NM-006", "sum-totals.ts", "sumTotals"),
    RecoveryCase("any-ts", "OD-006", "parse-config.ts", "parseConfig"),
    RecoveryCase("any-py", "OD-006", "load_settings.py", "load_settings"),
    RecoveryCase("eh002-ts", "EH-002", "fetch-user.ts", "fetchUser"),
    RecoveryCase("eh002-py", "EH-002", "read_file.py", "read_file"),
    RecoveryCase("fmt005-ts", "FMT-005", "calc.ts", "calc"),
)


def load_fixtures() -> dict[str, str]:
    """case_id -> the raw violating file content."""
    data = json.loads(_FIXTURES_PATH.read_text(encoding="utf-8"))
    return {str(k): str(v) for k, v in data.items()}
