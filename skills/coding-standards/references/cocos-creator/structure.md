# Cocos Creator — Structure

The chosen pattern for Cocos Creator (2.x and 3.x, TypeScript) projects: **flat feature folders at the top of `assets/`**. Each feature owns its scene, scripts, prefabs, and assets. Folders that benefit from lazy loading are marked as **Asset Bundles** in the editor.

**Design goal:** adding, refactoring, or removing a feature touches *one folder*. The size and number of features depend on the game — the *pattern* is universal, the *number of folders* is not.

---

## The philosophy in one sentence

> Top-level folders inside `assets/` are features. Each owns its scene, scripts, prefabs, and assets. Folders that should lazy-load are marked as Bundles. `shared/` holds cross-cutting code used by 3+ features and is never a bundle.

---

## The universal pattern

Every Cocos Creator project — regardless of size — follows this shape:

```
project-root/
  assets/
    loading/                        ← initial loading scene (always its own bundle)
    <feature>/                      ← one folder per feature
    <feature>/
    ...
    shared/                         ← cross-cutting (NOT a bundle)
    resources/                      ← Cocos Creator's stock folder for dynamic-name loads
                                       (use sparingly — bundles handle most loads)
  settings/                         ← editor settings (commit)
  package.json
  project.json (2.x) / cocos-project.json (3.x)
  tsconfig.json / jsconfig.json
  .gitignore                        ← MUST ignore: library/, temp/, build/, local/
```

The number and names of `<feature>/` folders depend on what the game actually contains.

---

## Examples by game type

### Single-scene game (e.g. a crash/aviator betting game)
One main scene, several rarely-opened windows.
```
assets/
  loading/                          🟢 bundle
  game/                             🟢 bundle  (the one game scene + always-loaded UI)
  chat/                             🟢 bundle  (lazy-loaded window)
  history/                          🟢 bundle  (lazy)
  leaderboard/                      🟢 bundle  (lazy)
  shared/                           plain folder
```

### Level-based game (platformer, puzzle, action)
Multiple discrete playable stages, each with its own scene, art, and music.
```
assets/
  loading/                          🟢 bundle
  main-menu/                        🟢 bundle
  level-01/                         🟢 bundle  ("level" = a distinct playable stage)
  level-02/                         🟢 bundle
  level-03/                         🟢 bundle
  hud/                              🟢 bundle  (in-game overlay shared by all levels)
  shared/                           plain folder
```

### Match-3 / arcade
One game scene, several modes, shop, menus.
```
assets/
  loading/                          🟢 bundle
  menu/                             🟢 bundle
  game/                             🟢 bundle  (the board scene)
  shop/                             🟢 bundle  (lazy)
  power-ups/                        🟢 bundle  (lazy)
  shared/                           plain folder
```

### RPG / open-world
Larger world with many systems.
```
assets/
  loading/                          🟢 bundle
  world/                            🟢 bundle
  inventory/                        🟢 bundle
  combat/                           🟢 bundle  (mostly scripts; loaded with world)
  dialogue/                         🟢 bundle
  shop/                             🟢 bundle
  quest-log/                        🟢 bundle  (lazy)
  dungeon-cave/                     🟢 bundle  (lazy — load when entered)
  dungeon-tower/                    🟢 bundle  (lazy)
  shared/                           plain folder
```

### Tiny prototype / game jam
Don't over-engineer. Three folders is enough.
```
assets/
  loading/
  game/
  shared/
```

You can skip Asset Bundle marking entirely on a prototype — Cocos Creator works fine without them.

---

## Glossary (so the game-type examples are unambiguous)

| Term | Meaning |
|---|---|
| **Scene** | A `.fire` (Cocos 2.x) or `.scene` (3.x) file — the engine's top-level rendered container. Each scene typically lives in its own bundle. |
| **Level** | A distinct playable stage/map with its own scene, art, and (usually) scripts. Mario 1-1, Candy Crush level 247, "forest stage." Not applicable to single-scene games. |
| **Mode** | A gameplay variant (tournament, free play, daily challenge). |
| **Window** | A UI overlay opened from gameplay (chat, settings, shop). Usually a bundle if rarely opened. |
| **System** | A game-mechanics module (inventory, combat, dialogue). May or may not have its own scene. |

---

## When to mark a folder as an Asset Bundle (vs leaving it as a plain folder)

A folder **should be a Bundle** when at least one of these is true:

