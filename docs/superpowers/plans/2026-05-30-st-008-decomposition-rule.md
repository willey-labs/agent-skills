# ST-008 Decomposition Rule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a language-agnostic structural rule (ST-008) that prevents god-files, make DP-002's Strategy guidance self-detectable, enforce it with a soft-warning hook that fires even in fast/single-agent mode, and de-bias `common/structure.md` so the new rule lands in a genuinely common file.

**Architecture:** Five threads — (1) a new `ST-008` rule in `common/structure.md`; (2) a detectable trigger appended to `DP-002` in `common/code-principles.md`; (3) a new stdlib-only PreToolUse hook `hooks/warn-god-file.py` that warns (exit 0 + stderr) when a non-test/non-schema source file crosses a tunable threshold, wired into `_structure.py`, `bootstrap.py`, `review-files.py`, and `hooks/README.md`; (4) de-biasing `common/structure.md` (ST-001/ST-006/ST-007) by trimming framework specifics already covered downstream; (5) updating `worker-1-structure.md` and `SKILL.md`.

**Tech Stack:** Python 3 (stdlib only) for the hook; Markdown for the rule references. The repo dogfoods its own hooks, so all edits must themselves pass the hooks.

**Spec:** `docs/superpowers/specs/2026-05-30-st008-decomposition-and-debias-design.md`

**Branch:** `feat/st-008-decomposition-rule` (already created and checked out).

**Skill dir (all relative paths below are under this):** `skills/coding-standards/`

---

## Conventions for this plan

- **Hook test harness.** This repo tests hooks by piping a PreToolUse JSON payload to stdin and asserting on exit code + stderr (see `AGENTS.md` → "Testing the hooks"). There is no pytest suite; tests are bash one-liners. **Never run against `~/.claude`** — the hook itself is read-only on settings, but `bootstrap.py` is not; the bootstrap test (Task 11) uses the sandbox pattern from `AGENTS.md`.
- **Default threshold:** 400 lines OR 10 top-level declarations. Either crossing fires the warning.
- **Commit after each task.** Conventional-style subjects.

---

## Task 1: Threshold + enable config in `_structure.py`

The hook needs to read `god-file` on/off plus numeric overrides from `.coding-standards-structure`. Extend the existing toggle reader (do not add a YAML dep — keep the flat line-scan).

**Files:**
- Modify: `skills/coding-standards/hooks/_structure.py`

- [ ] **Step 1: Write the failing test**

Create a scratch structure file and probe the new function:

```bash
cd skills/coding-standards/hooks
SANDBOX=$(mktemp -d)
printf 'variant: current\nhooks:\n  god-file: off\n  god-file-max-lines: 600\n' > "$SANDBOX/.coding-standards-structure"
touch "$SANDBOX/.git"  # project-root marker
python3 - "$SANDBOX/src/a.ts" <<'PY'
import sys
from _structure import load_god_file_config, is_check_enabled
fp = sys.argv[1]
cfg = load_god_file_config(fp)
print("enabled", cfg["enabled"], "max_lines", cfg["max_lines"], "max_decls", cfg["max_decls"])
assert cfg["enabled"] is False, "god-file: off should disable"
assert cfg["max_lines"] == 600, "override not read"
assert cfg["max_decls"] == 10, "default decls expected"
print("OK")
PY
rm -rf "$SANDBOX"
```

Run it.
Expected: FAIL — `ImportError: cannot import name 'load_god_file_config'`.

- [ ] **Step 2: Implement the config reader**

In `skills/coding-standards/hooks/_structure.py`, add `god-file` to the on/off key set and add a numeric parser. Replace the `_TOGGLE_LINE` definition (lines ~41-45) with:

```python
_TOGGLE_LINE = re.compile(
    r"^\s*(deep-import|junk-drawer|tests-colocated|god-file)\s*:\s*"
    r"(on|off|true|false|yes|no|enable|enabled|disable|disabled)\s*$",
    re.IGNORECASE,
)

# ST-008 numeric overrides, e.g. `  god-file-max-lines: 600`.
_GOD_FILE_NUM_LINE = re.compile(
    r"^\s*(god-file-max-lines|god-file-max-decls)\s*:\s*(\d+)\s*$",
    re.IGNORECASE,
)

GOD_FILE_DEFAULT_MAX_LINES = 400
GOD_FILE_DEFAULT_MAX_DECLS = 10
```

Then append this function at the end of the file:

