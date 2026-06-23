#!/usr/bin/env python3
"""Canonical source-file extension sets, shared by every hook.

One home for "which extensions are TS/JS/SFC" and "which extensions are source
files the rules apply to" — so the sets can't drift between hooks (ISS-010: some
hooks had `.vue` but not `.svelte`, some had `.swift` but not `.kts`, etc.). Every
hook imports from here instead of carrying its own literal.

Stdlib only; no imports.
"""

from __future__ import annotations

# TS/JS family — parsed by the tree-sitter TS/TSX/JS grammars.
TS_EXTENSIONS = frozenset({".ts", ".tsx", ".mts", ".cts"})
JS_EXTENSIONS = frozenset({".js", ".jsx", ".mjs", ".cjs"})
# Single-file components carrying TS/JS in `<script>` blocks (Vue, Svelte). The
# block-ts hook extracts and AST-checks those blocks; keep the old name too.
SFC_EXTENSIONS = frozenset({".vue", ".svelte"})
VUE_LIKE_EXTENSIONS = SFC_EXTENSIONS  # back-compat alias

# Every source extension the rules apply to, across all covered languages. Used by
# the language-agnostic hooks (ST-005 junk paths, ST-008 god-file). Add a new
# language's extension HERE and every universal hook picks it up at once.
SOURCE_EXTENSIONS = frozenset(
    TS_EXTENSIONS
    | JS_EXTENSIONS
    | SFC_EXTENSIONS
    | {".py", ".pyi", ".go", ".cs", ".java", ".kt", ".kts", ".php", ".rb", ".rs", ".swift"}
)

# Extensions backed by a dedicated content-checking hook (block-<lang>-violations.py).
# Languages in SOURCE_EXTENSIONS but NOT here — Ruby (.rb), Rust (.rs), Swift
# (.swift), v5-unsupported — get only the language-agnostic path check (ST-005) and
# structure check (ST-008). For them ST-008's decl-count is an ADVISORY, not a hard
# block (block-god-file.py), so "unsupported" means uniformly not-hard-blocked rather
# than half-enforced. Add a language's extension here when its content hook ships.
CONTENT_HOOK_EXTENSIONS = frozenset(
    TS_EXTENSIONS
    | JS_EXTENSIONS
    | SFC_EXTENSIONS
    | {".py", ".pyi", ".go", ".cs", ".java", ".kt", ".kts", ".php"}
)
