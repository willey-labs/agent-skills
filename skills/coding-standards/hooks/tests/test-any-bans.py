#!/usr/bin/env python3
"""Regression test — OD-006 `any`/`Any` ban coverage (ISS-002 TS, ISS-003 Python).

Pins the gaps the audit found: `any` as a non-leading generic argument
(`Record<string, any>`), type-alias laundering (`type X = any`), PEP 585
lowercase builtins (`dict[str, Any]`), and PEP 604 pipe unions (`int | Any`).
Plus the false-positive guard: identifiers that merely contain the letters
(company, Anything, unknown) must still pass.

    python3 hooks/tests/test-any-bans.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

TS = "block-ts-violations.py"
PY = "block-py-violations.py"
GO = "block-go-violations.py"

CASES: list[Case] = [
    # ISS-002 — TypeScript `any`, must block.
    Case("ts record-string-any", TS, "/tmp/x/src/a.ts",
         "export function f(x: Record<string, any>) { return x }\n", block=True, rule="OD-006"),
    Case("ts type-alias laundering", TS, "/tmp/x/src/b.ts",
         "export type Loose = any\nexport const v = 1\n", block=True, rule="OD-006"),
    Case("ts map-string-any", TS, "/tmp/x/src/c.ts",
         "export const m: Map<string, any> = new Map()\n", block=True, rule="OD-006"),
    Case("ts nested promise-map-any", TS, "/tmp/x/src/d.ts",
         "export const p: Promise<Map<string, any>> = null as never\n", block=True, rule="OD-006"),
    Case("ts as any", TS, "/tmp/x/src/e.ts",
         "export const v = (x as any).y\n", block=True, rule="OD-006"),
    Case("ts extends any constraint", TS, "/tmp/x/src/f.ts",
         "export function g<T extends any>(x: T) { return x }\n", block=True, rule="OD-006"),
    # ISS-002 — TypeScript false-positive guards, must pass.
    Case("ts unknown ok", TS, "/tmp/x/src/g.ts",
         "export function f(x: Record<string, unknown>) { return x }\n", block=False),
    Case("ts company/strategy identifiers ok", TS, "/tmp/x/src/h.ts",
         "export const company = { strategy: 1, strengthScore: 2 }\n", block=False),
    Case("ts Array<string> ok", TS, "/tmp/x/src/i.ts",
         "export const xs: Array<string> = []\n", block=False),

    # ISS-003 — Python `Any`, must block.
    Case("py dict-str-any pep585", PY, "/tmp/x/a.py",
         "from typing import Any\n\ndef f(x: dict[str, Any]) -> None:\n    pass\n", block=True, rule="OD-006"),
    Case("py list-any pep585", PY, "/tmp/x/b.py",
         "from typing import Any\n\nxs: list[Any] = []\n", block=True, rule="OD-006"),
    Case("py pipe union pep604", PY, "/tmp/x/c.py",
         "from typing import Any\n\ndef f(x: int | Any) -> None:\n    pass\n", block=True, rule="OD-006"),
    Case("py tuple-any-ellipsis", PY, "/tmp/x/d.py",
         "from typing import Any\n\nx: tuple[Any, ...] = ()\n", block=True, rule="OD-006"),
    Case("py callable-returns-any", PY, "/tmp/x/e.py",
         "from typing import Any, Callable\n\nf: Callable[..., Any] = None\n", block=True, rule="OD-006"),
    # ISS-003 — Python false-positive guards, must pass.
    Case("py Anything identifier ok", PY, "/tmp/x/f.py",
         "class Anything:\n    pass\n\ncompany = Anything()\n", block=False),
    Case("py dict-str-int ok", PY, "/tmp/x/g.py",
         "x: dict[str, int] = {}\ny: list[str] = []\n", block=False),

    # Go `any` is now an ADVISORY (exit 0 + stderr), NOT a hard block — it fired on
    # ~60% of idiomatic Go files in the GAP-002 corpus. These must NOT block; the
    # advisory-stderr assertion lives in test-idiomatic-carveouts.py.
    Case("go return-tuple any advisory", GO, "/tmp/x/a.go",
         "package p\nfunc Load() (any, error) { return nil, nil }\n", block=False),
    Case("go map[any] key advisory", GO, "/tmp/x/b.go",
         "package p\nvar m map[any]string\n", block=False),
    # ISS-014 — Go false-positive guard.
    Case("go company identifier ok", GO, "/tmp/x/c.go",
         "package p\nfunc f() { company := 1; _ = company }\n", block=False),
]


if __name__ == "__main__":
    sys.exit(report("any-ban", CASES))
