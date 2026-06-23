#!/usr/bin/env python3
"""Regression test — OD-004 hybrid-class detector requires >=2 accessors (P2).

The detector once fired on ONE accessor + ONE business method, over-firing on
ordinary classes (a single computed @property / getter next to a real method — the
Django corpus false positive). It now needs >=2 accessor members before the hard
block; a single-accessor class is left to review judgement (Worker 1 owns OD-004).

Python OD-004 uses stdlib `ast` (always on). The TS cases need tree-sitter and skip
loudly when it's absent (run-all.py then reports DEGRADED).

    <venv-python> hooks/tests/test-od004.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, run_cases  # noqa: E402

PY = "block-py-violations.py"
TS = "block-ts-violations.py"

PY_HYBRID = (
    "class Order:\n"
    "    @property\n"
    "    def total(self):\n"
    "        return self._total\n"
    "    @property\n"
    "    def tax(self):\n"
    "        return self._tax\n"
    "    def apply_discount(self, pct):\n"
    "        self._total = self._total * (1 - pct)\n"
    "        return self._total\n"
)
PY_ORDINARY = (
    "class Order:\n"
    "    @property\n"
    "    def total(self):\n"
    "        return self._total\n"
    "    def apply_discount(self, pct):\n"
    "        self._total = self._total * (1 - pct)\n"
    "        return self._total\n"
)

PY_CASES = [
    Case("py 2 properties + business method blocks", PY, "/t/order.py", PY_HYBRID, block=True, rule="OD-004"),
    Case("py 1 property + business method passes (over-fire fix)", PY, "/t/order2.py", PY_ORDINARY, block=False),
]

TS_HYBRID = (
    "export class Order {\n"
    "  get total() { return this._total }\n"
    "  get tax() { return this._tax }\n"
    "  applyDiscount(pct: number) {\n"
    "    this._total = this._total * (1 - pct)\n"
    "    return this._total\n"
    "  }\n"
    "}\n"
)
TS_ORDINARY = (
    "export class Order {\n"
    "  get total() { return this._total }\n"
    "  applyDiscount(pct: number) {\n"
    "    this._total = this._total * (1 - pct)\n"
    "    return this._total\n"
    "  }\n"
    "}\n"
)

TS_CASES = [
    Case("ts 2 getters + business method blocks", TS, "/t/order.ts", TS_HYBRID, block=True, rule="OD-004"),
    Case("ts 1 getter + business method passes (over-fire fix)", TS, "/t/order2.ts", TS_ORDINARY, block=False),
]


def main() -> int:
    failures = run_cases(PY_CASES)
    ran_ts = False
    try:
        import tree_sitter, tree_sitter_typescript  # noqa: F401
        ran_ts = True
    except Exception:  # noqa: BLE001
        sys.stderr.write("SKIP od004 TS cases: tree-sitter not importable here "
                         "(run with the venv python); run-all.py reports DEGRADED.\n")
    if ran_ts:
        failures += run_cases(TS_CASES)
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    total = len(PY_CASES) + (len(TS_CASES) if ran_ts else 0)
    print(f"ok — {total} OD-004 (>=2 accessor) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