- ✅ It has its own scene that the engine loads/unloads (`loading/`, `game/`, `level-01/`).
- ✅ It's optional / on-demand (a window the player rarely opens; a tutorial that runs once).
- ✅ Its assets are large enough to delay startup if always loaded.
- ✅ It should be hot-reloadable independently during development.

A folder **stays a plain folder** when:

- ❌ It's `shared/` — every bundle imports from it; bundling adds round-trips for no benefit.
- ❌ It's very small (a single popup with one button) — bundle overhead exceeds the savings.
- ❌ It's always loaded with the main scene anyway.

**Bundles don't nest.** A bundle cannot contain another bundle. If you need deeper grouping, use plain subfolders inside the bundle.

---

## Cocos Creator-managed folders (gitignore these)

The engine generates these — never commit, never hand-edit:

- `library/` — derived asset metadata
- `temp/` — build artifacts
- `build/` — final platform builds
- `local/`, `profiles/` — local editor state
- `build_<timestamp>/` (2.x build output)

---

## CC-001 — Top-level folders inside `assets/` are features

Mark feature folders as Bundles in the editor when CC-001b applies (see the bundle decision rule above):

1. Select the folder in the Cocos Creator editor.
2. Inspector → check **"Configure as Bundle"**.
3. Set the bundle name (matches the folder name).
4. Save the meta file.

The engine now treats this folder as an independent unit. You load it at runtime:

```typescript
import { assetManager } from 'cc';

// load the bundle
const bundle = await new Promise<AssetManager.Bundle>((resolve, reject) => {
    assetManager.loadBundle('level-01', (err, b) => err ? reject(err) : resolve(b));
});

// load assets from it
bundle.load('Level01', Prefab, (err, prefab) => { ... });

// when done, free it
assetManager.removeBundle(bundle);
```

