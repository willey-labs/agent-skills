# Cocos Creator — Structure

## Builds on `common/structure.md`

This file adds only what's specific to Cocos Creator (2.x and 3.x, TypeScript games). The decomposition
model — business → feature → sub-feature → unit, one job per file, front door, Rule of Three, all the ST
rules — lives in `common/structure.md`, loaded alongside this. Cocos diverges from a web framework on
several engine-specific points.

## Outer shell

Business folders are yours to name: put them flat at the top of `assets/`, one folder per feature, each
owning its own scene, scripts, prefabs, and assets. Adding or removing a feature touches one folder.

- A feature folder that benefits from lazy loading is marked an **Asset Bundle** in the editor (select it,
  Inspector → "Configure as Bundle", name it after the folder, save the meta). Mark a folder when it has
  its own loadable scene, is opened on demand, or is heavy enough to delay startup. Leave it a plain folder
  when it's always loaded with the main scene or too small to earn the overhead.
- **Bundles must not nest** — a bundle cannot contain another bundle. Group deeper with plain subfolders.
- No `bundles/` or `features/` wrapper, and no layered top-level `assets/scripts/`, `assets/prefabs/`,
  `assets/textures/` — those collapse the whole project into one undivided unit.
- The engine-managed folders `library/`, `temp/`, `build/` (plus `local/`, `profiles/`, `build_<timestamp>/`)
  are generated, never hand-edited, and must be gitignored. Commit `settings/` and the project/ts config.

How many feature folders you end up with depends on the game — a jam prototype may have three, an RPG a
dozen. The pattern is fixed; the count is not.

## Naming

- **Bundle / feature folders** — `kebab-case` (`main-menu/`, `level-01/`).
- **Component scripts** (`extends Component` + `@ccclass`) — `PascalCase.ts`, one component per file, and
  the `@ccclass('Name')` name matches both the class and the filename. Names are feature-qualified, not
  generic: `MenuButton`, not `Button`; `InventorySlot`, not `Slot`. Generic names live only in
  `assets/shared/prefabs/`.
- **Pure modules** (no Cocos `Component` — just functions, types, constants) — `kebab-case.ts`
  (`spawn-table.ts`, `damage-calc.ts`, `events.ts`). The casing difference is the visual hint: PascalCase
  files attach to nodes, kebab-case files don't.
- **Assets** — scenes `PascalCase.scene`, prefabs `PascalCase.prefab`, materials `PascalCase.mat`;
  textures, audio, and `.anim` clips `kebab-case`.
- **Event keys** (strings in the typed bus) — `<domain>/<verb-noun>` (`'level/start'`,
  `'inventory/changed'`).

## Front door

There is **no `index.ts` barrel** in Cocos — the **bundle is the boundary**. A bundle's scenes, prefabs,
and scripts are private to it. Cross-bundle access never goes through a deep import path; it goes through
one of three explicit seams:

1. a typed event bus in `shared/` that either side emits to and listens on,
2. shared typed state (save/profile data) in `shared/`,
3. the always-loaded boot/composition script that loads bundles and wires them at the seams.

A direct `import { X } from '../../other-bundle/scripts/...'` compiles but breaks isolation, so it's
forbidden the same way reaching past a folder's front door is in `common`.

## Cocos specifics

- **One layout inside every bundle.** Group by asset kind at the bundle root: the scene (named
  after the bundle), then `scripts/`, `prefabs/`, `textures/`, `audio/`, `materials/`, `animations/` as
  each is needed. A `.ts` or `.prefab` loose at the bundle root is wrong. Inside `scripts/`: stay flat
  until it grows past ~7 files, then group by **sub-concern** (`scripts/player/`, `scripts/enemies/`) —
  never by class kind (`components/`, `systems/`, `types/`), which is the layered mistake one level down.

- **Bundles don't import each other.** A bundle you reference may not be loaded when you need it
  (null refs), hot-reloading one invalidates the other, and the dependency graph goes implicit so unloading
  breaks. Talk through the three seams above; depend only on `shared/`.

- **The component is the unit; one component, one responsibility.** Treat each `@ccclass` like a
  function: one job, intent-revealing name, lifecycle methods kept short (push logic into private methods).
  Subscribe in `onLoad()`, unsubscribe in `onDestroy()` — a missed `.off()` leaks across scene changes and
  breaks hot-reload.

- **No global singletons holding state across bundles.** A `Game.instance` / `Player.instance`
  static becomes the new junk drawer: every bundle couples to it and unloading leaves stale references.
  Cross-bundle state goes through the save layer or the event bus, both in `shared/`. A stateless typed
  event bus and local node-scoped state are fine.

- **Each bundle owns its own load/unload.** A bundle must load, run, and unload as a unit. The
  composition root tracks which bundles are alive; inside a bundle, the main controller loads its own
  prefabs on `start()`, subscribes to events, and releases references + unsubscribes on `onDestroy()` so
  unloading doesn't leak. Don't load another bundle's assets from inside a bundle controller, and don't
  hold references to assets after their bundle is removed.

- **Typed events over magic strings.** Cocos's event system is string-keyed. Wrap an
  `EventTarget` in a module that maps each key to its payload type, so the compiler catches typos:

  ```typescript
  // assets/shared/scripts/events.ts
  type GameEventMap = {
      'level/start':       { levelId: string };
      'level/complete':    { levelId: string; stars: number };
      'inventory/changed': { added?: string; removed?: string };
  };
  // emit<K>(key: K, payload: GameEventMap[K]) / on / off, exported as one bus instance
  ```

  Raw `node.emit('mEnu/Action', ...)` is forbidden — a typo is a silent failure.

- **Load scenes/prefabs/resources by bundle, not by global path.** Load a bundle
  (`assetManager.loadBundle('level-01', ...)`), then load through it (`bundle.loadScene('Level01', ...)`,
  `bundle.load('prefabs/Coin', Prefab, ...)`). Don't hardcode another bundle's path through
  `resources.load(...)`, and don't dump every asset into `assets/resources/` "just in case" — that defeats
  bundle laziness and balloons the always-loaded payload.

- **Keep the editor `@property` surface narrow.** Per `common/objects-and-data.md` OD-005, a
  Cocos component's `@property` fields are the framework contract for the inspector, not the forbidden
  data-exposing hybrid. Keep the carve-out small: `@property`-decorate only fields a non-coder must set in
  the editor, always type them explicitly with a default (`@property(Prefab) myPrefab: Prefab | null =
  null`), and prefer a `@property(Node)` reference over `find()`-by-name (which breaks silently on rename).

> **Trap — moving a script breaks scene references.** Cocos tracks every script by a GUID stored in its
> sibling `.ts.meta` file, and scenes/prefabs reference scripts by that GUID, not by path. Move or rename a
> script with a plain file operation and you orphan the meta — the GUID changes and every scene/prefab
> pointing at it loses the component. Always move/rename inside the editor, or move the `.ts` **and** its
> `.ts.meta` together.
