#!/usr/bin/env python3
"""Regression test — mega-files under app/, and PHP heredoc bodies.

The ST-005 mega-file ban covers `app/` (src-less Next.js) as well as `src/`. PHP
heredoc/nowdoc bodies are string data — `mixed`/Hungarian inside them must not
fire, while the same shapes as real code still block.

    python3 hooks/tests/test-precision-fixes.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from harness import Case, report  # noqa: E402

JUNK = "block-junk-paths.py"
PHP = "block-php-violations.py"

CASES: list[Case] = [
    # Mega-file under app/ and src/ blocks; a real feature file passes.
    Case("app/types.ts mega-file blocks", JUNK, "/t/app/types.ts", "export type X = 1\n", block=True),
    Case("app/constants.ts mega-file blocks", JUNK, "/t/app/constants.ts", "export const X = 1\n", block=True),
    Case("src/types.ts mega-file blocks", JUNK, "/t/src/types.ts", "export type X = 1\n", block=True),
    Case("app/users/profile.ts feature file passes", JUNK, "/t/app/users/profile.ts", "export const x = 1\n", block=False),

    # PHP heredoc body is data (pass); same shape as code blocks.
    Case("php heredoc body passes", PHP, "/t/tpl.php",
         "<?php\n$t = <<<EOT\nfunction f(mixed $strName) {}\nEOT;\n", block=False),
    Case("php real mixed param blocks", PHP, "/t/real.php",
         "<?php\nfunction f(mixed $x) { return $x; }\n", block=True, rule="OD-006"),
    Case("php code after heredoc still blocks", PHP, "/t/after.php",
         "<?php\n$t = <<<EOT\nhello\nEOT;\nfunction g(mixed $x) {}\n", block=True, rule="OD-006"),

    # Star and dot imports cite their rule.
    Case("python star import cites ST-010", "block-py-violations.py", "/t/s.py",
         "from billing.invoice import *\n", block=True, rule="ST-010"),
    Case("kotlin star import cites ST-010", "block-jvm-violations.py", "/t/S.kt",
         "import com.acme.billing.*\n", block=True, rule="ST-010"),
    Case("go dot import cites ST-010", "block-go-violations.py", "/t/s.go",
         "package s\n\nimport . \"fmt\"\n", block=True, rule="ST-010"),
]


if __name__ == "__main__":
    sys.exit(report("precision-fixes", CASES))
