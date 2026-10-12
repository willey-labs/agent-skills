#!/usr/bin/env python3
"""Composes this skill's hook entries into a settings dict.

Enforcement, the session health check and the per-prompt reminder are always wired.
The comment judge spends a model call per turn, so it is opt-in: an explicit choice
wires or removes it, and with no choice it stays as the settings already have it.

Stdlib only.
"""

from __future__ import annotations

from dataclasses import dataclass

from .hook_entries import (
    build_hook_entry,
    build_post_tool_use_entry,
    build_session_start_entry,
    build_stop_entry,
    build_user_prompt_submit_entry,
)
from .hook_identity import comment_judge_wired
from .settings import (
    merge_hook_entry,
    merge_post_tool_use_entry,
    merge_session_start_entry,
    merge_stop_entry,
    merge_user_prompt_submit_entry,
    remove_comment_judge,
)


@dataclass(frozen=True)
class WiringRequest:
    """What to wire: the scope, the interpreter hook commands run under, and the judge choice."""

    scope: str
    hook_python: str
    judge_choice: bool | None


@dataclass(frozen=True)
class SettingsActions:
    """Per part of settings.json: 'noop', 'added', 'updated' or 'removed'."""

    hooks: str
    session: str
    prompt: str
    judge: str
    judge_enabled: bool

    @property
    def changed(self) -> bool:
        return any(action != "noop" for action in (self.hooks, self.session, self.prompt, self.judge))


def wire_comment_judge(settings: dict, scope: str, wanted: bool) -> str:
    if not wanted:
        return "removed" if remove_comment_judge(settings) else "noop"
    _, post_action = merge_post_tool_use_entry(settings, build_post_tool_use_entry(scope))
    _, stop_action = merge_stop_entry(settings, build_stop_entry(scope))
    return "noop" if post_action == stop_action == "noop" else "updated"


def wire_settings(settings: dict, request: WiringRequest) -> SettingsActions:
    """Merge every entry into `settings` in place and report what changed."""
    scope = request.scope
    judge_enabled = (
        comment_judge_wired(settings) if request.judge_choice is None else request.judge_choice
    )
    _, hooks_action = merge_hook_entry(settings, build_hook_entry(scope, request.hook_python))
    _, session_action = merge_session_start_entry(settings, build_session_start_entry(scope))
    _, prompt_action = merge_user_prompt_submit_entry(
        settings, build_user_prompt_submit_entry(scope)
    )
    return SettingsActions(
        hooks=hooks_action,
        session=session_action,
        prompt=prompt_action,
        judge=wire_comment_judge(settings, scope, judge_enabled),
        judge_enabled=judge_enabled,
    )
