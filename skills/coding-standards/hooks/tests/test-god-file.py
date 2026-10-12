#!/usr/bin/env python3
"""Regression test — ST-008 god-file block.

- Arrow-function / function-expression consts count as behavioral, so a file of
  11+ `export const f = () => …` can't evade the block — while a file of const
  *data* (values, objects, `.map(...)` results) still passes.
- Edit/MultiEdit are counted on the POST-edit content: an Edit that shrinks an
  over-threshold file passes; an Edit that grows a file past the threshold blocks.
- The JVM/C# test exemption is anchored, so `Contest.java` is NOT exempt.

Edit cases need an on-disk fixture, so this test drives the hook directly rather
than through harness.run_cases (which only builds Write payloads).

    python3 hooks/tests/test-god-file.py
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
HOOK = HOOKS_DIR / "block-god-file.py"


def run(payload: dict) -> int:
    proc = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True, text=True
    )
    return proc.returncode


def write_payload(file_path: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}


def edit_payload(file_path: str, old: str, new: str) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": file_path, "old_string": old, "new_string": new}}


def load_module():
    spec = importlib.util.spec_from_file_location("god", HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []

    arrows = "".join(f"export const f{i} = () => {i}\n" for i in range(14))
    if run(write_payload("/tmp/gf/src/arrows.ts", arrows)) != 2:
        failures.append("14 arrow-consts should block")
    data = "".join(f"export const v{i} = {{ id: {i}, xs: [{i}].map(x => x + 1) }}\n" for i in range(14))
    if run(write_payload("/tmp/gf/src/data.ts", data)) != 0:
        failures.append("14 const-data lines should pass (precision)")

    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "src"
        src.mkdir()
        shrink = src / "shrink.ts"
        shrink.write_text("".join(f"export function f{i}() {{ return {i} }}\n" for i in range(11)))
        if run(edit_payload(str(shrink), "export function f10() { return 10 }\n", "")) != 0:
            failures.append("Edit shrinking an 11-decl file to 10 should pass")

        grow = src / "grow.ts"
        grow.write_text("".join(f"export function g{i}() {{ return {i} }}\n" for i in range(10)))
        added = "export function g9() { return 9 }\nexport function g10() {}\nexport function g11() {}\nexport function g12() {}"
        if run(edit_payload(str(grow), "export function g9() { return 9 }", added)) != 2:
            failures.append("Edit growing a 10-decl file past threshold should block")

    god = load_module()
    for name, expect in [
        ("Contest.java", False), ("Attest.cs", False), ("Protest.java", False),
        ("FooTest.java", True), ("OrderServiceTests.cs", True), ("UserTest.kt", True),
    ]:
        if god.is_exempt_name("/p/" + name) != expect:
            failures.append(f"{name} exemption should be {expect}")

    ruby = "".join(f"def m{i}\n  {i}\nend\n" for i in range(11))
    if run(write_payload("/tmp/gf/lib/many.rb", ruby)) != 0:
        failures.append("11-def Ruby file (no content hook) should advise (exit 0), not hard-block")
    py11 = "".join(f"def m{i}():\n    return {i}\n" for i in range(11))
    if run(write_payload("/tmp/gf/pkg/many.py", py11)) != 2:
        failures.append("11-def Python file should still hard-block")

    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print("ok — god-file cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
