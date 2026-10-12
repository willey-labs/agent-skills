#!/usr/bin/env python3
"""Regression test — `--verify` reports a stale wiring, not just a broken one.

A settings.json wired by an older version passes every entry recognizer while
running none of the scripts added since. `--verify` gates the skill's Step 0, so a
stale install that reads as ready never gets repaired. This asserts the
registry-completeness half of that check: one entry per event, no wired script left
unnoticed, and a malformed settings value read as incomplete rather than complete.

    python3 hooks/tests/test-verify-completeness.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent.parent  # skills/coding-standards
sys.path.insert(0, str(SKILL))
from _bootstrap.hook_identity import (  # noqa: E402
    COMMENT_JUDGE_EVENTS,
    HOOK_FILES_BY_EVENT,
    missing_wired_scripts,
)

COMMAND_PREFIX = "python3 /somewhere/.claude/skills/coding-standards/hooks/"
REGISTERED_TOTAL = sum(len(names) for names in HOOK_FILES_BY_EVENT.values())
REQUIRED_BY_EVENT = {
    event: names for event, names in HOOK_FILES_BY_EVENT.items() if event not in COMMENT_JUDGE_EVENTS
}
REQUIRED_TOTAL = sum(len(names) for names in REQUIRED_BY_EVENT.values())


def settings_wiring(names_by_event: dict[str, list[str]]) -> dict:
    """A settings.json shaped like bootstrap writes one, wiring exactly these scripts."""
    return {
        "hooks": {
            event: [
                {"hooks": [{"type": "command", "command": COMMAND_PREFIX + name} for name in names]}
            ]
            for event, names in names_by_event.items()
        }
    }


def check_current_wiring_is_clean(failures: list[str]) -> None:
    absent = missing_wired_scripts(settings_wiring(HOOK_FILES_BY_EVENT))
    if absent:
        failures.append(f"a fully wired settings reported missing scripts: {absent}")


def check_stale_wiring_is_caught(failures: list[str]) -> None:
    """An install wired before the comment hooks: PreToolUse without them, SessionStart without the reminder."""
    pre_tool_use = [name for name in HOOK_FILES_BY_EVENT["PreToolUse"] if "comment" not in name]
    session_start = [name for name in HOOK_FILES_BY_EVENT["SessionStart"] if "inject" not in name]
    absent = missing_wired_scripts(
        settings_wiring({"PreToolUse": pre_tool_use, "SessionStart": session_start})
    )
    expected = REQUIRED_TOTAL - len(pre_tool_use) - len(session_start)
    if len(absent) != expected:
        failures.append(f"stale wiring reported {len(absent)} missing scripts, want {expected}")
    if not any(name.startswith("UserPromptSubmit:") for name in absent):
        failures.append("stale wiring did not report the unwired UserPromptSubmit script")


def check_comment_judge_is_opt_in(failures: list[str]) -> None:
    """Without the judge nothing of it is missing; half a judge reports the other half."""
    absent = missing_wired_scripts(settings_wiring(REQUIRED_BY_EVENT))
    if absent:
        failures.append(f"settings without the comment judge reported missing scripts: {absent}")
    half_judge = settings_wiring({**REQUIRED_BY_EVENT, "PostToolUse": HOOK_FILES_BY_EVENT["PostToolUse"]})
    if not any(name.startswith("Stop:") for name in missing_wired_scripts(half_judge)):
        failures.append("a judge wired without its Stop script did not report it")


def check_unwired_settings_reports_everything(failures: list[str]) -> None:
    for label, settings in (
        ("empty", {}),
        ("no hooks key", {"permissions": {"allow": []}}),
        ("hooks is not a mapping", {"hooks": []}),
    ):
        absent = missing_wired_scripts(settings)
        if len(absent) != REQUIRED_TOTAL:
            failures.append(
                f"{label} settings reported {len(absent)} missing, want {REQUIRED_TOTAL}"
            )


def check_malformed_event_is_not_read_as_wired(failures: list[str]) -> None:
    for label, value in (("string", "not-a-list"), ("mapping", {"hooks": []}), ("null", None)):
        absent = missing_wired_scripts({"hooks": {"PreToolUse": value}})
        if not any(name.startswith("PreToolUse:") for name in absent):
            failures.append(f"a {label} PreToolUse value was read as fully wired")


def check_foreign_entry_counts_as_wired(failures: list[str]) -> None:
    """A registered script wired under someone else's entry still runs, so it is not
    missing — completeness asks what executes, not who wired it."""
    complete = settings_wiring(HOOK_FILES_BY_EVENT)
    complete["hooks"]["PreToolUse"][0]["matcher"] = "Write|Edit|MultiEdit"
    complete["hooks"]["PreToolUse"].insert(0, {"hooks": [{"command": "python3 /other/thing.py"}]})
    if missing_wired_scripts(complete):
        failures.append("an unrelated neighbouring entry made a wired script read as missing")


def main() -> int:
    failures: list[str] = []
    check_current_wiring_is_clean(failures)
    check_stale_wiring_is_caught(failures)
    check_comment_judge_is_opt_in(failures)
    check_unwired_settings_reports_everything(failures)
    check_malformed_event_is_not_read_as_wired(failures)
    check_foreign_entry_counts_as_wired(failures)

    if failures:
        for failure in failures:
            sys.stderr.write(f"FAIL {failure}\n")
        return 1
    print(f"ok — verify-completeness cases hold ({REGISTERED_TOTAL} registered scripts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