```python
def load_god_file_config(file_path: str) -> dict[str, object]:
    """ST-008 soft-warning config for the project owning `file_path`.

    Returns {"enabled": bool, "max_lines": int, "max_decls": int}. Defaults:
    enabled True (warn), 400 lines, 10 top-level declarations. Only an explicit
    `god-file: off` disables; numeric keys override the thresholds.
    """
    enabled = is_check_enabled("god-file", file_path)
    max_lines = GOD_FILE_DEFAULT_MAX_LINES
    max_decls = GOD_FILE_DEFAULT_MAX_DECLS
    root = find_project_root(Path(file_path))
    if root is not None:
        structure_file = root / STRUCTURE_FILENAME
        if structure_file.exists():
            try:
                for line in structure_file.read_text(encoding="utf-8").splitlines():
                    m = _GOD_FILE_NUM_LINE.match(line)
                    if not m:
                        continue
                    key, value = m.group(1).lower(), int(m.group(2))
                    if key == "god-file-max-lines":
                        max_lines = value
                    elif key == "god-file-max-decls":
                        max_decls = value
            except (OSError, UnicodeDecodeError, ValueError):
                pass
    return {"enabled": enabled, "max_lines": max_lines, "max_decls": max_decls}
```

- [ ] **Step 3: Run the test to verify it passes**

Run the Step 1 block again.
Expected: prints `enabled False max_lines 600 max_decls 10` then `OK`.

- [ ] **Step 4: Verify default (no structure file) path**

```bash
cd skills/coding-standards/hooks
python3 - "/tmp/no-such-project/src/a.ts" <<'PY'
from _structure import load_god_file_config
cfg = load_god_file_config("/tmp/no-such-project/src/a.ts")
assert cfg == {"enabled": True, "max_lines": 400, "max_decls": 10}, cfg
print("OK defaults")
PY
```
Expected: `OK defaults`.

- [ ] **Step 5: Commit**

```bash
git add skills/coding-standards/hooks/_structure.py
git commit -m "add ST-008 god-file threshold config to _structure.py"
```

---

## Task 2: The `warn-god-file.py` hook

A PreToolUse hook that warns (never blocks) when a non-test/non-schema, non-generated, non-excluded source file crosses the threshold. Always exits 0.

**Files:**
- Create: `skills/coding-standards/hooks/warn-god-file.py`

- [ ] **Step 1: Write the failing test (over-threshold file warns)**

```bash
cd skills/coding-standards/hooks
python3 - <<'PY'
import json, subprocess, sys
content = "\n".join(f"const x{i} = {i};" for i in range(450))  # 450 lines, 450 decls
payload = json.dumps({"tool_name": "Write",
                      "tool_input": {"file_path": "/tmp/proj/src/big.ts", "content": content}})
p = subprocess.run([sys.executable, "warn-god-file.py"], input=payload,
                   capture_output=True, text=True)
print("exit", p.returncode)
print("stderr:", p.stderr.strip()[:200])
assert p.returncode == 0, "must never block"
assert "ST-008" in p.stderr, "should warn"
print("OK")
PY
```
Run it.
Expected: FAIL — `No such file or directory: 'warn-god-file.py'`.

- [ ] **Step 2: Implement the hook**

Create `skills/coding-standards/hooks/warn-god-file.py`:

