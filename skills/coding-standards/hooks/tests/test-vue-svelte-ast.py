#!/usr/bin/env python3
"""Regression test — AST checks on Vue/Svelte `<script>` blocks (ISS-010).

The hook extracts `<script>` / `<script setup>` from .vue/.svelte SFCs and runs
the tree-sitter AST checks on them, with line numbers aligned to the SFC. This
exercises an AST-ONLY rule (FN-001 function length — no regex fallback), so it
skips loudly when tree-sitter isn't importable (run-all.py then reports DEGRADED).

    <venv-python> hooks/tests/test-vue-svelte-ast.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, run_cases  # noqa: E402

TS = "block-ts-violations.py"

# A 21-statement function body trips FN-001 (cap 20) — AST-only, no regex fallback.
_LONG = "\n".join(f"  const v{i} = {i}" for i in range(21))
LONG_VUE = (
    "<template><div/></template>\n"
    '<script setup lang="ts">\n'
    f"function huge() {{\n{_LONG}\n}}\n"
    "</script>\n"
)
CLEAN_VUE = (
    "<template><div/></template>\n"
    '<script setup lang="ts">\n'
    "const x: number = 1\nfunction ok(a: number) { return a }\n"
    "</script>\n"
)
LONG_SVELTE = '<script lang="ts">\n' + f"function huge() {{\n{_LONG}\n}}\n" + "</script>\n"

CASES = [
    Case("vue long function blocks (FN-001, AST-only)", TS, "/t/A.vue", LONG_VUE, block=True, rule="FN-001"),
    Case("vue clean passes", TS, "/t/B.vue", CLEAN_VUE, block=False),
    Case("svelte long function blocks (FN-001, AST-only)", TS, "/t/C.svelte", LONG_SVELTE, block=True, rule="FN-001"),
]


def main() -> int:
    try:
        import tree_sitter, tree_sitter_typescript  # noqa: F401
    except Exception:  # noqa: BLE001
        sys.stderr.write("SKIP vue-svelte-ast: tree-sitter not importable here "
                         "(run with the venv python); run-all.py reports DEGRADED.\n")
        return 0
    failures = run_cases(CASES)
    if failures:
        for f in failures:
            sys.stderr.write(f"FAIL {f}\n")
        return 1
    print(f"ok — {len(CASES)} vue-svelte-ast cases hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
