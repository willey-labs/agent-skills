#!/usr/bin/env python3
"""Regression test — the Stop-time comment judge and its wiring.

Offline: a fake `claude` on PATH stands in for the model, so the plumbing is tested
without a network call or a bill. What each case pins down:

- the judge holds a turn open (exit 2) on a delete verdict, and lets it end on keep
- every failure path fails OPEN — no CLI, a failing CLI, unparseable output, the
  recursion guard, an already-active Stop hook
- the round cap: a session cannot be held open forever
- only comments on lines the working tree changed are judged
- the recorder logs source files and skips excluded, generated and non-source ones
- the wired PostToolUse and Stop entries have the right shape and re-merge cleanly

    python3 hooks/tests/test-comment-judge.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
HOOKS_DIR = TESTS_DIR.parent
SKILL = HOOKS_DIR.parent
sys.path.insert(0, str(TESTS_DIR))
sys.path.insert(0, str(HOOKS_DIR))
sys.path.insert(0, str(SKILL))

from _bootstrap.hook_entries import build_post_tool_use_entry, build_stop_entry  # noqa: E402
from _bootstrap.settings import merge_post_tool_use_entry, merge_stop_entry  # noqa: E402
from harness import report_failures  # noqa: E402

JUDGE = HOOKS_DIR / "judge-comments.py"
RECORDER = HOOKS_DIR / "record-touched-files.py"

BLOATED = """export function withdraw() {
  // I switched this to a lookup as you asked — let me know if the loop reads
  // better. Not sure the empty case can even happen here?
  return validate();
}
"""
DELETE_VERDICT = '{"findings":[{"id":1,"verdict":"delete","why":"chat left in the file"}]}'
KEEP_VERDICT = '{"findings":[{"id":1,"verdict":"keep","why":"earns its place"}]}'


def _fake_cli(workdir: Path, answer: str, exit_code: int = 0) -> Path:
    """A stand-in `claude` that ignores its arguments and prints `answer`."""
    bin_dir = workdir / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "claude"
    script.write_text(f"#!/bin/sh\ncat > /dev/null\nprintf '%s' '{answer}'\nexit {exit_code}\n")
    script.chmod(0o755)
    return bin_dir


def _repo_with_comment(workdir: Path, content: str) -> Path:
    """A git repo whose committed file has just gained `content`, so the comment
    lines show up as this working tree's change."""
    repo = workdir / "repo"
    (repo / "src").mkdir(parents=True)
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.email", "t@t"],
        ["git", "config", "user.name", "t"],
    ):
        subprocess.run(command, cwd=repo, check=True, capture_output=True)
    target = repo / "src" / "withdraw.ts"
    target.write_text("export const placeholder = 1;\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True, capture_output=True)
    target.write_text(content)
    return target


def _run_judge(workdir: Path, target: Path, answer: str, extra_env: dict) -> tuple[int, str]:
    """Record `target`, then run the Stop hook with a fake model answering `answer`."""
    env = dict(os.environ)
    env["XDG_DATA_HOME"] = str(workdir / "data")
    env["PATH"] = f"{_fake_cli(workdir, answer)}{os.pathsep}{env['PATH']}"
    env.pop("CODING_STANDARDS_COMMENT_JUDGE", None)
    env.update(extra_env)
    key = extra_env.get("_key", "test-session")
    payload = {"session_id": key, "transcript_path": "/tmp/t.jsonl", "cwd": str(target.parent)}
    payload.update(json.loads(extra_env.get("_payload", "{}")))

    sys.path.insert(0, str(HOOKS_DIR))
    from _touched_ledger import record  # noqa: PLC0415

    os.environ["XDG_DATA_HOME"] = env["XDG_DATA_HOME"]
    record(key, str(target))
    proc = subprocess.run(
        [sys.executable, str(JUDGE)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stderr + proc.stdout


def judge_failures() -> list[str]:
    """Every judge case, each in its own sandbox."""
    failures: list[str] = []
    cases = [
        ("delete verdict holds the turn open", DELETE_VERDICT, {}, 2, "withdraw.ts"),
        ("keep verdict lets the turn end", KEEP_VERDICT, {}, 0, ""),
        ("unparseable answer fails open", "not json at all", {}, 0, ""),
        ("recursion guard exits at once", DELETE_VERDICT,
         {"CODING_STANDARDS_COMMENT_JUDGE": "running"}, 0, ""),
        ("active stop hook exits at once", DELETE_VERDICT,
         {"_payload": '{"stop_hook_active": true}'}, 0, ""),
    ]
    for name, answer, extra_env, expected_code, expected_text in cases:
        with tempfile.TemporaryDirectory() as raw:
            workdir = Path(raw)
            target = _repo_with_comment(workdir, BLOATED)
            code, output = _run_judge(workdir, target, answer, dict(extra_env))
            if code != expected_code:
                failures.append(f"{name}: expected exit {expected_code}, got {code}: {output.strip()}")
            elif expected_text and expected_text not in output:
                failures.append(f"{name}: expected {expected_text!r} in message, got {output.strip()!r}")
    return failures


def failing_cli_failure() -> str | None:
    """A model call that errors must not block the turn."""
    with tempfile.TemporaryDirectory() as raw:
        workdir = Path(raw)
        target = _repo_with_comment(workdir, BLOATED)
        env = dict(os.environ)
        env["XDG_DATA_HOME"] = str(workdir / "data")
        env["PATH"] = f"{_fake_cli(workdir, DELETE_VERDICT, exit_code=1)}{os.pathsep}{env['PATH']}"
        os.environ["XDG_DATA_HOME"] = env["XDG_DATA_HOME"]
        from _touched_ledger import record  # noqa: PLC0415

        record("cli-fails", str(target))
        proc = subprocess.run(
            [sys.executable, str(JUDGE)],
            input=json.dumps({"session_id": "cli-fails", "transcript_path": "/tmp/t.jsonl"}),
            capture_output=True,
            text=True,
            env=env,
        )
        if proc.returncode != 0:
            return f"failing CLI: expected exit 0, got {proc.returncode}"
    return None


def round_cap_failure() -> str | None:
    """After the cap, findings are reported instead of holding the turn open."""
    with tempfile.TemporaryDirectory() as raw:
        workdir = Path(raw)
        target = _repo_with_comment(workdir, BLOATED)
        codes = [
            _run_judge(workdir, target, DELETE_VERDICT, {"_key": "capped"})[0] for _ in range(3)
        ]
        if codes != [2, 2, 0]:
            return f"round cap: expected exits [2, 2, 0], got {codes}"
    return None


def unchanged_lines_failure() -> str | None:
    """A comment the working tree did not touch is not judged."""
    with tempfile.TemporaryDirectory() as raw:
        workdir = Path(raw)
        target = _repo_with_comment(workdir, BLOATED)
        subprocess.run(["git", "add", "-A"], cwd=target.parent, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-qm", "keep"], cwd=target.parent, check=True, capture_output=True
        )
        target.write_text(BLOATED + "export const later = 2;\n")
        code, output = _run_judge(workdir, target, DELETE_VERDICT, {"_key": "committed"})
        if code != 0:
            return f"unchanged comment: expected exit 0, got {code}: {output.strip()}"
    return None


def recorder_failures() -> list[str]:
    """The recorder logs source files a turn wrote and skips the rest."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as raw:
        workdir = Path(raw)
        env = dict(os.environ)
        env["XDG_DATA_HOME"] = str(workdir / "data")
        kept = workdir / "src" / "a.ts"
        kept.parent.mkdir(parents=True)
        kept.write_text("export const x = 1\n")
        skipped_dir = workdir / "node_modules" / "b.ts"
        skipped_dir.parent.mkdir(parents=True)
        skipped_dir.write_text("export const y = 1\n")
        doc = workdir / "notes.md"
        doc.write_text("# notes\n")
        for path in (kept, skipped_dir, doc):
            payload = {
                "session_id": "rec",
                "tool_name": "Write",
                "tool_input": {"file_path": str(path), "content": path.read_text()},
            }
            subprocess.run(
                [sys.executable, str(RECORDER)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=env,
            )
        ledger = Path(env["XDG_DATA_HOME"]) / "coding-standards" / "touched" / "rec.paths"
        recorded = ledger.read_text().split() if ledger.exists() else []
        if [Path(p).name for p in recorded] != ["a.ts"]:
            failures.append(f"recorder: expected only a.ts, got {recorded}")
    return failures


def wiring_failures() -> list[str]:
    """The wired entries have the right shape and re-merge without duplicating."""
    failures: list[str] = []
    stop_entry = build_stop_entry("global")
    if "matcher" in stop_entry:
        failures.append("Stop entry must carry no matcher")
    if "judge-comments.py" not in stop_entry["hooks"][0]["command"]:
        failures.append("Stop entry does not run the judge")
    post_entry = build_post_tool_use_entry("project")
    if post_entry.get("matcher") != "Write|Edit|MultiEdit":
        failures.append(f"PostToolUse matcher wrong: {post_entry.get('matcher')}")
    if "${CLAUDE_PROJECT_DIR}" not in post_entry["hooks"][0]["command"]:
        failures.append("project-scope PostToolUse command is not project-relative")

    settings = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo unrelated"}]}]}}
    _, first = merge_stop_entry(settings, build_stop_entry("global"))
    _, second = merge_stop_entry(settings, build_stop_entry("global"))
    if (first, second) != ("added", "noop"):
        failures.append(f"Stop merge should be added then noop, got {(first, second)}")
    if len(settings["hooks"]["Stop"]) != 2:
        failures.append("Stop merge dropped or duplicated an unrelated entry")
    _, post_action = merge_post_tool_use_entry(settings, build_post_tool_use_entry("global"))
    if post_action != "added":
        failures.append(f"PostToolUse merge should be added, got {post_action}")
    return failures


def main() -> int:
    failures = judge_failures() + recorder_failures() + wiring_failures()
    for check in (failing_cli_failure(), round_cap_failure(), unchanged_lines_failure()):
        if check:
            failures.append(check)
    return report_failures("comment-judge", failures, 16)


if __name__ == "__main__":
    sys.exit(main())