```python
#!/usr/bin/env python3
"""PreToolUse hook — ST-008 god-file soft warning.

Warns (stderr, exit 0 — NEVER blocks) when a Write/Edit targets a source file
that has grown past the project threshold (default 400 lines / 10 top-level
declarations), which usually means it holds more than one responsibility and
should be split into named sibling units. See references/common/structure.md#st-008.

This is a WARNING, not a block: a raw line/declaration count has a false-positive
rate well above the ~1% bar AGENTS.md sets for hard blocks (large test files,
schema/DTO files, lookup tables). So it nudges on the write path that fast/
single-agent mode would otherwise skip, without fighting legitimate large files.

Skips: excluded paths (node_modules, generated, ...), generated-marker files,
and test/schema/fixture/story files (any language). Reads the threshold +
on/off from .coding-standards-structure via _structure.py. Stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _exclusions import is_excluded_path, has_generation_marker  # noqa: E402
from _structure import load_god_file_config  # noqa: E402

# Source extensions this rule applies to (mirrors block-junk-paths.py's set).
SOURCE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mts", ".cts", ".mjs", ".cjs",
    ".py", ".go", ".cs", ".java", ".kt", ".php", ".rb", ".rs", ".vue", ".swift",
}

# Test / schema / fixture / story files — legitimately large, never warned.
# Matched against the filename (lowercased), language-agnostic.
EXEMPT_NAME_PATTERNS = (
    re.compile(r"\.test\."), re.compile(r"\.spec\."),
    re.compile(r"_test\.(py|go)$"), re.compile(r"^test_.*\.py$"),
    re.compile(r"(test|tests)\.(java|kt|cs)$"),   # FooTest.java, FooTests.cs
    re.compile(r"\.schema\."), re.compile(r"-schema(s)?\."),
    re.compile(r"\.fixtures?\."), re.compile(r"\.stories\."),
    re.compile(r"\.e2e\."),
)

# A top-level declaration: a declaration keyword at column 0 (no indent). Broad
# on purpose — it's a warning heuristic, not a gate.
_DECL_LINE = re.compile(
    r"^(export\s+)?(default\s+)?(public\s+|private\s+|protected\s+|internal\s+|"
    r"abstract\s+|static\s+|final\s+|async\s+)*"
    r"(function|class|interface|type|enum|struct|const|let|var|def|func|trait|impl|protocol)\b"
)


def is_exempt_name(file_path: str) -> bool:
    name = Path(file_path).name.lower()
    return any(p.search(name) for p in EXEMPT_NAME_PATTERNS)


def count_top_level_decls(content: str) -> int:
    return sum(1 for line in content.splitlines() if _DECL_LINE.match(line))


def assess(file_path: str, content: str) -> str | None:
    """Return a warning message if the file is over threshold, else None."""
    cfg = load_god_file_config(file_path)
    if not cfg["enabled"]:
        return None
    line_count = content.count("\n") + 1 if content else 0
    decl_count = count_top_level_decls(content)
    over_lines = line_count > cfg["max_lines"]
    over_decls = decl_count > cfg["max_decls"]
    if not (over_lines or over_decls):
        return None
    reasons = []
    if over_lines:
        reasons.append(f"{line_count} lines (> {cfg['max_lines']})")
    if over_decls:
        reasons.append(f"{decl_count} top-level declarations (> {cfg['max_decls']})")
    return (
        f"{file_path} — ST-008: {', '.join(reasons)}. This file likely holds more "
        f"than one responsibility — consider splitting it into named sibling units "
        f"(see references/common/structure.md#st-008). "
        f"Tune or disable via .coding-standards-structure (god-file / god-file-max-lines)."
    )


def main() -> int:
    raw = sys.stdin.read()
    if not raw.strip():
        return 0
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name", "") not in {"Write", "Edit", "MultiEdit"}:
        return 0
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")
    if not file_path or Path(file_path).suffix.lower() not in SOURCE_EXTS:
        return 0
    if is_exempt_name(file_path):
        return 0

    excluded, _ = is_excluded_path(file_path)
    if excluded:
        return 0

    # For Edit/MultiEdit the full new content isn't in the payload; fall back to
    # the post-edit file on disk if present, else the provided content/new_string.
    content = tool_input.get("content")
    if content is None:
        try:
            content = Path(file_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return 0
    if has_generation_marker(content):
        return 0

    message = assess(file_path, content)
    if message:
        sys.stderr.write(
            "coding-standards (advisory — not blocked):\n  - " + message + "\n"
        )
    return 0  # ALWAYS 0 — advisory only.


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Run the Step 1 test to verify it passes**

Expected: `exit 0`, stderr contains `ST-008`, prints `OK`.

- [ ] **Step 4: Test the exemptions (must stay silent)**

```bash
cd skills/coding-standards/hooks
python3 - <<'PY'
import json, subprocess, sys
big = "\n".join(f"const x{i} = {i};" for i in range(450))
cases = {
    "/tmp/proj/src/big.test.ts": "test file",
    "/tmp/proj/src/user.schema.ts": "schema file",
    "/tmp/proj/node_modules/pkg/big.ts": "excluded",
    "/tmp/proj/src/small.ts": "under threshold",  # uses small content below
}
def run(fp, content):
    payload = json.dumps({"tool_name":"Write","tool_input":{"file_path":fp,"content":content}})
    p = subprocess.run([sys.executable,"warn-god-file.py"],input=payload,capture_output=True,text=True)
    return p.returncode, p.stderr.strip()
for fp, label in cases.items():
    content = "const a = 1;" if "small" in fp else big
    code, err = run(fp, content)
    assert code == 0, (fp, code)
    assert err == "", f"{label} should be silent, got: {err}"
