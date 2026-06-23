#!/usr/bin/env python3
"""Regression — idiomatic carve-outs the GAP-002 false-block measurement motivated.

Four changes, each because the rule was hard-blocking idiomatic professional code:

  - Go `interface{}` / `any` is an ADVISORY (exit 0 + stderr), not a hard block —
    it fired on ~60% of idiomatic Go files (gin) in the corpus. Hungarian and
    FN-005 on Go still hard-block.
  - shadcn/ui's `lib/utils.ts` (the cn() helper) is exempt from the ST-005 junk
    filename ban — every other junk `utils.*` / `helpers.*` still blocks.
  - FastAPI route handlers whose return annotation is Any are exempt from OD-006
    (the response_model decorator defines the schema) — a non-route handler and a
    param annotated Any still block.
  - `.NET Common/` folders are exempt from the ST-005 junk-folder ban for `.cs`
    files only — a `common/` folder in a JS/TS project still blocks.

    python3 hooks/tests/test-idiomatic-carveouts.py

Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
GO = "block-go-violations.py"
JUNK = "block-junk-paths.py"
PY = "block-py-violations.py"


def run(hook: str, file_path: str, content: str) -> tuple[int, str]:
    payload = json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}
    )
    proc = subprocess.run(
        [sys.executable, str(HOOKS / hook)], input=payload, capture_output=True, text=True
    )
    return proc.returncode, proc.stderr


def _expect(failures: list[str], name: str, ok: bool) -> None:
    if not ok:
        failures.append(name)


def _check_go(failures: list[str]) -> None:
    code, err = run(GO, "/tmp/cs/handler.go", "package h\n\nvar data map[string]any\n")
    _expect(failures, "go map[string]any not blocked", code != 2)
    _expect(failures, "go map[string]any advised (OD-006)", "OD-006" in err)

    code, err = run(GO, "/tmp/cs/bind.go", "package h\n\nfunc Bind(obj any) {}\n")
    _expect(failures, "go param any not blocked", code != 2)
    _expect(failures, "go param any advised (OD-006)", "OD-006" in err)

    code, _err = run(GO, "/tmp/cs/gen.go", "package h\n\nfunc Map[T any](xs []T) []T { return xs }\n")
    _expect(failures, "go generic [T any] not blocked", code != 2)

    code, err = run(GO, "/tmp/cs/h.go", 'package h\n\nfunc f() {\n\tstrName := "x"\n\t_ = strName\n}\n')
    _expect(failures, "go hungarian still hard-blocks", code == 2 and "NM-006" in err)

    code, err = run(GO, "/tmp/cs/a.go", "package h\n\nfunc F(a, b, c, d int) int { return a }\n")
    _expect(failures, "go 4-param still hard-blocks", code == 2 and "FN-005" in err)

    code, err = run(GO, "/tmp/cs/m.go", 'package h\n\nfunc F(obj any) {\n\tstrName := "x"\n\t_ = strName\n}\n')
    _expect(failures, "go any+hungarian blocks (hard wins)", code == 2 and "NM-006" in err)


def _check_shadcn(failures: list[str]) -> None:
    cn = "export function cn() { return null }\n"
    _expect(failures, "lib/utils.ts exempt", run(JUNK, "/tmp/cs/lib/utils.ts", cn)[0] != 2)
    _expect(failures, "src/lib/utils.ts exempt", run(JUNK, "/tmp/cs/src/lib/utils.ts", cn)[0] != 2)
    _expect(failures, "lib/utils.js exempt", run(JUNK, "/tmp/cs/lib/utils.js", cn)[0] != 2)
    _expect(failures, "src/utils.ts still blocks", run(JUNK, "/tmp/cs/src/utils.ts", cn)[0] == 2)
    _expect(failures, "components/utils.ts still blocks", run(JUNK, "/tmp/cs/src/components/utils.ts", cn)[0] == 2)
    _expect(failures, "lib/helpers.ts still blocks", run(JUNK, "/tmp/cs/lib/helpers.ts", cn)[0] == 2)


def _check_fastapi(failures: list[str]) -> None:
    route = (
        "from fastapi import APIRouter\n"
        "from typing import Any\n\n"
        "router = APIRouter()\n\n\n"
        "@router.get('/items')\n"
        "def read_items() -> Any:\n"
        "    return []\n"
    )
    _expect(failures, "fastapi route return-Any exempt", run(PY, "/tmp/cs/routes.py", route)[0] != 2)

    plain = "from typing import Any\n\n\ndef helper() -> Any:\n    return None\n"
    code, err = run(PY, "/tmp/cs/helper.py", plain)
    _expect(failures, "non-route return-Any still blocks", code == 2 and "OD-006" in err)

    param = (
        "from fastapi import APIRouter\n"
        "from typing import Any\n\n"
        "router = APIRouter()\n\n\n"
        "@router.post('/x')\n"
        "def create(body: Any) -> Any:\n"
        "    return body\n"
    )
    code, err = run(PY, "/tmp/cs/create.py", param)
    _expect(failures, "route param Any still blocks", code == 2 and "OD-006" in err)


def _check_dotnet(failures: list[str]) -> None:
    cs = "namespace App.Common;\n\npublic class Mapper { }\n"
    _expect(failures, "cs Common/ folder exempt",
            run(JUNK, "/tmp/cs/src/Application/Common/Behaviours/Mapper.cs", cs)[0] != 2)
    _expect(failures, "ts common/ folder still blocks",
            run(JUNK, "/tmp/cs/src/common/widget.ts", "export const x = 1\n")[0] == 2)
    _expect(failures, "cs Utils/ folder still blocks",
            run(JUNK, "/tmp/cs/src/Utils/Mapper.cs", cs)[0] == 2)


def main() -> int:
    failures: list[str] = []
    _check_go(failures)
    _check_shadcn(failures)
    _check_fastapi(failures)
    _check_dotnet(failures)
    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print("ok — idiomatic-carveout (Go any / shadcn utils / FastAPI -> Any / .NET Common) cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
