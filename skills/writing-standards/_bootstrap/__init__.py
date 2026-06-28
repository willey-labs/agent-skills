"""writing-standards bootstrap internals.

Mirrors coding-standards' _bootstrap split (ST-008/ST-004): one responsibility per
module — `paths` (filesystem anchors), `scope` (project/global detection),
`settings` (settings.json wiring). The entry point is `bootstrap.py` at the skill
root; it must stay there because SKILL.md Step 0 invokes it by that exact path and
`paths` anchors scope detection on that file's location.
"""