print("OK all exemptions silent")
PY
```
Expected: `OK all exemptions silent`.

- [ ] **Step 5: Test the `god-file: off` toggle**

```bash
cd skills/coding-standards/hooks
SANDBOX=$(mktemp -d); touch "$SANDBOX/.git"
printf 'hooks:\n  god-file: off\n' > "$SANDBOX/.coding-standards-structure"
python3 - "$SANDBOX" <<'PY'
import json, subprocess, sys, os
root = sys.argv[1]
fp = os.path.join(root, "src", "big.ts")
big = "\n".join(f"const x{i} = {i};" for i in range(450))
payload = json.dumps({"tool_name":"Write","tool_input":{"file_path":fp,"content":big}})
p = subprocess.run([sys.executable,"warn-god-file.py"],input=payload,capture_output=True,text=True)
assert p.returncode == 0 and p.stderr.strip() == "", f"off should silence, got: {p.stderr}"
print("OK off silences")
PY
rm -rf "$SANDBOX"
```
Expected: `OK off silences`.

- [ ] **Step 6: Commit**

```bash
git add skills/coding-standards/hooks/warn-god-file.py
git commit -m "add warn-god-file.py — ST-008 soft-warning hook"
```

---

## Task 3: Register the hook in `bootstrap.py`

So a fresh install wires it as a PreToolUse hook alongside the blockers.

**Files:**
- Modify: `skills/coding-standards/bootstrap.py` (the `HOOK_FILES` list, ~line 71)

- [ ] **Step 1: Add the hook to the list**

In `skills/coding-standards/bootstrap.py`, append to `HOOK_FILES`:

```python
HOOK_FILES = [
    "block-junk-paths.py",
    "block-ts-violations.py",
    "block-py-violations.py",
    "block-go-violations.py",
    "block-csharp-violations.py",
    "block-php-violations.py",
    "block-jvm-violations.py",
    "warn-god-file.py",
]
```

- [ ] **Step 2: Verify the generated command block includes it (sandbox)**

```bash
REPO=$(git rev-parse --show-toplevel)
SANDBOX=$(mktemp -d); export HOME="$SANDBOX/home"
mkdir -p "$HOME/.claude/skills"
ln -sf "$REPO/skills/coding-standards" "$HOME/.claude/skills/coding-standards"
python3 "$HOME/.claude/skills/coding-standards/bootstrap.py" --auto-install >/dev/null 2>&1
grep -q "warn-god-file.py" "$HOME/.claude/settings.json" && echo "OK registered" || echo "MISSING"
rm -rf "$SANDBOX"; unset HOME
```
Expected: `OK registered`. (If `HOME` unset misbehaves in your shell, open a new shell; never run without the `HOME` override.)

- [ ] **Step 3: Commit**

```bash
git add skills/coding-standards/bootstrap.py
git commit -m "register warn-god-file.py in bootstrap HOOK_FILES"
```

---

## Task 4: Surface the warning in `review-files.py`

The review linter currently keeps only exit-2 findings. The warning hook exits 0, so add it as a separate, clearly-labelled "advisory" stream — not a must-fix.

**Files:**
- Modify: `skills/coding-standards/hooks/review-files.py`

- [ ] **Step 1: Write the failing test**

```bash
cd skills/coding-standards/hooks
BIG=$(mktemp --suffix=.ts); python3 -c "print('\n'.join(f'const x{i}={i};' for i in range(450)))" > "$BIG"
python3 review-files.py --json "$BIG" | python3 -c "import json,sys; d=json.load(sys.stdin); print('ADVISORY' if any('ST-008' in v for vs in d.values() for v in (vs if isinstance(vs,list) else [])) else 'NONE')"
rm -f "$BIG"
```
Run it.
Expected: currently `NONE` (the review driver ignores the exit-0 warning). After the change: `ADVISORY`.

- [ ] **Step 2: Implement — run the warn hook separately and capture its stderr**

In `skills/coding-standards/hooks/review-files.py`, add the warn hook name as a constant after `HOOK_FILES` (it must NOT be in `HOOK_FILES`, which is gated on exit 2):

```python
WARN_HOOKS = ("warn-god-file.py",)
```

Then, inside `check_file`, after the existing `for hook in HOOK_FILES:` loop and before `return violations`, add:

```python
    # Advisory hooks exit 0 and write to stderr regardless. Capture them as
    # warnings, tagged so the merge step files them as should-fix, not must-fix.
    for hook in WARN_HOOKS:
        proc = subprocess.run(
            [sys.executable, str(HOOK_DIR / hook)],
            input=payload,
            capture_output=True,
            text=True,
        )
        if proc.stderr.strip():
            for line in proc.stderr.splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    violations.append("[advisory] " + stripped[2:].strip())
    return violations
```

- [ ] **Step 3: Run the Step 1 test to verify it passes**

Expected: `ADVISORY`.

- [ ] **Step 4: Verify a clean small file still reports clean**

```bash
cd skills/coding-standards/hooks
SMALL=$(mktemp --suffix=.ts); printf 'export const a = 1;\n' > "$SMALL"
python3 review-files.py "$SMALL" | grep -q "clean" && echo "OK clean" || echo "FAIL"
rm -f "$SMALL"
```
Expected: `OK clean`.

- [ ] **Step 5: Commit**

```bash
git add skills/coding-standards/hooks/review-files.py
git commit -m "review-files.py: surface ST-008 advisory warnings"
```

---

## Task 5: Add ST-008 to `common/structure.md`

**Files:**
- Modify: `skills/coding-standards/references/common/structure.md` (insert after ST-007, before "How framework files extend this"; update the review checklist)

- [ ] **Step 1: Insert the rule**

After the ST-007 section and before `## How framework files extend this`, insert:

````markdown
---

## ST-008 — One file, one responsibility; grow folders by tier, not by accretion

Source is organized in four tiers: **Domain → Feature → Sub-feature → Unit**.

