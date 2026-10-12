---
type: llm
focus:
  source: file
  path: assets/player/scripts/PlayerHealth.ts
---
The file is a Cocos Creator component that tracks the player's health. Judge the logic as written; do not run it. Judge only the claims below: behaviour the task did not specify (zero or negative amounts, whether damage ignored during invulnerability restarts the timer, the event's name or payload, the default max health) does not affect the verdict. Ignore style, naming and comments. PASS only if every claim holds; otherwise FAIL and name the claim that failed.

1. It exports a class decorated with `@ccclass` that extends `Component`.
2. The max health and the invulnerability duration are editor fields marked `@property`, the duration defaults to 0.5 seconds, and health starts at the max.
3. Damage lowers health by the amount and never below 0.
4. After damage lands, further damage is ignored until the invulnerability duration has passed (through `scheduleOnce`, a timer advanced in `update`, or a timestamp check), and damage applies again after that.
5. Healing raises health by the amount and never above the max.
6. When health reaches 0, an event is emitted (on the node, an `EventTarget`, or an event bus) exactly once; after death, damage and healing change nothing and the event is not emitted again.
