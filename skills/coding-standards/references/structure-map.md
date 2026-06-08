# Structure map (comprehension artifact)

Before the orchestrator checks structure, it **comprehends** it: a top-down model of what the
codebase *is*, expressed in the skill's own hierarchy (`common/structure.md`: Business → Feature →
Sub-feature → Unit). The map is the spec the real tree is diffed against — most ST-* / DP-007 / ST-009
findings are "the real tree doesn't fit this model" deltas, which a per-file pass can never see.

## When it's built
- Built in **Review** (orchestrator pipeline) over the whole package/sub-project, gated by the same
  scope threshold as Fix mode (`orchestrator-pipeline.md`). Below the threshold (small diff/PR), skip
  the full map — note that structural cross-feature findings were not run.
- **Persisted** to `<root>/.coding-standards/structure-map.md` (gitignored via the existing
  `.coding-standards/` line; excluded from future reviews like reports/fixes). NOT stored in
  `.coding-standards-structure` — that file stays placement-only (AGENTS.md).
- **Reused** by the Fix pass (it reads the review report + this map) and by the next review unless the
  tree changed materially (regenerate when stale; a one-line staleness note when reused).

## How it's built — grounded, not narrated
Each node MUST be backed by evidence read from the code, never inferred from folder names alone:
- the folder's front-door exports (`index.*`), a representative unit, and its cross-folder imports.
- For large trees the orchestrator may dispatch a comprehension agent per top-level folder (read +
  return that folder's node as JSON), then assemble. Keep context lean: read excerpts, not whole files.

## Confirm once (large reviews)
Present the map compactly and ask the user **one** question: "is this the intended Business/Feature/
Sub-feature structure?" (reuse the `AskUserQuestion` shape from Step 4 structure-resolution). Confirm
*before* checks run, so a wrong map is caught before it cascades. A wrong map poisons every downstream
check. Below the scope threshold, skip the question.

## Format

```markdown
# Structure map — <sub-project path>  (comprehended <ts>, confirmed <ts|unconfirmed>)

Business: <one line — what the product/sub-project does>

## Features
- <feature-folder>/ — <what it's about>  [product | core/infra | shell]
  - sub: <sub-feature folders, or "none">
  - units: <key units + one-word job>
  - front door: <what index exports>  · depends on: <other features it imports from>

## Relationships & deltas (candidate structural findings)
- <rule code>: <the mismatch between the real tree and the model> — <evidence file:line> — <fix shape>
```

A node with sub-features lists them; a delta names the rule it will become (ST-001/004/008/009, DP-007).
The deltas are *candidate* findings — Worker 1 confirms/severity-grades them against the loaded rules.

## Worked example — claude-tui/packages/api (abridged; the executor's dry-run target)

```markdown
# Structure map — packages/api  (comprehended <ts>, unconfirmed)

Business: an OpenAI-compatible HTTP gateway that fronts the Claude CLI — spawns/pools Claude CLI
processes and exposes them over OpenAI-shaped endpoints.

## Features
- claude/ — engine: spawn & drive the Claude CLI, parse its output.  [core/infra]
  - sub: transport/, output-parsing/, session-files/, usage/
  - units: runner.ts (PTY state machine — cohesive, NOT a god class), json-runner.ts (child-process
    stream-json), account-cli-pool.ts, parse-json-frames.ts, process-termination.ts, ...
  - front door: claude/index.ts · depends on: http (errors)
- http/ — HTTP shell + the shared OpenAI-protocol adapter.  [shell]
  - sub: completion/ (runner→SSE driver toSseEvents/jsonToSseEvents, buildSseChunk, OpenAI body/usage
    shapers, error-mapper) ← the shared home the completion features should build on
- completions/ — POST /v1/completions.  sub: terminal/ (+ a flat json handler — asymmetric)
- chat-completions/ — POST /v1/chat/completions.  sub: json/, terminal/
- sessions/ — PTY single-session (one long-lived runner per session)
- chat-sessions/ — pooled chat sessions  [PEER of sessions — currently MISNESTED under sessions/]
- accounts/ — account CRUD + login/OAuth + warmup
- auth/ — API keys + invites
- files/, observability/ — upload store, request-log store

## Relationships & deltas (candidate structural findings)
- DP-007 / ST-004: completions, chat-completions, chat-sessions each hand-roll the runner-drive + SSE
  pump + OpenAI body/usage shaper; shared home http/completion/ exists — completions uses it, the other
  two bypass it (chat-completions/json/handler.ts, chat-completions/terminal/handler.ts,
  sessions/chat-sessions/chat-sessions.sse-stream.ts). Fix: route all three through http/completion/.
- ST-009: sessions/chat-sessions/ is a peer of sessions/ (own registry/service/routes; shares only
  session-access) — nested as a child. Fix: lift to a sibling; put session-access in a front-doored
  shared home both reach.
- ST-001: the api-key feature is split — accounts/api-key.routes.ts imports ApiKeyStore from
  ../auth/index.js (routes in accounts/, store in auth/). Fix: one feature, one folder.
- ST-008 (promotion, cohesion not count): auth/ holds a 5-file invite-* cluster flat (8-file folder, so
  the 12-count advisory never fires) → auth/invites/. accounts/ holds a 3-file login-* cluster (incl.
  login.ts 478 lines — check DP-001) → accounts/login/.
- NM (stutter): completions/completions-*.ts, chat-completions/chat-completions.*.ts repeat the folder
  name in the file name.
```