| Tier | Also called | What it is |
|---|---|---|
| Domain | Bounded Context, Capability | A top-level area of *what the product does* (ST-001) |
| Feature | Feature Module, Vertical Slice | A cohesive capability inside the domain |
| Sub-feature | Component, Concern | A distinct piece inside a feature (a folder once it earns 2+ files) |
| Unit | Module file | One responsibility, one file |

A *unit* (one file) has **one reason to change**. ST-005 governs a file's *name*;
ST-008 governs its *scope*. A file can have a perfect name and still be wrong — if
`payment.ts` parses input, talks to a gateway, and writes the ledger, it is three
units wearing one filename.

**The smell:** a well-named file that grows by accretion — it passes ST-005 (the
name is fine) but does several unrelated things.

**Detectable trigger — check before every write:**
- the file exceeds the project threshold (default ~400 lines / ~10 top-level
  declarations — tunable in `.coding-standards-structure`), **or**
- it holds 2+ unrelated responsibility clusters (e.g. a state machine *and* regex
  parsers *and* file I/O), **or**
- you are about to *add* a concern to a file that already owns a different one.

**Then:** extract the new concern into a named sibling unit. When three siblings
share a theme, promote them to a sub-feature folder with its own `index` (Rule of
Three, ST-004). **Never create a folder for a single file**, and if a feature has a
handful of flat units, stop at the feature tier — a sub-feature folder there is
over-engineering (DP-006 KISS).

**Worked example — a unit doing three things splits into siblings:**

```
# Before — one unit, three responsibilities
billing/
  invoice.ts        ← parses requests + computes totals + persists rows
  index.ts

# After — one responsibility per unit, same public door
billing/
  parse-invoice-request.ts   ← input parsing
  invoice.ts                 ← the orchestrator (compute + coordinate)
  invoice-store.ts           ← persistence
  index.ts                   ← still the only public entry (ST-002)
```

The behavioral companion is **DP-002** (extract an abstraction when you have 2+
variants of a behavior) — structure splits *responsibilities*; DP-002 splits
*variants*.

> **Enforcement note:** the `warn-god-file.py` hook emits an *advisory* warning at
> write time when a file crosses the threshold (it never blocks — a raw size count
> has too high a false-positive rate to gate on). The judgement parts of this rule
> (responsibility clusters) are checked by Worker 1 and in Review mode.
````

- [ ] **Step 2: Update the review checklist**

In the `## Review checklist` block at the end of the file, under "Per folder" (or add a new group), add these lines:

```
File scope (ST-008)
  □ No unit holds 2+ unrelated responsibilities (god-file)
  □ Oversized files (advisory warn-god-file threshold) are split into named siblings
  □ Sub-feature folders are earned (2+ cohesive files), not created for symmetry
```

- [ ] **Step 3: Verify the file still passes its own hooks**

