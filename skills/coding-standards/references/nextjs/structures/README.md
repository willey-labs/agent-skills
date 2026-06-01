# Next.js — structure catalog

A **menu** of legitimate Next.js (App Router) project structures. None is "the one true way" — each is a real pattern used by serious teams. On first activation the skill detects the framework, scans the repo, and either **learns** the existing structure or asks the user to **pick** one of these.

The chosen (or learned) variant is written to `.coding-standards-structure` at the framework project root (the sub-project root in a monorepo, not the monorepo root), and from then on the skill reads that file instead of any bundled `structure.md` for layout decisions. Line-level rules (`common/`) always apply unchanged.

| Variant | Where a feature's code lives | Best when | Source |
|---|---|---|---|
| [`route-colocated`](./route-colocated.md) | inside its own `app/<segment>/` | you organize primarily by route; most App Router apps | common Next.js practice |
| [`feature-first`](./feature-first.md) | `src/features/<feature>/` (optional subfolders) | a large app with clear capabilities; you want enforced feature isolation | [bulletproof-react](https://github.com/alan2207/bulletproof-react) |
| [`screaming-architecture`](./screaming-architecture.md) *(default)* | `src/<business>/<feature>/` (fixed subfolders) | you want one uniform, strictly-enforced shape everywhere; the skill's default | this skill (original) |
| [`feature-sliced-design`](./feature-sliced-design.md) | layered slices, imports flow downward only | you want a formal, strictly-specified methodology with shared vocabulary | [feature-sliced.design](https://feature-sliced.design) |

> `feature-first` and `screaming-architecture` are the **loose and strict ends of the same feature-first family** — both put a capability in one folder. bulletproof-react leaves the internal subfolders optional; the original mandates them, per use case.

**Folder descriptions are deliberately school-neutral.** Where a methodology ships its own official names (FSD's layers/segments, bulletproof-react's `features/`), those are used verbatim — we don't invent terminology or borrow loaded terms (e.g. "shared kernel") that overstate what a folder is.
