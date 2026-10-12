---
max_turns: 30
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit]
model: opus
runs: 3
plugins: [../..]
tags: [typescript, write, cocos-creator]
---
In my Cocos Creator 3.8 project, write the player's health component at `assets/player/scripts/PlayerHealth.ts` (a `@ccclass` that extends `Component`).

Max health is set in the editor and the player starts at full health. Taking damage lowers health, never below zero, and then makes the player invulnerable for a short time, also set in the editor and 0.5 seconds by default; damage during that window is ignored. Healing raises health, never above the max. When health reaches zero the player is dead: other scripts need to hear about the death exactly once, and after that the player takes no more damage and can't be healed.
