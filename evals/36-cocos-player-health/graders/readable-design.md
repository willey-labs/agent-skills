---
type: llm
focus:
  source: file
  path: assets/player/scripts/PlayerHealth.ts
---
Grade the design of this file. Ignore whether the logic is correct; another check covers that. PASS only if every claim holds; otherwise FAIL and name the claim and the line.

1. Names say what they hold or do: no abbreviations such as `dmg`, `amt`, `tmp`, `val`, `cfg`, and no single-letter names except a loop or callback parameter used within one or two lines. `dt` as the `update(dt)` parameter is fine.
2. No function or method body is longer than 25 lines.
3. Nothing is more elaborate than one component's health needs: no state machine, damage-type or modifier system, generic stats framework, Strategy/Factory pattern, or static singleton instance. A constant or small typed map for the event name is fine.
4. No `//` comment restates what the next line does, addresses a reader, or describes the change being made. A comment that gives a reason passes even when it also names what the line does. Ignore doc comments and comment length; another check covers those.
