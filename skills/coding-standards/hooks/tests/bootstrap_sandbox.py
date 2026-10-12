#!/usr/bin/env python3
"""Runs the real bootstrap against a throwaway `$HOME` and project, never the user's settings.

Import from a sibling test file:

    from bootstrap_sandbox import project_sandbox, run_bootstrap

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_SKILL = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Sandbox:
    """A throwaway `$HOME`, the linked skill, the venv to reuse, and the project (None: global)."""

    home: Path
    skill: Path
    venv: str
    project: Path | None = None

    @property
    def project_settings(self) -> Path:
        return (self.project or self.home) / ".claude" / "settings.json"


def reuse_venv() -> str | None:
    """The running interpreter's venv when it has tree-sitter, so bootstrap skips the pip build."""
    try:
        import tree_sitter, tree_sitter_typescript  # noqa: F401
    except Exception:  # noqa: BLE001
        return None
    return str(Path(sys.executable).parent.parent)


def run_bootstrap(sandbox: Sandbox, *flags: str) -> int:
    env = {**os.environ, "HOME": str(sandbox.home), "CODING_STANDARDS_VENV": sandbox.venv}
    if sandbox.project is not None:
        env["CLAUDE_PROJECT_DIR"] = str(sandbox.project)
    proc = subprocess.run(
        ["python3", str(sandbox.skill / "bootstrap.py"), "--auto-install", *flags],
        env=env, cwd=str(sandbox.project or sandbox.home), capture_output=True, text=True, timeout=180,
    )
    return proc.returncode


def link_skill(parent: Path) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    link = parent / "coding-standards"
    link.symlink_to(REPO_SKILL)
    return link


def project_sandbox(home: Path, venv: str, proj: Path) -> Sandbox:
    (proj / ".claude").mkdir(parents=True)
    (proj / "package.json").write_text("{}\n")
    return Sandbox(home=home, skill=link_skill(proj / ".claude" / "skills"), venv=venv, project=proj)


def wire_seeded_project(sandbox: Sandbox, seed: dict) -> tuple[int, dict]:
    sandbox.project_settings.write_text(json.dumps(seed, indent=2) + "\n")
    returncode = run_bootstrap(sandbox)
    return returncode, json.loads(sandbox.project_settings.read_text())


def commands(settings: dict, section: str) -> list[str]:
    out: list[str] = []
    for entry in settings.get("hooks", {}).get(section, []):
        for hook in entry.get("hooks", []):
            out.append(hook.get("command", ""))
    return out
