#!/usr/bin/env python3
"""Run the content hooks against in-memory content (no file on disk).

Used both to capture the block message a case produces (the stderr the model is
shown) and to re-check a candidate fix. Content is passed in the synthetic Write
payload exactly as at write time; the file path is a neutral sandbox path so
project-root / ignore-file detection can't pick up this repo's own config.

Stdlib only.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_HOOK_DIR = Path(__file__).resolve().parents[2] / "hooks"
# Outside any repo, so find_project_root() finds no .git / .coding-standards-ignore.
_SANDBOX = "/tmp/cs-recovery-sandbox"

HOOK_FILES: tuple[str, ...] = (
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
)


def _payload(file_name: str, content: str) -> str:
    path = f"{_SANDBOX}/{file_name}"
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path, "content": content}})


def run_hook(interpreter: str, hook: str, file_name: str, content: str) -> tuple[int, str]:
    proc = subprocess.run(
        [interpreter, str(_HOOK_DIR / hook)],
        input=_payload(file_name, content),
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc.returncode, proc.stderr


def block_message(interpreter: str, file_name: str, content: str) -> str:
    """The joined stderr of every hook that hard-blocks (exit 2) this content."""
    messages: list[str] = []
    for hook in HOOK_FILES:
        code, stderr = run_hook(interpreter, hook, file_name, content)
        if code == 2 and stderr.strip():
            messages.append(stderr.strip())
    return "\n".join(messages)


def is_blocked(interpreter: str, file_name: str, content: str) -> bool:
    for hook in HOOK_FILES:
        code, _stderr = run_hook(interpreter, hook, file_name, content)
        if code == 2:
            return True
    return False
