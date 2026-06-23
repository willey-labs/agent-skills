#!/usr/bin/env python3
"""Regression test — FN-005 FastAPI + pytest carve-outs (ISS-017).

A handler whose params are FastAPI bindings via the no-default `Annotated[T,
Depends(...)]` style (what FastAPI now recommends) must not count toward FN-005;
neither should pytest fixtures or unittest test methods. A plain 5-arg function
still blocks.

    python3 hooks/tests/test-fastapi-fn005.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

PY = "block-py-violations.py"

CASES: list[Case] = [
    Case("annotated-depends handler passes", PY, "/t/api.py",
         "from typing import Annotated\nfrom fastapi import Depends\n\n"
         "def handler(a: Annotated[A, Depends(g)], b: Annotated[B, Depends(g)], "
         "c: Annotated[C, Depends(g)], d: Annotated[D, Depends(g)], "
         "e: Annotated[E, Depends(g)]) -> None:\n    pass\n", block=False),
    Case("default-depends handler passes", PY, "/t/api2.py",
         "from fastapi import Depends, Query\n\n"
         "def h(a=Depends(g), b=Depends(g), c=Depends(g), d=Depends(g), e=Query(None)):\n"
         "    return a\n", block=False),
    Case("pytest fixture many params passes", PY, "/t/conftest.py",
         "import pytest\n\n@pytest.fixture\ndef big(a, b, c, d, e):\n    return a\n", block=False),
    Case("unittest testFoo passes", PY, "/t/test_x.py",
         "def testFoo(self, a, b, c, d):\n    return a\n", block=False),
    Case("plain 5-arg fn still blocks", PY, "/t/plain.py",
         "def f(a, b, c, d, e):\n    return a\n", block=True, rule="FN-005"),
    Case("mixed: 5 real args + 1 depends still blocks", PY, "/t/mix.py",
         "from fastapi import Depends\n\n"
         "def h(a, b, c, d, e, db=Depends(g)):\n    return a\n", block=True, rule="FN-005"),
]


if __name__ == "__main__":
    sys.exit(report("fastapi-fn005", CASES))