| Allowed at the top of `assets/` | Forbidden |
|---|---|
| ✅ `<feature>/` (one folder per feature, marked as Bundle when it should lazy-load) | ❌ Top-level `scripts/`, `prefabs/`, `textures/`, `images/`, `animations/` (layered — fights feature isolation) |
| ✅ `shared/` (cross-cutting code/assets used by 3+ features — NOT a bundle) | ❌ Loose `.ts`, `.scene`, `.prefab` files at the root of `assets/` |
| ✅ `resources/` (Cocos Creator's stock folder for assets loaded by name from non-bundle code — use sparingly) | ❌ A `bundles/` or `features/` wrapper folder — features sit at the top of `assets/` directly |
|  | ❌ A bundle folder *containing* sub-bundles (bundles don't nest) |

---

## CC-002 — Standard internal layout per bundle

Same shape inside every bundle:

```
<feature>/
  <Feature>.scene                   ← the scene if this bundle has one (named after the bundle)
  scripts/                          ← all TypeScript components / logic
  prefabs/                          ← all .prefab files
  textures/                         ← images
  audio/                            ← sounds
  materials/                        ← shaders / materials (when used)
  animations/                       ← .anim clips (when used)
```

Add a subfolder only when its first file arrives — the slot is reserved. Small bundles can be flat (just `scripts/` and the scene); large bundles fill out the full set.

**Forbidden:**
- ❌ A `.ts` script file at the bundle root — must be inside `scripts/`.
- ❌ A `.prefab` file at the bundle root — must be inside `prefabs/`.
- ❌ Scattering one bundle's pieces across multiple folders.

### CC-002b — Inside `scripts/`: flat until it grows, then group by sub-concern

Start with a **flat `scripts/`** folder. One TypeScript file per component, one component per file:

```
level-01/scripts/
  Level01Controller.ts
  Level01Goals.ts
  Coin.ts
  ExitDoor.ts
```

Once `scripts/` exceeds ~7 files **and** the files visibly cluster around sub-concerns, **group by sub-concern** (not by kind):

```
✅ level-01/scripts/
     player/
       PlayerController.ts
       PlayerInput.ts
       PlayerAnimator.ts
     enemies/
       Slime.ts
       SlimeBehavior.ts
       Boss.ts
       BossPhases.ts
     pickups/
       Coin.ts
       PowerUp.ts
     level/
       Level01Controller.ts
       Level01Goals.ts
       spawn-table.ts
```

**Forbidden — grouping by file kind ("component vs system vs type"):**

```
❌ level-01/scripts/
     components/        ← layered thinking
       PlayerController.ts
       Slime.ts
     systems/
       CombatSystem.ts
     types/
       player-stats.ts
```

That's the layered-vs-feature mistake all over again, one level deeper. *Sub-concerns are mini-features inside the bundle*; group code by what it's about, not by what kind of class it is.

**Rule of thumb:**
- ≤ 7 files → flat `scripts/`.
- 8+ files clustered around sub-concerns → group by sub-concern (`scripts/player/`, `scripts/enemies/`, …).
- One file standing alone (e.g. `scripts/level/Level01Controller.ts`) is still fine inside a sub-concern folder — predictability beats minor folder count.

**File-name conventions inside `scripts/`:**
- Component (`extends Component` + `@ccclass`): `PascalCase.ts`, one component per file.
- Pure module (no Cocos `Component`, just functions/types/constants): `kebab-case.ts`. Examples: `spawn-table.ts`, `damage-calc.ts`, `events.ts`.

The casing difference is the visual hint: PascalCase files attach to nodes; kebab-case files don't.

---

## CC-003 — Bundles must not import from each other

Cross-bundle TypeScript imports compile, but they **violate runtime isolation**:
- The dependent bundle may not be loaded when the importer needs it → null references at runtime.
- Hot-reloading one bundle invalidates references in the other.
- Bundle dependency graph becomes implicit (and breaks unloading).

```typescript
// ❌ Forbidden — inventory/scripts/InventoryController.ts importing main-menu
import { MainMenuController } from '../../main-menu/scripts/MainMenuController';

// ✅ Allowed — depend only on shared/
import { GameEvents } from '../../shared/scripts/events';
```

**Three legitimate communication paths between bundles:**

1. **Shared event bus** — `assets/shared/scripts/events.ts` defines typed events; either bundle emits and listens.
2. **Shared types/state** — typed save/profile data in `assets/shared/scripts/save-data.ts`.
3. **Boot/composition code** — the always-loaded entry point loads bundles and wires them together at the seams.

Direct script-to-script imports across bundles are the smell.

---

## CC-004 — Components are the building block; one component, one responsibility

Cocos Creator components extend `Component` and are decorated with `@ccclass`. Treat each component like a function — one job, intent-revealing name, lifecycle methods kept tight.

```typescript
import { _decorator, Component, Node, EventTarget } from 'cc';
const { ccclass, property } = _decorator;

@ccclass('MenuButton')
export class MenuButton extends Component {
    @property(Node)
    label: Node | null = null;

    @property
    actionName = '';

    onLoad(): void {
        this.node.on(Node.EventType.TOUCH_END, this.handleTap, this);
    }

    onDestroy(): void {
        this.node.off(Node.EventType.TOUCH_END, this.handleTap, this);
    }

    private handleTap(): void {
        gameEvents.emit('menu/action', this.actionName);
    }
}
```

| Rule | Applies |
|---|---|
| One component per file; filename matches class name | Always |
| `@ccclass('Name')` name matches class name | Always |
| Subscribe in `onLoad()`, unsubscribe in `onDestroy()` | Always — leaks break hot-reload |
| Lifecycle methods stay short; push logic into private methods or another component | `common/functions.md` FN-001 |
| `@property` for editor-exposed fields only; private fields stay private | Always |

---

## CC-005 — No global singletons that hold state across bundles

A `Game.instance` or `Player.instance` static class becomes the new junk drawer — every bundle reaches into it, every bundle becomes coupled, and unloading a bundle leaves stale references.

| Allowed | Forbidden |
|---|---|
| ✅ A typed event bus (`shared/scripts/events.ts`) — emits, no state | ❌ `class GameManager { static instance: GameManager; player: Player; ... }` |
| ✅ A typed save-data accessor (`shared/scripts/save-data.ts`) — reads/writes persisted state | ❌ A mutable "context" object passed to every component |
| ✅ Local state on a component scoped to its node | ❌ Components reaching across the scene with `find()` paths |

If you need cross-bundle state, persist it via the save layer (your project's own save mechanism in `shared/`) or send it through the event bus. Don't add static singletons.

---

## CC-006 — Loading and unloading is the bundle's responsibility

Each bundle should be loadable, runnable, and unloadable as a unit. The composition root (always-loaded entry script) orchestrates which bundles are alive:

```typescript
// shared/scripts/bundle-loader.ts (or wherever the entry lives)
class BundleLoader {
    private loaded = new Map<string, AssetManager.Bundle>();

    async load(name: string): Promise<AssetManager.Bundle> { ... }
    unload(name: string): void { ... }
}
```

**Inside each bundle**, the scene's main controller should:
1. Load its prefabs from its own bundle on `start()`.
2. Subscribe to relevant events.
3. Release references and unsubscribe on `onDestroy()` so unloading the bundle doesn't leak.

**Forbidden:**
- ❌ Loading another bundle's assets directly from inside a bundle controller (`assetManager.getBundle('other').load(...)`).
- ❌ Holding references to assets after the bundle is unloaded.

---

## CC-007 — `shared/` requires three users

Same Rule of Three. Move scripts, prefabs, or assets to `assets/shared/` only when 3+ bundles use them:

| Allowed in `shared/` | Forbidden |
|---|---|
| ✅ Design-system prefabs (`Button.prefab`, `Modal.prefab`, `Toast.prefab`) — used everywhere | ❌ A prefab only the main menu uses |
| ✅ `events.ts` — typed event bus used by every bundle | ❌ A controller specific to one game mode |
| ✅ `audio-mixer.ts` — global mixer everyone routes through | ❌ Bundle-specific audio cue logic |
| ✅ UI icons used across many screens | ❌ Mega-file `shared/scripts/utils.ts` (junk drawer) |

**Never start in `shared/`.** Write the asset/script inside the first bundle that needs it. Duplicate into the second. On the third, extract.

---

## CC-008 — Typed events over magic strings

Cocos Creator's event system uses string keys. Wrap them in a typed module so the compiler catches mistakes:

```typescript
// assets/shared/scripts/events.ts
import { EventTarget } from 'cc';

type GameEventMap = {
    'menu/action':       { action: string };
    'level/start':       { levelId: string };
    'level/complete':    { levelId: string; stars: number };
    'inventory/changed': { added?: string; removed?: string };
};

class TypedEventBus {
    private readonly target = new EventTarget();

    emit<K extends keyof GameEventMap>(key: K, payload: GameEventMap[K]): void {
        this.target.emit(key, payload);
    }

    on<K extends keyof GameEventMap>(key: K, handler: (p: GameEventMap[K]) => void, ctx?: unknown): void {
        this.target.on(key, handler, ctx);
    }

    off<K extends keyof GameEventMap>(key: K, handler: (p: GameEventMap[K]) => void, ctx?: unknown): void {
        this.target.off(key, handler, ctx);
    }
}

export const gameEvents = new TypedEventBus();
```

Forbidden: raw `node.emit('mEnu/Action', ...)` with magic strings — typos are silent failures.

---

## CC-009 — Resources, scenes, and prefabs: load by bundle, not by global path

| Operation | Right way |
|---|---|
| Load a scene from a bundle | `bundle.loadScene('Level01', ...)` after `assetManager.loadBundle('level-01', ...)` |
| Load a prefab dynamically | `bundle.load('prefabs/Coin', Prefab, ...)` |
| Load a one-off asset shared by everything | `resources.load(...)` only if the asset lives under `assets/resources/` |
| Switch scenes | `director.loadScene(...)` after the bundle is loaded |

**Forbidden:**
- ❌ Hardcoding asset paths from another bundle: `resources.load('main-menu/prefabs/MenuButton')` won't work (main-menu isn't in `resources/`).
- ❌ Putting every prefab in `assets/resources/` "just in case" — defeats bundle isolation and balloons the always-loaded payload.

The rule: a bundle's prefabs/scenes/textures are loaded **through that bundle's API**, not through global paths.

---

## CC-010 — File and folder naming

| Type | Convention | Example |
|---|---|---|
| Bundle folder | `kebab-case`, descriptive | `main-menu/`, `level-01/`, `inventory/` |
| Scene file | `PascalCase.scene` | `MainMenu.scene`, `Level01.scene` |
| TypeScript component | `PascalCase.ts`, one component per file | `PlayerController.ts`, `MenuButton.ts` |
| Component class | `PascalCase`, matches `@ccclass(...)` and filename | `class MenuButton extends Component` |
| Prefab | `PascalCase.prefab` | `MenuButton.prefab`, `Coin.prefab` |
| Texture | `kebab-case.{png,jpg,webp}` | `logo.png`, `menu-bg.webp` |
| Audio | `kebab-case.{mp3,ogg,wav}` | `button-tap.ogg`, `level-music.mp3` |
| Material | `PascalCase.mat` | `WaterReflective.mat` |
| Animation | `kebab-case.anim` | `player-run.anim` |
| Event key (string in typed bus) | `<domain>/<verb-noun>` | `'level/start'`, `'inventory/changed'` |

Component names must be **feature-qualified**, not generic. `MenuButton` (not `Button`), `InventorySlot` (not `Slot`). Generic names are reserved for `assets/shared/prefabs/` — the design-system primitives.

---

## CC-011 — Editor-exposed properties stay narrow

The `@property` decorator publishes a field to the editor inspector. Each property is a **public surface** of the component — published properties are harder to change later because designers wire them up in scenes/prefabs.

| Rule | Why |
|---|---|
| Only `@property`-decorate fields a non-coder needs to set in the editor | Every exposed property is a future migration cost |
| Always type the property explicitly (`@property(Prefab) myPrefab: Prefab \| null = null`) | The editor needs the type hint; TS strict mode demands it |
| Prefer `Node` references via `@property(Node)` over `find()`-by-name | Compile-time wiring; find-by-name breaks silently on rename |
| Default values for properties (`= null`, `= 0`) so the component is in a valid state on creation | Avoids null-ref crashes when designers add the component to an empty node |

---

## Anti-patterns to flag in review

| Anti-pattern | Why it's banned |
|---|---|
| Top-level `assets/scripts/`, `assets/prefabs/`, `assets/textures/` (layered) | Fights feature isolation; the whole project becomes one bundle |
| A bundle's script importing from another bundle's `scripts/` | Couples bundles; breaks runtime isolation |
| Static singletons (`Game.instance`, `Player.instance`) holding cross-bundle state | Coupling soup; breaks unload |
| `node.emit('eventName', ...)` with magic strings | Typos are silent; use typed event bus |
| Putting every asset in `assets/resources/` | Defeats bundle laziness; balloons initial payload |
| `find('Canvas/UI/HealthBar')` from script | Couples to scene hierarchy; renames break silently |
| `@property` on every field, including internal ones | Inflates the public surface; designers wire things they shouldn't |
| `update(dt)` doing heavy work every frame | Cocos calls `update` every frame; do work in response to events instead |
| Forgetting `onDestroy()` cleanup (`.off()`, `assetManager.removeBundle()`) | Memory leaks survive scene change |
| `shared/scripts/utils.ts` | Junk drawer; name files by what they do |
| Bundle containing a sub-bundle | Bundles don't nest — flatten |
| Layered split inside a feature (`<feature>/components/`, `<feature>/services/`) | Cocos isn't NestJS; group by asset *kind* (`scripts/`, `prefabs/`), not by abstract layer |
| A `bundles/` or `features/` wrapper at the top of `assets/` | Adds a useless level — feature folders should sit at the top of `assets/` directly |

---

## Review checklist

```
Structure
  □ Top-level folders inside assets/ are features (no bundles/ or features/ wrapper)
  □ Folders that should lazy-load are marked as Bundles in the editor
  □ shared/ is a plain folder (not a bundle)
  □ Bundle count matches game size — don't over-bundle a small game
  □ Each bundle has scripts/, prefabs/, textures/ as needed
  □ assets/shared/ contains only assets used by 3+ bundles
  □ No top-level assets/scripts/, assets/prefabs/, assets/textures/
  □ library/, temp/, build/, local/ in .gitignore

Bundles
  □ Bundles never import from other bundles' scripts/
  □ Cross-bundle communication via typed event bus (shared/scripts/events.ts)
  □ Each bundle loads/unloads as a unit

Components
  □ One @ccclass component per file; filename matches class name
  □ Lifecycle methods short (delegate logic out)
  □ on() in onLoad, off() in onDestroy — no leaks
  □ @property used only for editor-exposed fields
  □ Generic component names (Button, Modal) only in shared/prefabs/

Loading
  □ Assets loaded via the owning bundle, not global resources.load()
  □ Bundles removed via assetManager.removeBundle() when no longer needed
  □ No magic-string scene/prefab paths

Naming
  □ Bundle folders kebab-case
  □ Components PascalCase, feature-qualified
  □ Prefabs PascalCase
  □ Textures/audio kebab-case
  □ Event keys typed in shared/scripts/events.ts
```