```bash
cd skills/coding-standards
python3 hooks/review-files.py references/common/structure.md
```
Expected: `clean` (markdown isn't a source ext; the run should report no violations).

- [ ] **Step 4: Commit**

```bash
git add skills/coding-standards/references/common/structure.md
git commit -m "add ST-008 (tier decomposition, no god-files) to common/structure.md"
```

---

## Task 6: Add the Strategy trigger to DP-002

**Files:**
- Modify: `skills/coding-standards/references/common/code-principles.md` (DP-002, after the `**How:**` line ~36)

- [ ] **Step 1: Insert the trigger**

Immediately after the `**How:** extract an interface ...` line in DP-002 and before the `---`, add:

```markdown
**Detectable trigger:** you have written 2+ branches switching on a `type` / `kind`
/ `mode` string, **or** 2+ sibling types named `XHandler` / `XStrategy` /
`XProvider`. That is a Strategy. Define one abstraction; each variant implements it
(this rule + DP-003 LSP + DP-005 DIP); callers depend on the abstraction; adding a
variant adds a file and edits nothing. If the variants don't all share every method,
split the abstraction into capability/role interfaces (DP-004 ISP). This is the
behavioral companion to ST-008: ST-008 splits *responsibilities* into sibling units;
DP-002 splits *variants* behind one interface.
```

- [ ] **Step 2: Commit**

```bash
git add skills/coding-standards/references/common/code-principles.md
git commit -m "DP-002: add detectable Strategy trigger"
```

---

## Task 7: De-bias ST-001 (move the Laravel carve-out out of common)

`laravel/structure.md` already owns the full exception (`LRV-001` + the "Builds on … with a named exception" note). The common file's embedded Laravel paragraph is duplication — trim it to a neutral pointer.

**Files:**
- Modify: `skills/coding-standards/references/common/structure.md` (ST-001, ~line 23)

- [ ] **Step 1: Confirm Laravel already documents the exception**

```bash
cd skills/coding-standards
grep -n "named exception" references/laravel/structure.md
```
Expected: a match (line ~19 and `LRV-001`). If absent, STOP and add it to `laravel/structure.md` before trimming common.

- [ ] **Step 2: Replace the Laravel-specific paragraph with a neutral pointer**

In `references/common/structure.md`, replace the `**The named exception** is Laravel — …` paragraph (the one naming `Http/`, `Models/`, `Providers/`) with:

```markdown
**Framework exceptions live in the framework file, not here.** A framework whose
stock skeleton legitimately puts technical folders at the top (the clearest case is
Laravel's `app/Http/`, `app/Models/`) declares that carve-out in its own
`references/<framework>/structure.md` under "Builds on `common/structure.md`". The
universal rule is stated here; the exceptions are named there.
```

- [ ] **Step 3: Verify no framework name beyond a single illustrative mention remains baked into the rule body**

```bash
cd skills/coding-standards
grep -nc "Laravel" references/common/structure.md
```
Expected: `1` (the single illustrative mention in the pointer above). If higher, trim the extras.

- [ ] **Step 4: Commit**

```bash
git add skills/coding-standards/references/common/structure.md
git commit -m "de-bias ST-001: move Laravel carve-out to laravel/structure.md"
```

---

## Task 8: De-bias ST-006 (generalize; keep the UI example in framework files)

`nextjs`, `react-native`, and `vue-nuxt` already state "generic names at the design-system layer" and carry the `Card`/`Modal`/`Button` examples. Generalize ST-006 in common so the principle is language-neutral, and confirm the concrete UI tree lives downstream.

**Files:**
- Modify: `skills/coding-standards/references/common/structure.md` (ST-006, ~lines 130-153)
- Verify (no edit unless a gap is found): `references/nextjs/structure.md`, `references/react-native/structure.md`, `references/vue-nuxt/structure.md`

- [ ] **Step 1: Confirm the downstream files carry the concrete example**

```bash
cd skills/coding-standards
grep -lni "design.system" references/nextjs/structure.md references/react-native/structure.md references/vue-nuxt/structure.md
grep -ni "Card\|Modal" references/react-native/structure.md | head -3
```
Expected: all three files listed; React Native shows the `Card`/`Modal` generic-name rule. If any framework lacks a design-system statement, add a one-line one there before trimming common.

- [ ] **Step 2: Rewrite ST-006 to be language-neutral**

Replace the React-specific worked example block in ST-006 (the `src/ shared/ui/ Card.tsx …` tree and the `.tsx` prose) with a neutral statement plus a pointer. Keep the type-level example (`Repository<T>`, `BaseEntity`) — it's already language-neutral. The section should read (principle first):

```markdown
A name like `Card`, `Modal`, `Button`, `Selector`, `Repository<T>`, `BaseEntity` is
too generic to mean anything about the business. Generic names belong **only at the
shared / design-system layer**; capability code uses domain-qualified names
(`AppointmentCard`, `OrderRepository`, `PrescriptionDoseEditor`).

This holds in every language and applies to both UI components and types:
- a generic UI primitive (`Button`, `Modal`) lives in the project's design-system
  folder, never inside a capability;
- `Repository<T>` (one generic interface every capability implements) is a smell —
  repositories should be capability-shaped (`OrderRepository`) with domain methods;
- a `BaseEntity` parent every entity extends is usually a shared ID/timestamp shape
  better expressed as a mixin than a parent.

**The design-system folder's name and the file extensions are framework-specific**
(`shared/ui/` and `.tsx` for Next.js/React Native, `components/ui/` with `.vue` for
Nuxt). Each `references/<framework>/structure.md` shows the concrete layout; this
rule states only the principle.
```

- [ ] **Step 3: Verify**

```bash
cd skills/coding-standards
grep -nc "\.tsx" references/common/structure.md
```
Expected: `1` (only the single illustrative mention in the pointer). The `shared/ui/` tree example should be gone from common.

- [ ] **Step 4: Commit**

```bash
git add skills/coding-standards/references/common/structure.md
git commit -m "de-bias ST-006: state principle language-neutrally, UI example stays in framework files"
```

---

## Task 9: De-bias ST-007 (neutral co-location, multi-language)

**Files:**
- Modify: `skills/coding-standards/references/common/structure.md` (ST-007, ~lines 157-175)

- [ ] **Step 1: Generalize the suffix list**

In ST-007, replace the TS-only trailing paragraph (`The same applies to .types.ts, .styles.ts, .stories.tsx …`) with a multi-language statement:

```markdown
The same applies to every artifact that exists *because of* a source file —
co-locate it. The concrete suffixes are language/framework-specific and documented
in the framework files: TS uses `.test.ts` / `.types.ts` / `.stories.tsx`; Python
uses `test_*.py` next to the module; Go uses `*_test.go` in the same package; C#
uses `*Tests.cs`. The rule is the same everywhere: the artifact lives next to what
it describes, never in a parallel mirror tree.
```

- [ ] **Step 2: Verify the existing TS tree example near the top of ST-007 is kept as one illustration**

The `checkout/ … Checkout.test.ts` tree at the top of ST-007 is fine as a single concrete illustration (ST-005 already shows multiple languages). Leave it. Just confirm the file still reads coherently:

```bash
cd skills/coding-standards
sed -n '/## ST-007/,/## ST-008/p' references/common/structure.md | head -40
```
Expected: ST-007 reads principle → one illustration → neutral multi-language note.

- [ ] **Step 3: Commit**

```bash
git add skills/coding-standards/references/common/structure.md
git commit -m "de-bias ST-007: multi-language co-location, suffixes deferred to framework files"
```

---

## Task 10: Wire ST-008 into Worker 1

**Files:**
- Modify: `skills/coding-standards/workers/worker-1-structure.md`

- [ ] **Step 1: Add ST-008 to `owns_rules`**

In the frontmatter `owns_rules` list, add `- ST-008` after `- ST-007`.

- [ ] **Step 2: Update the references-to-load line**

Change reference #1 from `references/common/structure.md — your primary rule set (ST-001 to ST-007).` to `… (ST-001 to ST-008).`

- [ ] **Step 3: Add the decomposition check to the write-mode process**

In the `## Process (write mode)` list, extend step 2 ("Decide file paths") with a sub-bullet, and add a new check to step 3:

Append to step 2:
```markdown
   - **ST-008 (no god-files):** for each artifact, if it would hold 2+ unrelated
     responsibilities, plan it as multiple named sibling units up front. Promote a
     group of 3+ related units to a sub-feature folder; never make a folder for one
     file. Stop at the feature tier when a handful of flat units suffice (KISS).
```

Add to step 3 (class/module shape), after the SRP bullet:
```markdown
   - Does any single file accrete more than one responsibility (DP-001 / ST-008)?
     If so, split it into sibling units behind the same `index`.
```

- [ ] **Step 4: Add ST-008 to the review-mode rule coverage**

In the review-mode section, wherever owned ST rules are enumerated for the "every rule appears in passed/findings/skipped" invariant, ensure `ST-008` is included so a review accounts for it explicitly.

```bash
cd skills/coding-standards
grep -n "ST-007" workers/worker-1-structure.md
```
Expected: confirm each place that lists `ST-007` for coverage now also has `ST-008` (frontmatter, references line, and any review-coverage enumeration).

- [ ] **Step 5: Commit**

```bash
git add skills/coding-standards/workers/worker-1-structure.md
git commit -m "worker-1: own and enforce ST-008"
```

---

## Task 11: Update SKILL.md, hooks/README.md, and the structure-file template

**Files:**
- Modify: `skills/coding-standards/SKILL.md`
- Modify: `skills/coding-standards/hooks/README.md`
- Modify: `skills/coding-standards/bootstrap.py` (the seeded `.coding-standards-structure` template, if it documents hook toggles)

- [ ] **Step 1: Reference ST-008 in SKILL.md**

In SKILL.md's Step 2 summary of `common/structure.md` (it currently says "no junk-drawer files"), add "no god-files (ST-008)" to that parenthetical, and in the "What this skill explicitly does NOT cover" / hooks discussion note that `warn-god-file.py` is advisory (warns, never blocks).

```bash
cd skills/coding-standards
grep -n "junk-drawer files" SKILL.md
```
Edit the matching summary line to include `, no god-files`.

- [ ] **Step 2: Document the hook in hooks/README.md**

Add a row/entry for `warn-god-file.py` describing: ST-008 advisory; warns (exit 0 + stderr); skips test/schema/generated/excluded; reads `god-file*` keys from `.coding-standards-structure`. Update any coverage table and the hook count (it was "7 PreToolUse hooks" → now 8, with the note that the 8th is advisory not blocking).

```bash
cd skills/coding-standards
grep -niE "7 (PreToolUse )?hooks|block-jvm-violations" hooks/README.md
```
Update the count and add the new hook beneath the blockers, clearly marked **advisory**.

- [ ] **Step 3: Document the toggle in the seeded structure template**

Find where `bootstrap.py` seeds the commented `.coding-standards-structure` template (search for `junk-drawer` or `deep-import` in bootstrap.py). Add commented lines:

```
#   god-file: off            # ST-008 — silence the god-file size advisory
#   god-file-max-lines: 600  # raise the advisory line threshold (default 400)
#   god-file-max-decls: 15   # raise the top-level-declaration threshold (default 10)
```

```bash
cd skills/coding-standards
grep -n "junk-drawer" bootstrap.py
```
If the template lives in a separate file rather than bootstrap.py, edit that file instead (follow the grep).

- [ ] **Step 4: Update AGENTS.md repo-doc count if it cites the number of hooks**

```bash
REPO=$(git rev-parse --show-toplevel)
grep -niE "7 PreToolUse hooks|1 path-checker \+ 6" "$REPO/AGENTS.md"
```
If matched, update to reflect the new advisory hook (e.g. "8 PreToolUse hooks (1 path-checker + 6 language content-checkers + 1 advisory size-checker)").

- [ ] **Step 5: Commit**

```bash
git add skills/coding-standards/SKILL.md skills/coding-standards/hooks/README.md skills/coding-standards/bootstrap.py
REPO=$(git rev-parse --show-toplevel); git add "$REPO/AGENTS.md" 2>/dev/null || true
git commit -m "docs: document ST-008 + warn-god-file.py advisory hook"
```

---

## Task 12: Full dogfood + bootstrap regression + final verification

**Files:** none (verification only)

- [ ] **Step 1: Run the review linter over every file this plan touched**

```bash
cd skills/coding-standards
python3 hooks/review-files.py \
  hooks/warn-god-file.py hooks/_structure.py hooks/review-files.py bootstrap.py \
  references/common/structure.md references/common/code-principles.md \
  workers/worker-1-structure.md SKILL.md
```
Expected: no must-fix violations. (`warn-god-file.py` itself should be under threshold — if its own advisory fires on it, split it; that's the dogfood rule.)

- [ ] **Step 2: Confirm the new hook does not flag its own source**

```bash
cd skills/coding-standards/hooks
python3 - <<'PY'
import json, subprocess, sys
content = open("warn-god-file.py").read()
payload = json.dumps({"tool_name":"Write","tool_input":{"file_path":"warn-god-file.py","content":content}})
p = subprocess.run([sys.executable,"warn-god-file.py"],input=payload,capture_output=True,text=True)
print("self-advisory:", p.stderr.strip() or "(none)")
assert p.returncode == 0
PY
```
Expected: `self-advisory: (none)` (the hook is well under 400 lines).

- [ ] **Step 3: Bootstrap 6-test matrix (sandbox — never touch ~/.claude)**

Run the `AGENTS.md` bootstrap matrix in a sandbox to confirm registration didn't regress scope detection:

```bash
REPO=$(git rev-parse --show-toplevel)
SANDBOX=$(mktemp -d); export HOME="$SANDBOX/home"
mkdir -p "$HOME/.claude/skills"
ln -sf "$REPO/skills/coding-standards" "$HOME/.claude/skills/coding-standards"
# Test 4 (global install) — wires with absolute paths incl. the new hook:
python3 "$HOME/.claude/skills/coding-standards/bootstrap.py" --auto-install
grep -q "warn-god-file.py" "$HOME/.claude/settings.json" && echo "T4 OK"
# Test 2 (re-run is noop):
python3 "$HOME/.claude/skills/coding-standards/bootstrap.py" --auto-install | grep -qiE "noop|no change|already" && echo "T2 OK" || echo "T2 check output"
rm -rf "$SANDBOX"; unset HOME
```
Expected: `T4 OK` and `T2 OK`. If your shell can't unset `HOME` cleanly, run this in a subshell. Run the remaining matrix cases (3, 5, 6) per `AGENTS.md` if scope-detection code was touched — it was not in this plan, so 2 and 4 suffice as the smoke test.

- [ ] **Step 4: Spec coverage check**

```bash
cd skills/coding-standards
echo "ST-008:";        grep -l "ST-008" references/common/structure.md workers/worker-1-structure.md SKILL.md
echo "DP-002 trigger:"; grep -l "Detectable trigger" references/common/code-principles.md
echo "hook:";          ls hooks/warn-god-file.py && grep -l "warn-god-file" bootstrap.py hooks/review-files.py hooks/README.md
echo "de-bias:";       echo "Laravel in common = $(grep -c Laravel references/common/structure.md) (expect 1); .tsx in common = $(grep -c '\.tsx' references/common/structure.md) (expect 1)"
```
Expected: every artifact present; de-bias counts at 1 each.

- [ ] **Step 5: Final branch state**

```bash
git log --oneline feat/st-008-decomposition-rule ^main
git status
```
Expected: ~11 task commits + the spec commit; clean working tree.

---

## Self-review notes (author check — completed)

- **Spec coverage:** Part 1 → Task 5; Part 2 → Task 6; Part 3 (wiring) → Tasks 1-4, 10, 11; Part 4 (de-bias) → Tasks 7-9. All four parts mapped.
- **Type/name consistency:** the config function is `load_god_file_config` everywhere (Tasks 1, 2); the hook file is `warn-god-file.py` everywhere (Tasks 2, 3, 4, 11, 12); config keys `god-file` / `god-file-max-lines` / `god-file-max-decls` are consistent across `_structure.py`, the hook, the seeded template, and ST-008's prose.
- **No placeholders:** every code step shows full code; every command states expected output.
- **Out of scope (per spec):** Fix-mode fan-out, hard-blocking on size, new SOLID rules — none appear here.
