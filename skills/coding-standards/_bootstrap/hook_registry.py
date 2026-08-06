#!/usr/bin/env python3
"""What this skill ships and under which event each script runs.

Four events carry the enforcement: PreToolUse blocks a bad write, SessionStart
repairs dead enforcement, PostToolUse records what a turn wrote, and Stop judges the
comments in it. Adding a script means adding its basename to the right list here and
nowhere else — the entry builders, the recognizers and the config-sync test all read
these lists.

Stdlib only; no imports.
"""

from __future__ import annotations

# Every command we wire references one of these by basename, which is how a re-run
# recognizes (and replaces) our previous block without disturbing unrelated hooks.
HOOK_FILES = [
    "block-junk-paths.py",
    "block-ts-violations.py",
    "block-py-violations.py",
    "block-go-violations.py",
    "block-csharp-violations.py",
    "block-php-violations.py",
    "block-jvm-violations.py",
    "block-god-file.py",
    "block-swallowed-errors.py",
    "block-debug-artifacts.py",
    "advise-comment-slop.py",
    "block-added-comments.py",
    "block-structure-file-violations.py",
]

# Basenames shipped by PAST versions and since retired/renamed. Listed ONLY so an
# older wired block is still recognised (and replaced) on upgrade — never wired anew.
# `warn-god-file.py` is an earlier basename of the god-file check that
# `block-god-file.py` ships under.
RETIRED_HOOK_FILES = [
    "warn-god-file.py",
]

# PostToolUse records which source files a turn wrote; Stop judges the comments in
# them.
POST_TOOL_USE_FILES = [
    "record-touched-files.py",
]
STOP_FILES = [
    "judge-comments.py",
]

# The health check repairs dead enforcement (ISS-006). `startup` is the verified
# matcher value for a new session — the case where silently-dead enforcement does the
# most damage (a whole session of unchecked writes).
SESSION_HEALTH_SCRIPT = "session-health-check.py"
SESSION_START_MATCHER = "startup"

# The reminder rides SessionStart for the opening context and UserPromptSubmit for
# every turn after it, because a rule read once is buried by the time code is written.
INJECT_SCRIPT = "inject-coding-standards.py"
SESSION_START_FILES = [SESSION_HEALTH_SCRIPT, INJECT_SCRIPT]
USER_PROMPT_SUBMIT_FILES = [INJECT_SCRIPT]

# The health check, the recorder and the judge run under a stable `python3`, NOT the
# venv the health check polices: none of them needs the grammars, and a wiped venv
# must not take them down with it.
EVENT_INTERPRETER = "python3"

WRITE_MATCHER = "Write|Edit|MultiEdit"
