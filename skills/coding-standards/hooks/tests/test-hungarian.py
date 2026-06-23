#!/usr/bin/env python3
"""Regression test — NM-006 Hungarian notation coverage (ISS-013, ISS-018).

ISS-013: TS class fields / interface members / object properties (`private
  strName`, `strHost: string`) — not just let/const/var/param shapes.
ISS-018: Go and Java/Kotlin gain the same multi-char-prefix Hungarian check.
False-positive guard throughout: `strategy`, `strengthScore`, `strings`,
`strconv`, `name` must pass (the char after the prefix is lowercase).

    python3 hooks/tests/test-hungarian.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

TS, GO, JVM = "block-ts-violations.py", "block-go-violations.py", "block-jvm-violations.py"

CASES: list[Case] = [
    # ISS-013 — TS members, must block.
    Case("ts private class field", TS, "/t/a.ts",
         "export class C {\n  private strName: string = ''\n}\n", block=True, rule="NM-006"),
    Case("ts interface member", TS, "/t/b.ts",
         "export interface I {\n  strHost: string\n}\n", block=True, rule="NM-006"),
    # ISS-013 — false-positive guard, must pass.
    Case("ts strategy/strengthScore ok", TS, "/t/c.ts",
         "export interface I {\n  strategy: string\n  strengthScore: number\n}\n", block=False),

    # ISS-018 — Go, must block.
    Case("go short var strName", GO, "/t/a.go",
         "package p\nfunc f() { strName := \"x\"; _ = strName }\n", block=True, rule="NM-006"),
    Case("go param strData", GO, "/t/b.go",
         "package p\nfunc f(strData string) string { return strData }\n", block=True, rule="NM-006"),
    # ISS-018 — Go false-positive guard.
    Case("go strings/strconv ok", GO, "/t/c.go",
         "package p\nimport \"strings\"\nfunc f() string { return strings.Join(nil, \"\") }\n", block=False),

    # ISS-018 — Java/Kotlin, must block.
    Case("java field String strName", JVM, "/t/A.java",
         "class A {\n  private String strName = \"\";\n}\n", block=True, rule="NM-006"),
    Case("kotlin val strName", JVM, "/t/B.kt",
         "val strName: String = \"\"\n", block=True, rule="NM-006"),
    # ISS-018 — Java false-positive guard.
    Case("java strategy/name ok", JVM, "/t/C.java",
         "class C {\n  private String strategy = \"\";\n  private String name = \"\";\n}\n", block=False),
]


if __name__ == "__main__":
    sys.exit(report("hungarian", CASES))
