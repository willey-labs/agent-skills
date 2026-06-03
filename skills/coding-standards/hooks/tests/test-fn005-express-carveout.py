#!/usr/bin/env python3
"""Regression test — FN-005 Express error-middleware carve-out.

Express dispatches error middleware by arity: exactly four declared params
(err, req, res, next). The TS hook must exempt that shape — in BOTH its
detection paths (tree-sitter AST and the regex fallback) — while still
blocking every other 4+-positional-arg signature.

Run directly (stdlib only, no test framework):

    python3 hooks/tests/test-fn005-express-carveout.py

Exit 0 = all cases hold; exit 1 = a case regressed (named on stderr).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent.parent
HOOK = HOOKS_DIR / "block-ts-violations.py"

# (case name, file content, expect_block)
END_TO_END_CASES: list[tuple[str, str, bool]] = [
    (
        "typed arrow error middleware with underscored unused params passes",
        "import type { ErrorRequestHandler } from 'express'\n"
        "export const errorHandler: ErrorRequestHandler = (err, _req, res, _next) => {\n"
        "  res.status(500).json({ code: 'INTERNAL_ERROR' })\n"
        "}\n",
        False,
    ),
    (
        "plain function error middleware passes",
        "export function errorHandler(err, req, res, next) {\n"
        "  res.status(500).end()\n"
        "}\n",
        False,
    ),
    (
        "generic 4-arg function still blocks",
        "function notMiddleware(alpha, beta, gamma, delta) {\n  return alpha\n}\n",
        True,
    ),
    (
        "5-arg signature starting like middleware still blocks",
        "function tooMany(err, req, res, next, extra) {\n  return err\n}\n",
        True,
    ),
    (
        "wrong fourth param name still blocks",
        "function notQuite(err, req, res, last) {\n  return err\n}\n",
        True,
    ),
    (
        "object-param escape hatch still passes",
        "function fine({ alpha, beta, gamma, delta }) {\n  return alpha\n}\n",
        False,
    ),
]

# Param-list shapes for the shared helper, exercised directly so the carve-out
# is pinned independently of which detection path ran.
HELPER_CASES: list[tuple[str, str, bool]] = [
    ("canonical names", "(err, req, res, next)", True),
    ("long names with annotations", "(error: unknown, request: Request, response: Response, next: NextFunction)", True),
    ("underscored unused params", "(err, _req, res, _next)", True),
    ("short err alias", "(e, req, res, next)", True),
    ("fifth param breaks the shape", "(err, req, res, next, extra)", False),
    ("wrong order breaks the shape", "(req, err, res, next)", False),
    ("unrelated 4-arg list", "(alpha, beta, gamma, delta)", False),
]


def run_hook(content: str) -> tuple[int, str]:
    payload = json.dumps(
        {
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/tmp/fn005-carveout-check/src/handler.ts",
                "content": content,
            },
        }
    )
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stderr


def load_ts_ast_module():
    spec = importlib.util.spec_from_file_location("_ts_ast", HOOKS_DIR / "_ts_ast.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    failures: list[str] = []

    for name, content, expect_block in END_TO_END_CASES:
        code, stderr = run_hook(content)
        blocked = code == 2 and "FN-005" in stderr
        if blocked != expect_block:
            failures.append(
                f"end-to-end: {name} — expected "
                f"{'block' if expect_block else 'pass'}, got exit {code}: {stderr.strip()}"
            )

    ts_ast = load_ts_ast_module()
    for name, params_text, expect_match in HELPER_CASES:
        if ts_ast.is_express_error_middleware_params(params_text) != expect_match:
            failures.append(f"helper: {name} — `{params_text}` misclassified")

    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1

    total = len(END_TO_END_CASES) + len(HELPER_CASES)
    print(f"ok — {total} FN-005 carve-out cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
