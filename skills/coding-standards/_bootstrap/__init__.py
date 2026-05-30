"""Installer internals for the coding-standards skill.

The skill's setup tooling — machine-readiness check, the mandatory dependency
install, scope detection, and settings.json wiring — grouped behind one boundary
so it doesn't clutter the skill root next to SKILL.md and the content folders
(ST-001 / ST-004). The public entry point stays `../bootstrap.py`; it imports
the pieces it orchestrates from this package.

Modules:
  paths         filesystem anchors (derived from the bootstrap.py entry's path)
  dependencies  REQUIRED_PACKAGES registry + presence checks
  readiness     host detection + the readiness report
  install       the mandatory dependency install (+ PEP 668 venv fallback)
  scope         project/global scope detection + the ignore-file template
  settings      settings.json wiring + slash command + permissions
"""
